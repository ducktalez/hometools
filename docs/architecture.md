# Architecture

## Streaming issue pipeline

Die Streaming-Server schreiben Warnungen/Errors nicht nur in Logs, sondern zusätzlich in den Shared-Core-Mechanismus unter `src/hometools/streaming/core/issue_registry.py`.

Ablauf:

1. Logs/Fehlerquellen erzeugen offene Unregelmäßigkeiten in `issues/open_issues.json`
2. Jede Beobachtung wird zusätzlich in `issues/issue_events.jsonl` angehängt
3. Offene Issues werden im Shared Core zu stabileren Aufgabenfamilien gebündelt und als `issues/todo_candidates.json` persistiert
4. Der Scheduler-Stub dämpft wiederkehrende Aufgaben über `issues/todo_state.json` per Cooldown
5. `todo_state.json` speichert zusätzlich manuelle Zustände wie `acknowledged` und `snoozed`
6. Die Status-Endpunkte (`/api/audio/status`, `/api/video/status`) liefern neben `issues` eine kompakte `todos`-Summary — ausschließlich für serverseitiges Monitoring und CLI-Zugriff, **nicht** in der Browser-UI sichtbar
7. Beide Server bieten zusätzlich denselben Schreib-Endpunkt (`POST /api/<media>/todos/state`) für `acknowledge`, `snooze` und `clear`
8. Jeder Scheduler-Lauf wird in `issues/scheduler_runs.jsonl` protokolliert

## Designregeln

- TODO-Ableitung bleibt **shared core**, nicht audio-/video-spezifisch.
- Aufgaben werden **konservativ gebündelt** (primär nach Quelle + Kategorie), damit wiederkehrende Einzel-Issues nicht sofort Aufgabenfluten erzeugen.
- Der Scheduler meldet standardmäßig nur **aktive** Aufgaben; kürzlich bereits gemeldete Aufgaben werden bis zum Cooldown unterdrückt, außer ihre Severity steigt.
- Manuelle Zustände (`acknowledge`, `snooze`) gelten pro `todo_key` und leben bewusst im Shared Core statt in audio-/video-spezifischen Modulen.
- Issues/TODOs werden **nicht** in der Browser-UI angezeigt. Die Status-/State-Endpunkte dienen ausschließlich dem serverseitigen Monitoring und der CLI.
- Der Scheduler-Stub führt **noch keine** destruktiven oder langsamen Aktionen automatisch aus; er erzeugt nur priorisierte Kandidaten.
- Alle Funktionen liefern bei Fehlern robuste Defaults zurück und dürfen keine Aufrufer abstürzen lassen.
- Offene Issues, TODO-Kandidaten und spätere Automationsschritte müssen mit dem Schattenverzeichnis unter `HOMETOOLS_CACHE_DIR` koordiniert bleiben.

## Non-blocking Index-Aufbau

Die Katalog-API-Endpunkte (`/api/audio/tracks`, `/api/video/items`) prüfen zuerst den Cache und starten ggf. einen Background-Refresh. `check_library_accessible` wird **nur** aufgerufen, wenn keine gecachten Items vorhanden sind (Cold-Start oder leerer Cache). Dadurch blockiert der Library-Check (bis zu 3 s bei NAS-Pfaden) nie die Auslieferung bereits verfügbarer Daten.

## CLI-Dashboard

`hometools stream-dashboard` kombiniert Issues, TODO-Kandidaten und den letzten Scheduler-Lauf in einer einzigen Box-Drawing-Tabelle. Daten-Logik lebt in `streaming/core/issue_registry.py`, Präsentation in `streaming/core/issue_dashboard.py`. Unterstützt `--json` für maschinelle Auswertung und `--fail-on-match` als Scheduler-Gate.

## Action Hints

TODO-Kandidaten und Scheduler-Ergebnisse enthalten ein `action_hints`-Feld mit strukturierten CLI-Empfehlungen pro Kategorie. Jeder Hint hat `action_id`, `label`, `cli_command` und `make_target`. Mapping in `_ACTION_HINT_MAP`: `thumbnail` → `prewarm-thumbnails`, `cache` → `reindex`, `sync` → `check-nas`, `metadata` → `check-metadata`. Platzhalter `{server}` wird aus dem Source-String aufgelöst.

## Noise-Unterdrückung

`_NOISE_RULES` in `issue_registry.py` definieren quellspezifische Schwellen. Jede Regel hat `source_prefix`, `category`, `min_severity_for_todo` und `min_count_for_todo`. CRITICAL-Issues passieren immer. Noise-gefilterte Kandidaten werden als `noise_suppressed_count` im Payload und Dashboard ausgewiesen.

## Root-Cause-Deduplizierung

`_ROOT_CAUSE_PATTERNS` in `issue_registry.py` gruppieren Issues über Sources und Kategorien hinweg nach gemeinsamer Root-Cause. Erkannte Muster (`library-unreachable`, `ffmpeg-missing`, `permission-denied`) erzeugen einen einzigen TODO statt mehrerer per-Source-TODOs. Der Family-Key wird dann `root-cause|{cause_id}` statt `{category}|{source}`.

## Serien-Episoden-Ordnung (Video)

`parse_season_episode()` in `streaming/core/catalog.py` ist die zentrale Funktion zur Extraktion von Staffel/Episode aus Dateinamen. Unterstützte Muster: `S##E##` und `##x##` (Priorität in dieser Reihenfolge). Gibt `(0, 0)` zurück wenn kein Muster erkannt wird — wirft nie Exceptions.

`MediaItem` trägt die Felder `season: int = 0` und `episode: int = 0`. `build_video_index()` und `quick_folder_scan()` befüllen diese automatisch. `sort_items()` sortiert innerhalb desselben Ordners (artist) nach `(season, episode, title)`, wodurch Serien-Episoden chronologisch statt alphabetisch geordnet werden. Der Client-seitige JS-Sort in `applyFilter()` verwendet dieselbe Logik.

`serie_path_to_numbers()` in `video/organizer.py` delegiert an die Shared-Funktion, wirft aber weiterhin `ValueError` für den Organizer-Workflow.

## YAML-Media-Overrides

Per-Ordner `hometools_overrides.yaml`-Dateien erlauben manuelle Korrektur von Anzeigenamen, Staffel/Episode-Nummern und dem Serientitel. Ähnlich zu Jellyfin NFO-Dateien, aber als einzelne YAML-Datei pro Ordner.

**Modul:** `streaming/core/media_overrides.py`

**Dateiformat:**
```yaml
series_title: "Avatar: Der Herr der Elemente"
episodes:
  "filename.mp4":
    title: "Episodentitel"
    season: 1
    episode: 1
```

**Ablauf:**
1. `load_all_overrides(library_root)` scannt alle Unterordner nach Override-Dateien
2. `apply_overrides(items, library_root)` erstellt neue `MediaItem`-Instanzen mit überschriebenen Werten (frozen dataclass)
3. `series_title` überschreibt das `artist`-Feld (Ordnername) für alle Items im Ordner
4. Fehlende Felder behalten ihren auto-detektierten Wert
5. Integration in `build_video_index()` (vor dem Sortieren) und `quick_folder_scan()`

**Design-Regeln:**
- Override-Dateien leben im Library-Ordner neben den Media-Dateien
- Fehlerhafte/fehlende YAML wird lautlos ignoriert (robustes Fallback)
- `MediaItem` wird nie mutiert — neue Instanzen bei Override

## Shadow-Cache

Das Shadow-Cache-Verzeichnis (Default: `.hometools-cache/` im Repo-Root, überschreibbar via `HOMETOOLS_CACHE_DIR`) speichert alle generierten Artefakte:

- `audio/` — Audio-Thumbnails (Cover-Art, 120px + 480px) **und Waveform-Caches** (`*.waveform.json`)
- `video/` — Video-Thumbnails (Frame-Extraktion via ffmpeg, 120px + 480px)
- `indexes/` — Persisted Index-Snapshots (JSON, library-dir-spezifisch via MD5-Hash)
- `progress/` — Wiedergabe-Fortschritt (JSON)
- `issues/` — Issue-Registry, TODO-Kandidaten, Scheduler-Logs
- `logs/` — Server-Log-Dateien
- `thumbnail_failures.json` — Failure-Registry für fehlgeschlagene Thumbnails
- `video_metadata_cache.json` — Persistierter Metadaten-Cache (ffprobe-Ergebnisse)

### Index-Snapshots

Der vollständige Index wird nach einem erfolgreichen Rebuild atomar als JSON-Snapshot gespeichert (`_save_snapshot`). **Es gibt kein inkrementelles Speichern während des Builds** — wird der Server während der Indizierung beendet, geht der laufende Scan-Fortschritt verloren. Der **letzte erfolgreiche Snapshot bleibt erhalten** und wird beim nächsten Start als Fallback geladen, sodass der Server sofort funktionsfähig ist (ohne Scan-Wartezeit).

### `make clean`

`make clean` löscht **alle** Artefakte unter `.hometools-cache/`:

- Ordner: `audio/`, `video/`, `indexes/`, `issues/`, `logs/`, `progress/`, `shortcuts/`, `playlists/`, `channel/`
- Dateien: `video_metadata_cache.json`, `thumbnail_failures.json`

Das Audit-Log liegt seit dem Refactoring in einem eigenen Verzeichnis (`.hometools-audit/`, konfigurierbar via `HOMETOOLS_AUDIT_DIR`) und wird von `make clean` **nicht berührt**.

### Thumbnails

Zwei Größen pro Mediendatei:
- **Klein** (120px, `.thumb.jpg`) — für Listen- und Grid-Ansichten, schnell ladend
- **Groß** (480px, `.thumb-lg.jpg`) — für Serien-Vorschauen und Detail-Ansichten, nachladend

Beide werden im Hintergrund-Thread generiert (`start_background_thumbnail_generation`). MTime-basierte Invalidierung: Thumbnails werden regeneriert wenn die Quelldatei neuer ist.

### Waveform-Cache (Audio)

**Modul:** `streaming/core/waveform.py`

Für jede Audio-Datei werden 128 normalisierte Peak-Werte (0.0–1.0) im Shadow Cache gespeichert:

```
<cache_dir>/audio/<relative_path>.waveform.json
→ {"peaks": [0.0, ..., 1.0], "segments": 128}
```

**Extraktion:** ffmpeg dekodiert die Audiodatei bei 1 kHz Mono (`-ar 1000 -ac 1 -f f32le`) und schreibt rohes Float32-PCM auf stdout. Python liest es via `struct.unpack`, teilt in 128 gleichgroße Blöcke auf und berechnet pro Block den Peak-Wert (`max(abs(sample))`). Anschließend wird auf [0, 1] normalisiert.

**API-Endpunkt:** `GET /api/audio/waveform?path=<relative_path>`
- Prüft zuerst den Shadow Cache (schnell).
- Generiert bei Cache-Miss on-demand (dauert < 5 s für typische Songs).
- Gibt `{"peaks": [...128 floats...], "segments": 128}` zurück oder 404 bei Fehler.

**Hintergrund-Warmup:** Audio-Server-Startup startet neben dem Thumbnail-Thread auch einen `waveform-bg`-Thread, der alle Waveform-Caches vorab befüllt (`start_background_waveform_generation`). Gleicher Work-Item-Typ wie Thumbnails: `(media_path, cache_dir, media_type, relative_path)`.

**Classic-Mode-UI (Waveform-Overlay):**
Im classic Player-Bar (28 px hoch, `<canvas id="waveform-canvas">`) werden die gecacheten Peaks als semi-transparente Amplituden-Streifen über den Fortschrittsbalken gelegt:
- **Layer 1:** Basis-Fortschrittsbalken (5 px hoch, `#333` / Akzentfarbe je gespielt/ungespielt)
- **Layer 2:** 128 Waveform-Balken zentriert auf der Canvas-Mittellinie (`globalAlpha 0.38` gespielt / `0.22` ungespielt, Farbe `#fff`)
- **Layer 3:** Playhead-Dot (weißer Kreis r=6 an der aktuellen Position)

Die JS-Variable `WAVEFORM_API_PATH = '/api/audio/waveform'` wird in `_player_js.py` beim Rendern injiziert. Ist kein Waveform verfügbar oder `!isAudioMode`, fällt `drawWaveform` auf den reinen Fortschrittsbalken zurück.

**MTime-Invalidierung:** Shadow-Cache wird regeneriert wenn `source.st_mtime > waveform.st_mtime`.

**Exception Safety:** Alle Public-Funktionen in `waveform.py` geben im Fehlerfall `None`/`False` zurück, nie eine Exception.

## On-the-fly Remux & FastStart

**Modul:** `streaming/core/remux.py`

Nicht alle Videoformate sind direkt im Browser streambar. Der Remux-Mechanismus löst zwei Probleme:

### Nicht-native Container (FLV, AVI, MKV)

`needs_remux(path)` erkennt anhand der Dateiendung, ob ein Container nicht nativ vom Browser unterstützt wird. Solche Dateien werden on-the-fly über ffmpeg als **Fragmented MP4** (`-movflags frag_keyframe+empty_moov`) gestreamt.

- **Container Copy** (`-c copy`): Wenn die enthaltenen Codecs browserkompatibel sind (H.264/H.265 Video, AAC/MP3/Opus Audio) — `can_copy_codecs()` prüft via `probe_codecs()` (ffprobe).
- **Transcode**: Wenn die Codecs nicht kompatibel sind (z. B. XviD → H.264, MP2 → AAC).

### Non-FastStart MP4s

`has_faststart(path)` liest die MP4-Atom-Struktur (ftyp/moov/mdat) und erkennt Dateien, bei denen das `moov`-Atom am Ende liegt. Solche Dateien können vom Browser nicht gestreamt werden (HTTP 200 statt 206, gesamte Datei muss heruntergeladen werden).

**Lösung:** Der `/video/stream`-Endpoint erkennt Non-FastStart-MP4s und leitet sie automatisch durch `remux_stream()` mit `-c copy -movflags frag_keyframe+empty_moov`. Für den Browser transparent — sofortige Wiedergabe.

**Design-Regeln:**
- Originaldateien werden **nie** modifiziert
- Remux-Ergebnisse werden **nicht** gecacht — immer on-the-fly (vermeidet Speicherprobleme bei großen Dateien)
- UI zeigt ein ⚡-Badge bei Dateien, die Konvertierung benötigen
- `ffmpeg`/`ffprobe`-Fehler werden graceful behandelt (optimistisches Fallback auf `FileResponse`)

## Wiedergabe-Fortschritt

**Modul:** `streaming/core/progress.py`

Thread-sicherer, atomarer JSON-Storage im Shadow-Cache (`progress/playback_progress.json`). Speichert pro Datei `{relative_path, position_seconds, duration}`.

**Endpoints (Audio + Video):**
- `POST /api/<media>/progress` — speichert Position
- `GET /api/<media>/progress?path=…` — lädt gespeicherte Position

**Client-Verhalten:**
- Debounced Save alle 5 Sekunden via `timeupdate`-Event
- Sofortiges Speichern bei Pause
- Löschung bei `ended`
- Beim Track-Wechsel: letzte Position laden, Toast „Fortfahren bei X:XX" anzeigen (nur wenn `AUTO_RESUME_ENABLED`)

**Auto-Resume (`enable_auto_resume`):**

| Server | `enable_auto_resume` | Begründung |
|---|---|---|
| **Audio** | `False` | Songs starten immer von vorn; kein „Fortfahren bei"-Toast |
| **Video** | `True` (Default) | Serien/Filme nahtlos an letzter Position fortsetzen |

`AUTO_RESUME_ENABLED` steuert nur den Seek beim Track-Wechsel. Progress wird **immer** gespeichert (für „Zuletzt gespielt"-Sektion und explizites Resume via Klick in der Sektion).

## Recently Added (Sortierung nach Neuheit)

`MediaItem` trägt ein `mtime`-Feld (Unix-Timestamp der Datei, via `stat()`). Die Sortier-Option `"recent"` sortiert absteigend nach `mtime` mit Titel als Tiebreaker. Sowohl server-seitig (`sort_items()`) als auch client-seitig (`applyFilter()`) implementiert.

## SVG-Icons

Alle Player-Buttons und UI-Controls verwenden **inline SVGs** statt Unicode-Zeichen. iOS rendert Unicode-Steuerzeichen (▶ ◄ ► ⏸ ⊞ ↓) als farbige Emojis, was das Layout zerstört.

**Konvention:**
- Python-Konstanten: `SVG_PLAY`, `SVG_PAUSE`, `SVG_PREV`, `SVG_NEXT`, `SVG_PIP`, `SVG_BACK`, `SVG_MENU`, `SVG_DOWNLOAD`, `SVG_CHECK`, `SVG_FOLDER_PLAY`, `SVG_PIN`, `SVG_STAR`, `SVG_PLAYLIST`, `SVG_SMART_PLAYLIST`, `SVG_QUEUE`, `SVG_REFRESH`, `SVG_DUPLICATE` in `server_utils.py`
- JS-Variablen: `IC_PLAY`, `IC_PAUSE`, `IC_DL`, `IC_CHECK`, `IC_GRID`, `IC_LIST`, `IC_PIN`, `IC_STAR`, `IC_FOLDER_PLAY`, `IC_PLAYLIST`, `IC_SMART_PLAYLIST`, `IC_QUEUE`, `IC_REMOVE`, `IC_REFRESH` — über `innerHTML` gesetzt (nicht `textContent`)
- Alle SVGs nutzen `currentColor` für Theme-Kompatibilität
- **Nie** Unicode-Zeichen oder HTML-Entities (`&#9733;`, `&#9654;` etc.) — iOS rendert sie als Emoji

## PWA Shortcuts & Deep Linking

**Module:** `streaming/core/shortcuts.py`, `streaming/core/server_utils.py` (JS)

Benutzer können einzelne Medien-Items als Favoriten „pinnen" und auf den Home-Bildschirm speichern.

### Deep Linking

URL-Parameter `?id=<relative_path>` auf der Root-Route (`/`) beider Server (Legacy-Form). Das JS liest den Parameter nach dem Catalog-Load, navigiert automatisch zum Ordner des Items und startet die Wiedergabe. Diese Form bleibt für externe Bookmarks/Shortcut-Manifeste erhalten und wird vom Router (siehe unten) als Sonderfall behandelt.

### URL-Routing / View-State (`_router`)

**Modul:** `streaming/core/server_utils/_player_js.py` (IIFE `_router`)

Der gesamte Navigationszustand wird in der Browser-URL gespiegelt, sodass Reload, Bookmark und „Link teilen" exakt zur gleichen Ansicht zurückführen. Schema (Query-Parameter auf `/`):

| Parameter            | Bedeutung                                                   |
| -------------------- | ----------------------------------------------------------- |
| `view=folder&path=…` | Ordner-Grid (Default, `path=""` = Root)                     |
| `view=playlist&path=…` | Leaf-Ordner-Playlist (Tracklist)                          |
| `view=userplaylist&id=…` | Benutzer-Playlist                                       |
| `view=favorites`     | Favoriten-Playlist                                          |
| `view=offline`       | Offline-Downloads-Bibliothek                                |
| `view=search&q=…`    | Globale Suchergebnisse                                      |
| `track=<rel>`        | (optional) markierter / zuletzt gespielter Titel in der Liste |
| `sort=<field>`       | Sortier-Auswahl (überschreibt `localStorage.ht-sort` für diesen Reload) |
| `fr=<1..5>`          | Rating-Filter (mindestens N Sterne)                         |
| `ff=1`               | Favoriten-Filter aktiv                                      |
| `fg=<genre>`         | Genre-Filter                                                |
| `fh=0`               | Ausgeblendete Titel verstecken (Default = anzeigen/grau)    |
| `vm=grid` \| `vm=list` | View-Mode (Default = `list`)                              |
| `panel=tools`        | Tools-Panel-Modal beim Restore öffnen                       |

**Regeln:**

- Zustand wird automatisch nach jedem View-Wechsel via `pushState` geschrieben (`showFolderView`, `showPlaylist`, `showUserPlaylistView`, `openOfflineLibrary`, `playItem`).
- Nur `track`/Sort/Filter/View-Mode/Panel ändert sich → `replaceState` (kein zusätzlicher History-Einträge zu erzeugen).
- `popstate` (Browser-Vor/Zurück) ruft `_router.restore()` auf und rendert die Ansicht neu, ohne neue History-Einträge zu erzeugen.
- Beim Initial-Load läuft `_router.restore()` erst, nachdem Catalog **und** User-Playlists geladen sind — sonst würde eine `userplaylist`-URL ins Leere zeigen.
- `_suppress = true` während `restore()` verhindert, dass die internen `showFolderView`/`showPlaylist`-Aufrufe ihrerseits URL-Updates schreiben.
- Globale Suche ist routebar (`view=search&q=…`); Track-Marker funktioniert auch in Suchergebnissen.
- UI-State (Sort/Filter/View-Mode) wird in `_applyUiStateFromUrl` **vor** dem Rendern angewandt; die URL gewinnt über `localStorage` und persistiert die übernommenen Werte zurück in `localStorage`.
- Audit ist eine eigene Route (`/audit`), kein Modal — daher kein `panel=audit`.

### Shortcuts API

- `GET /api/<media>/shortcuts` — gespeicherte Shortcuts laden
- `POST /api/<media>/shortcuts` — Shortcut hinzufügen/aktualisieren (`{id, title}`)
- `DELETE /api/<media>/shortcuts?id=…` — Shortcut entfernen

Storage: `<cache_dir>/shortcuts/<server>.json` (Audio/Video getrennt). Thread-sicher, atomare Schreibzugriffe, max. 20 Shortcuts.

### Manifest-Integration

`render_pwa_manifest()` akzeptiert optionale `shortcuts`-Liste. Beide Server laden beim `/manifest.json`-Request die gespeicherten Shortcuts und betten sie als PWA-Shortcuts ein. Dadurch erscheinen Favoriten bei Long-Press auf das App-Icon (Android) bzw. im Share-Sheet (iOS 16.4+).

### UI

Jeder Track in der Liste hat einen Pin-Button (`track-pin-btn`, `IC_PIN` SVG). Klick ruft die Shortcuts-API auf und öffnet:
- **iOS/Android:** `navigator.share()` mit Deep-Link-URL
- **Desktop Fallback:** `navigator.clipboard.writeText()` mit Toast-Hinweis

## Rating-System (POPM)

**Modul:** `streaming/audio/catalog.py`, `audio/metadata.py`

`MediaItem` trägt ein `rating`-Feld (Float `0.0–5.0`, Default `0.0`).

### Format-bewusstes Rating-System

Ratings werden format-abhängig gelesen und geschrieben. Die zentralen Funktionen sind `get_rating_stars(path)` und `set_rating_stars(path, stars)` in `audio/metadata.py` — sie dispatchen automatisch auf den richtigen Format-Reader/-Writer.

| Format | Tag-Typ | Lesen | Schreiben | Wertebereich |
|--------|---------|-------|-----------|--------------|
| **MP3** | ID3 POPM (Popularimeter) | `get_popm_rating()` → `popm_raw_to_stars()` | `set_popm_rating()` | 0–255 (WMP-Mapping) |
| **M4A/MP4** | Windows Xtra + iTunes Freeform | `_read_m4a_rating()` (Xtra→iTunes) | `_write_m4a_rating()` (beide) | Xtra: 0/1/25/50/75/99; iTunes: 0–100 |
| **FLAC/OGG/Opus** | Vorbis `FMPS_RATING` + `RATING` | `_read_vorbis_rating()` | `_write_vorbis_rating()` | FMPS: 0.0–1.0, RATING: 0–5 |

#### MP3 POPM-Mapping (Windows Media Player Standard)

| Raw-Bereich | Sterne | Kanonischer Wert |
|-------------|--------|-----------------|
| 0           | 0 (unbewertet) | 0 |
| 1–31        | 1★     | 1   |
| 32–95       | 2★     | 64  |
| 96–159      | 3★     | 128 |
| 160–223     | 4★     | 196 |
| 224–255     | 5★     | 255 |

#### M4A/MP4 Dual-Tag-System (Xtra + iTunes)

M4A/MP4-Dateien verwenden **zwei unabhängige Rating-Tags**, die beim Schreiben synchron gehalten werden:

1. **Windows Xtra-Box** (`moov/udta/Xtra → WM/SharedUserRating`):
   - Microsoft-proprietäre Box, die Windows Explorer zum Anzeigen/Setzen von Bewertungen verwendet.
   - Werte als int64 (little-endian) im Xtra-Attribut-Format gespeichert.
   - Da mutagen die Xtra-Box nicht kennt, wird sie als Raw-Binary gelesen/geschrieben.
   - **Lese-Priorität 1** — das ist was der User im Windows Explorer sieht.

| WM-Wert | Sterne |
|---------|--------|
| 0       | 0 (unbewertet) |
| 1       | 1★     |
| 25      | 2★     |
| 50      | 3★     |
| 75      | 4★     |
| 99      | 5★     |

2. **iTunes Freeform-Atom** (`----:com.apple.iTunes:RATING`):
   - Prozent-Skala 0–100 (20 pro Stern), gespeichert als UTF-8-Text.
   - Kompatibel mit Mp3tag, MediaMonkey, foobar2000, macOS.
   - **Lese-Priorität 2** — Fallback wenn keine Xtra-Box vorhanden.

| iTunes-Wert | Sterne |
|-------------|--------|
| 0    | 0 (unbewertet) |
| 20   | 1★     |
| 40   | 2★     |
| 60   | 3★     |
| 80   | 4★     |
| 100  | 5★     |

Werte ≤ 5 werden als direkte Sternzahl interpretiert (Kompatibilität mit Tools die 1–5 statt 0–100 schreiben).

**Xtra-Box-Format (Binary):**
```
Box: 4 bytes size (BE) + "Xtra"
  Attribute: 4 entry_size (BE) + 4 name_len (BE) + name (ASCII)
           + 4 val_count (BE)
           + [4 val_size (BE) + 2 val_type (BE) + value_data]
  val_type 0x0013 = int64 (LE)
```

**Write-Fälle:**
1. Xtra-Box existiert mit `WM/SharedUserRating` → In-Place-Update (keine Größenänderung)
2. Xtra-Box existiert ohne `WM/SharedUserRating` → Attribut anhängen + Eltern-Boxen (Xtra/udta/moov) Größe anpassen
3. Keine Xtra-Box → Neue Box in `moov/udta` erstellen + Eltern-Boxen Größe anpassen

**Binary-Fallback:** `_read_m4a_rating` versucht zuerst UTF-8-Text-Parsing (z.B. `b"80"` → 80). Bei Fehlschlag wird der Wert als binärer Integer interpretiert (ein Byte: Ordinalwert; mehrere Bytes: Big-Endian). Damit werden auch Ratings gelesen, die von Tools mit IMPLICIT-Datenformat (statt UTF-8) geschrieben wurden.

#### FLAC/OGG Vorbis-Comments

- **`FMPS_RATING`** (Free Music Player Specifications): Float 0.0–1.0 (0.2 pro Stern). Wird bevorzugt gelesen.
- **`RATING`**: Integer 1–5. Fallback wenn kein FMPS_RATING vorhanden.
- Beim **Schreiben** werden beide Tags gesetzt (maximale Kompatibilität).

**Video:** Kein Rating-Lesen; Defaultwert `0.0`.

**UI:** Eine 3px hohe Verlaufsleiste (orange–gelb) erscheint am unteren Rand des Thumbnail-Bilds — sowohl in Track-Listen als auch in Folder-Grid-Karten. Die Breite entspricht `rating / 5 * 100 %`. Unbewertet = keine Leiste. CSS-Klasse `.rating-bar`.

**Design-Regeln:**
- `get_rating_stars()` und `set_rating_stars()` in `audio/metadata.py` sind die einzigen öffentlichen Funktionen für format-bewusstes Rating-Lesen/-Schreiben.
- `popm_raw_to_stars()` und `stars_to_popm_raw()` bleiben als MP3-spezifische Helfer erhalten (werden intern von `get_rating_stars`/`set_rating_stars` für MP3 aufgerufen).
- `get_popm_rating()` prüft vor dem ID3-Lesen die Dateiendung; gibt bei Nicht-MP3 `0` zurück um den `can't sync to MPEG frame`-Fehler zu vermeiden.
- **M4A Dual-Tag-Sync:** `_write_m4a_rating()` schreibt immer **beide** Tags (iTunes-Atom via mutagen, dann Xtra-Box via Raw-Binary). `_read_m4a_rating()` bevorzugt die Xtra-Box (Windows-Wahrheit), fällt auf iTunes-Atom zurück.
- **Snapshot-Versionierung:** `_SNAPSHOT_VERSION` in `index_cache.py` muss gebumpt werden, wenn sich das Datenformat ändert (z.B. Rating-Mapping). Alte Snapshots werden beim Laden verworfen, erzwingen frischen Rebuild vom Dateisystem. Aktuell: v5 (M4A Xtra-Box-Support).
- **Cache-Patch nach Rating-Write:** `audio_set_rating` ruft `patch_items()` auf, bevor `invalidate()` den Cache als stale markiert. So liefert die API sofort das korrekte Rating, auch wenn der Background-Rebuild noch nicht fertig ist.
- **`refreshCatalog()` pollt bei laufendem Build:** Die JS-Funktion prüft `data.refreshing` und ruft `scheduleBackgroundRefresh()` auf, statt veraltete Daten als final darzustellen.

### Rating-Schwellenwert (Min-Rating)

Konfigurierbar über `HOMETOOLS_MIN_RATING` (Env-Var, Default `0`, Bereich 0–5).

Bewertete Tracks mit Rating **< Schwellenwert** werden aus der Track-Liste ausgeblendet. Tracks mit Rating **= Schwellenwert** werden angezeigt. Unbewertete Tracks (`rating == 0`) sind immer sichtbar — sie gelten als „nicht bewertet", nicht als „schlecht bewertet".

**Implementierung:** Die Funktion `get_min_rating()` in `config.py` liest den Wert. Er wird als `min_rating` Parameter durch `render_media_page()` → `render_player_js()` durchgereicht und als JS-Variable `MIN_RATING_THRESHOLD` injiziert. Die Filterung erfolgt in `applyFilter()` (JS) mit `_effectiveThreshold`:
```js
items = items.filter(function(t) {
  var r = t.rating || 0;
  return r === 0 || r >= _effectiveThreshold;  // < threshold wird ausgeblendet, = threshold bleibt sichtbar
});
```

**Beispiel:** `HOMETOOLS_MIN_RATING=3` blendet 1★ und 2★ Tracks aus, zeigt aber unbewertete und **3★+** Tracks.


### Lazy Per-Folder Rating Refresh

Beim Öffnen eines Ordners (Leaf-Folder → `showPlaylist`) werden die Ratings der angezeigten Tracks on-demand vom Dateisystem neu gelesen — **ohne** den gesamten Katalog neu zu bauen. Das löst das Problem, dass ein Full-Rebuild von 5 000+ Songs mehrere Sekunden dauert und alte Ratings bis dahin sichtbar bleiben.

**Ablauf:**
1. `showPlaylist(items, ...)` rendert sofort mit den gecachten Daten (kein Delay).
2. JS `refreshFolderRatings(items)` feuert einen asynchronen `POST /api/audio/refresh-ratings` mit den `relative_path`-Werten der Folder-Items.
3. Der Server liest nur die übergebenen Dateien (typisch 10–50) via `get_rating_stars()` (format-bewusst: MP3/M4A/FLAC/OGG).
4. `IndexCache.patch_items()` ersetzt die Ratings im In-Memory-Cache (frozen MediaItem → `dataclasses.replace()`).
5. Der Server antwortet mit `{"ok": true, "ratings": {...}, "changed": N}`.
6. JS patcht `allItems` und `playlistItems`, ruft `applyFilter()` auf → UI re-rendert nur wenn sich etwas geändert hat.

**Dedup:** `_ratingRefreshPath` (JS) verhindert doppeltes Refresh beim erneuten Öffnen desselben Ordners. Wird bei `refreshCatalog()` zurückgesetzt.

**Bugfix (2026-04-10):** Die Original-Bedingung `!data.ratings || !data.changed` in `refreshFolderRatings()` führte dazu, dass bei `changed === 0` (alle Ratings unverändert) die UI **nie** aktualisiert wurde — selbst wenn das initiale Snapshot-Rating falsch war. Gefixt zu `!data.ratings` (ohne `!data.changed`).

**Module:**
- `streaming/core/index_cache.py` → `IndexCache.patch_items(updates)` — generische Methode für partielle Cache-Updates
- `streaming/audio/server.py` → `POST /api/audio/refresh-ratings` — Audio-spezifisch (POPM-Lesen)
- `streaming/core/server_utils.py` → JS `refreshFolderRatings()` (guarded durch `RATING_WRITE_ENABLED`)

### Debug Filter Mode

Wenn `HOMETOOLS_DEBUG_FILTER=true` in `.env` gesetzt ist, werden Items, die durch `MIN_RATING`, Quick-Filter (Rating-Chip, Favoriten, Genre) ausgeblendet würden, **nicht** aus der Track-Liste entfernt, sondern **ausgegraut** mit Begründungstext angezeigt. Die Textsuche filtert weiterhin normal.

**Motivation:** Beim Debugging von Rating-Problemen war unklar, warum bestimmte Tracks nicht angezeigt werden. Der Debug-Modus macht die Filterlogik transparent sichtbar.

**Implementierung:**
- `config.py` → `get_debug_filter()` liest `HOMETOOLS_DEBUG_FILTER` (bool, Default `false`)
- Parameter-Pipeline: `render_audio_index_html()` / `render_video_index_html()` → `render_media_page(debug_filter=...)` → `render_player_js(debug_filter=...)` → JS-Variable `DEBUG_FILTER`
- JS `applyFilter()`: Wenn `DEBUG_FILTER === true`, werden Items statt mit `.filter()` entfernt mit `._debugReason`-Property annotiert (Klonen des Objekts, Originalarray bleibt unverändert)
- JS `renderTracks()`: Items mit `_debugReason` werden als `<li class="track-item debug-filtered">` gerendert mit:
  - `·` als Nummerierung statt laufender Nummer
  - Alle Track-Info-Felder (Titel, Artist, Thumbnail, Rating-Bar)
  - Zusätzliche `<div class="debug-reason">` mit Begründungstext
  - `pointer-events: none` — nicht klickbar/spielbar
  - `opacity: 0.35` — visuell abgegrenzt
- Track-Count-Header zeigt `"42 tracks (+ 7 ausgeblendet)"` im Debug-Modus
- `filteredItems` enthält **nur** die realen (nicht-debug) Tracks → Shuffle/Queue/Playback unbeeinträchtigt
- CSS: `.track-item.debug-filtered`, `.debug-reason` in `render_base_css()`

**Begründungstexte:** z.B. `"Rating 2★ < Schwelle 3"`, `"Quick-Filter: Rating < 4★"`, `"Kein Favorit"`, `"Genre ≠ Rock"`

### Rating Refresh Log

Persistentes JSON-Log, das festhält, wann die Ratings eines Ordners zuletzt vom Dateisystem gelesen wurden. Löst das Problem der Unsicherheit bei häufigen Server-Neustarts: „Woher weiß der Algo, ob ein Ordner schon indiziert wurde?"

**Dateiformat:** `<cache_dir>/rating_refresh_log.json`
```json
{
  "Funsongs": {"last_refresh": "2026-04-10T14:30:00+00:00", "total": 12, "changed": 3},
  "Rock/Classic": {"last_refresh": "2026-04-10T14:25:00+00:00", "total": 8, "changed": 0}
}
```

**Ablauf:**
1. `POST /api/audio/refresh-ratings` schließt seinen Rating-Durchlauf ab
2. Der Ordner-Pfad wird aus dem gemeinsamen Prefix der übergebenen Paths abgeleitet
3. `_update_refresh_log()` schreibt Timestamp + Statistiken atomar in die JSON-Datei
4. Die Response enthält nun zusätzlich `"last_refresh"` und `"folder"` Felder
5. JS `refreshFolderRatings()` zeigt den Timestamp und die Statistiken im `#refresh-info`-Element im Header

**Endpunkte:**
- `POST /api/audio/refresh-ratings` → Response erweitert um `last_refresh`, `folder`
- `GET /api/audio/refresh-log` → gibt das vollständige Log als JSON zurück

**UI-Anzeige:** `<span id="refresh-info">` im Header neben `track-count`. Zeigt z.B. „23 Ratings gelesen, 5 aktualisiert (14:30)". Wird bei Ordner-Wechsel (`showFolderView`) geleert.

**Module:**
- `streaming/audio/server.py` → `_read_refresh_log()`, `_update_refresh_log()`, `GET /api/audio/refresh-log`
- `streaming/core/server_utils.py` → JS `refreshFolderRatings()` (erweitert), HTML `#refresh-info`-Element, CSS `.refresh-info`

**Design-Regeln:**
- `patch_items()` ist generisch (dict of field overrides) und kann auch für andere Felder genutzt werden.
- Maximal 500 Pfade pro Request (Server-Cap), um Missbrauch zu verhindern.
- Video hat keinen `/refresh-ratings` Endpoint (kein POPM). Die JS-Funktion existiert in beiden UIs, ist aber für Video ein No-Op (`RATING_WRITE_ENABLED = false`).

## Server-Logging

**Modul:** `logging_config.py`

`get_log_dir()` gibt `<cache_dir>/logs/` zurück und erstellt das Verzeichnis bei Bedarf. Alle Server-Commands (`serve-audio`, `serve-video`, `serve-channel`, `serve-all`) leiten Logs an eine rotierende Datei `hometools.log` (5 MB max, 3 Backups) weiter. Logs erscheinen gleichzeitig auf stdout. Sync-Commands (`sync-audio`, `sync-video`) schreiben nur auf stdout (kein `log_file`). `serve-all` startet alle drei Server (Audio, Video, Channel) als separate Subprozesse.

## Folder-Favorites (Namens-Konvention)

Ordner, deren Name mit `#` beginnt, werden als Favoriten behandelt:
- Sie erscheinen im Folder-Grid **zuerst** (vor alphabetischer Sortierung).
- Sie erhalten den CSS-Border `.fav-folder` (accent-farbener Rahmen).
- Ein **SVG-Stern-Badge** (`IC_STAR`, `.fav-badge`) wird absolut oben-rechts auf der Folder-Karte angezeigt (kein Unicode `&#9733;` — iOS-Emoji-Kompatibilität).
- Das `#`-Prefix wird im `displayName` entfernt, sodass in der UI nur der eigentliche Name erscheint.

Folder-Favorites sind **nicht** interaktiv toggle-bar aus dem Browser. Änderungen erfordern Umbenennen des Verzeichnisses auf dem NAS (via separatem `rename`-Workflow — Regel 9: „File renames must be proposed, never auto-applied").

**CSS-Konvention für SVG-Icons:**
- Python-Konstanten: `SVG_*` in `server_utils.py` (inkl. `SVG_STAR`, `SVG_STAR_EMPTY`, `SVG_SHUFFLE`, `SVG_REPEAT`, `SVG_HISTORY`, `SVG_PLAYLIST`, `SVG_TRASH`, `SVG_CAST`, `SVG_FLAG_DE`, `SVG_FLAG_EN`, `SVG_FLAG_FR`, `SVG_FLAG_ES`, `SVG_FLAG_IT`, `SVG_FLAG_JA`, `SVG_FLAG_KO`, `SVG_FLAG_ZH`, `SVG_FLAG_PT`, `SVG_FLAG_RU`)
- JS-Variablen: `IC_*` in der generierten JS-Seite (inkl. `IC_STAR`, `IC_STAR_FILLED`, `IC_STAR_EMPTY`, `IC_SHUFFLE`, `IC_PLAYLIST`, `IC_TRASH`); `LANG_TO_FLAG` Mapping-Objekt für Sprach-Flaggen
- Alle SVGs nutzen `currentColor` für Theme-Kompatibilität (Ausnahme: Flaggen-SVGs verwenden Landesfarben)
- Kein Unicode/HTML-Entities (`&#9733;`, `&#9654;` etc.) — sie rendern auf iOS als farbige Emojis

## Language Tags (Sprach-Erkennung)

**Modul:** `streaming/core/language.py`

### Übersicht

Ordnernamen wie `Malcolm in the Middle (engl)` oder `Narcos (engl, gersub)` werden automatisch erkannt: Das Sprach-Tag wird aus dem Anzeigenamen entfernt und stattdessen als SVG-Flaggen-Badge neben dem Ordnernamen dargestellt. Bei Multi-Language-Ordnern (z.B. „Malcolm Mittendrin" ↔ „Malcolm in the Middle (engl)") werden die Varianten zu einer Karte zusammengeführt mit inline-Flaggen-Buttons für Direktnavigation.

### Backend

**`parse_language_tag(name)`** — Zentrale Funktion für Sprach-Tag-Erkennung. Gibt `(clean_name, lang_code)` zurück. Unterstützte Muster:
- Englisch: `(engl)`, `(english)`, `(eng)`, `(en)`, `(engl, gersub)`, `(engl, desub)`
- Deutsch: `(german)`, `(deutsch)`, `(ger)`, `(de)`
- Französisch: `(french)`, `(français)`, `(fr)`, `(french, ensub)`
- Spanisch: `(spanish)`, `(español)`, `(es)`, `(spanish, ensub)`
- Italienisch: `(italian)`, `(italiano)`, `(it)`
- Japanisch: `(japanese)`, `(jap)`, `(jp)`, `(jpn)`, `(ja)`, `(japanese, ensub)`
- Koreanisch: `(korean)`, `(ko)`, `(kor)`, `(korean, ensub)`
- Chinesisch: `(chinese)`, `(zh)`
- Portugiesisch: `(portuguese)`, `(pt)`
- Russisch: `(russian)`, `(ru)`

**`parse_subtitle_hint(name)`** — Extrahiert die Untertitelsprache aus zusammengesetzten Tags wie `(engl, gersub)` → `"de"`. Unterstützte Untertitel-Sprachen: de, en, fr, es, it, ja.

**`parse_language_full(name)`** — Convenience-Wrapper: gibt `(clean_name, audio_lang, subtitle_lang)` zurück.

**`strip_language_tag(name)`** — Entfernt Sprach-Tag, gibt bereinigten Namen zurück.

**`clean_folder_name(name)`** — Kombiniert `#`-Prefix-Entfernung (Favoriten) und Sprach-Tag-Entfernung zu einer einzigen Hilfsfunktion. Wird auch vom Video-Organizer (`series_rename_episodes`, `generate_overrides_yaml`) verwendet (ersetzt das bisherige `re.sub(r"#|\(engl\)", ...)`).

**`MediaItem.language`** — Feld `language: str = ""` (ISO 639-1 Code, z.B. `"en"`, `"de"`). Wird von `build_video_index()` über `parse_language_tag()` aus dem Ordnernamen befüllt. Audio-Items haben vorerst `language=""`.

**`MediaItem.subtitle_language`** — Neues Feld `subtitle_language: str = ""` (ISO 639-1 Code). Wird von `build_video_index()` über `parse_subtitle_hint()` aus dem Ordnernamen befüllt.

**`get_default_language()`** — Config-Funktion (`HOMETOOLS_DEFAULT_LANGUAGE`, Default `"de"`). Bestimmt welche Sprachvariante bei Klick auf eine Multi-Language-Karte standardmäßig navigiert wird.

**`FolderOverrides.language` / `subtitle_language`** — Optionale Felder in `hometools_overrides.yaml` (siehe `streaming/core/media_overrides.py`). Für Ordner **ohne** erkennbaren Sprach-Tag im Namen (z.B. `Malcolm Mittendrin`) kann manuell `language: "de"` und/oder `subtitle_language: "en"` gesetzt werden. `apply_overrides()` füllt diese Felder **nur** dann ein, wenn das Item keinen automatisch erkannten Wert hat — der via `parse_language_tag()` ermittelte Wert hat immer Vorrang (Auto-Detection ist die Wahrheit, Override ist Fallback). Strings werden beim Laden normalisiert (`strip().lower()`).

**`EpisodeOverride.language` / `subtitle_language`** — Per-Episode-Verfeinerung im `episodes:`-Block. Im Gegensatz zum Folder-Fallback gewinnt der Episoden-Override **explizit** über Folder-Wert *und* Auto-Detection (konsistent mit `title`/`season`/`episode`). Anwendungsfall: Ordner mit gemischtsprachigen Episoden (z.B. eine einzelne englische Folge in einer deutschen Serie).

**Override-Validator (`overrides_validator.py`)** — Linter für `hometools_overrides.yaml`-Dateien. CLI: `hometools validate-overrides [--library-dir PATH] [--json] [--fail-on-warning]`. Prüft pro Override-Datei: (1) Parse-Fehler (`error`), (2) unbekannte ISO 639-1 Codes gegen `KNOWN_LANGUAGE_CODES` aus `language.py` (`warning`), (3) Episode-Keys ohne passende Datei im Ordner (`warning`, fängt Tippfehler und Stale-Einträge nach Renames), (4) unbekannte Top-Level- und Per-Episode-Felder (`warning`, fängt Tippfehler wie `series_titel`), (5) leere Override-Dateien (`info`), (6) Episode-Keys mit Nicht-Media-Extensions (`info`), (7) Cross-Folder: `language_group` mit nur einem Mitglied (`info`). Rückgabetyp `ValidationReport` mit `to_dict()` für JSON-Output. Issues haben stabile `code`-Strings (`parse_error`, `unknown_language`, `unknown_episode_key`, `unknown_field`, `empty_override`, `non_media_extension`, `lonely_language_group`) für programmatische Suppression. Exit-Code: `0` clean, `1` bei Errors (oder Warnungen mit `--fail-on-warning`). Schreibt nichts — rein read-only.

**`KNOWN_LANGUAGE_CODES`** — Frozen-Set in `language.py` als Single Source of Truth für die unterstützten ISO 639-1 Codes (`en`, `de`, `fr`, `es`, `it`, `ja`, `ko`, `zh`, `pt`, `ru`). Neue Sprache hinzufügen = hier eintragen + SVG-Flag in `_svg.py` + JS-Flag-Mapping in `_player_js.py`.

**Snapshot-Version** auf v7 gebumpt (neues Feld `subtitle_language`).

### Frontend (JS)

**`cleanFolderName(name)`** — JS-Pendant zu `clean_folder_name()`. Strippt `#`-Prefix und Sprach-Tags via `_LANG_TAG_RE` Regex. Wird verwendet in:
- `contentsAt()` → `displayName`
- `leafName()` → Header-Titel
- `renderBreadcrumb()` → Breadcrumb-Labels

**`detectLangFromName(name)`** — Erkennt Sprachcode aus Ordnernamen (JS-Pendant zu `parse_language_tag()`).

**`detectSubLangFromName(name)`** — Erkennt Untertitelsprache aus zusammengesetzten Tags (JS-Pendant zu `parse_subtitle_hint()`).

**`langBadgesHtml(langs)`** — Rendert ein Array von Sprachcodes als kleine SVG-Flaggen-Badges.

**`compositeFlagHtml(mainLang, subLang)`** — Rendert eine zusammengesetzte Flagge: Hauptsprache als großes Flag mit optional kleinerem Untertitel-Flag in der rechten unteren Ecke.

**`LANG_TO_FLAG`** — JS-Mapping-Objekt `{ 'de': '<svg ...>', 'en': '<svg ...>', ... }`.

**`DEFAULT_LANG`** — JS-Variable mit der konfigurierten Standardsprache (`get_default_language()`).

**`contentsAt()`** — Aggregiert Sprachen und Untertitelsprachen pro Ordner aus:
1. `it.language`- und `it.subtitle_language`-Feldern der enthaltenen MediaItems
2. Ordnernamen-Erkennung via `detectLangFromName()` und `detectSubLangFromName()`

Ordner-Objekte enthalten jetzt: `languages: ['en']`, `subLang: 'de'`, `variants: [{name, lang, subLang, count}]`.

**Multi-Language-Folder-Cards** — Wenn ein Ordner Varianten hat (`variants.length > 1`):
- **Statt einfachem Zähler** zeigt die Karte inline Flaggen-Buttons (`.lang-select-btn`) mit zusammengesetzter Flagge + Episodenanzahl pro Variante.
- **Klick auf Flaggen-Button** → Direktnavigation in diese Sprachvariante.
- **Klick auf die Karte** (außerhalb der Buttons) → Navigation in die `DEFAULT_LANG`-Variante.
- **Play-Button** → Lang-Picker-Overlay (wie bisher).
- **Sortierung:** `DEFAULT_LANG` wird als erster Button angezeigt, Rest alphabetisch.

### CSS

```css
.lang-badge { display: inline-block; width: 18px; height: 12px; vertical-align: middle; margin-left: 4px; border-radius: 2px; overflow: hidden; }
.lang-badge svg { width: 18px; height: 12px; display: block; }
/* Composite flags */
.composite-flag { position: relative; display: inline-block; width: 22px; height: 14px; }
.composite-flag > svg { width: 18px; height: 12px; border-radius: 2px; }
.composite-flag-sub { position: absolute; bottom: -2px; right: -4px; width: 11px; height: 8px; border: 1px solid #1a1a1a; border-radius: 1px; }
/* Language select buttons */
.lang-select-btn { display: inline-flex; align-items: center; gap: 3px; padding: 2px 4px; border: 1px solid transparent; border-radius: 4px; background: none; cursor: pointer; }
.lang-select-btn:hover { border-color: var(--accent); background: rgba(255,255,255,0.05); }
```

### SVG-Flaggen

Minimale 18×12 SVGs für jede unterstützte Sprache: `SVG_FLAG_DE` (Schwarz-Rot-Gold), `SVG_FLAG_EN` (Union Jack), `SVG_FLAG_FR` (Trikolore), `SVG_FLAG_ES`, `SVG_FLAG_IT`, `SVG_FLAG_JA`, `SVG_FLAG_KO`, `SVG_FLAG_ZH`, `SVG_FLAG_PT`, `SVG_FLAG_RU`.

### Design-Regeln

- Sprach-Tags werden nur aus Ordnernamen erkannt, nicht aus Dateinamen (die haben eigene Codec-Stripping-Logik in `_title_from_filename`).
- Das `artist`-Feld (= roher Ordnername) bleibt **unverändert** — die Bereinigung erfolgt nur für die Anzeige.
- `data-folder` im HTML nutzt weiterhin den **rohen** Ordnernamen für korrekte Navigation.
- Multi-Language-Grouping gruppiert Ordner mit gleichem `displayName` zu einer einzigen Karte.
- Klick auf eine Multi-Language-Karte navigiert direkt in die `DEFAULT_LANG`-Variante (keine Overlay-Auswahl nötig).

### Tests

- `test_language.py`: 28+ Unit-Tests (parse_language_tag, strip_language_tag, clean_folder_name, parse_subtitle_hint, parse_language_full, build_video_index Integration)
- `test_streaming_player_ui.py`: 12+ neue Tests (JS-Funktionen, CSS, Breadcrumb, Folder-Card, composite flags)
- `test_feature_parity.py`: `TestLanguageParity` (4+ Tests: CSS, JS-Map, MediaItem-Feld, subtitle_language)

## Audit-Log & Change-Log

**Module:** `streaming/core/audit_log.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py` (`render_audit_panel_html`)

### Zweck

Jede Dateisystem-Änderung (Rating-Schreiben, künftig: Tag-Edits, Umbenennen) wird als unveränderlicher JSONL-Eintrag protokolliert. Das ermöglicht:
- **Undo** — Versehentliche Änderungen rückgängig machen (aus App oder Control Panel)
- **Bewertungsverlauf** — Alle Rating-Änderungen eines Songs nachvollziehen (inkl. Zeitstempel)
- **Audit** — Vollständige, manipulationssichere Protokollierung aller Writes

### Storage

```
<audit_dir>/audit.jsonl    ← append-only JSONL, eine JSON-Zeile pro Eintrag
```

Default: `.hometools-audit/` im Repository-Root (neben `src/`). Konfigurierbar via `HOMETOOLS_AUDIT_DIR`.

Das Audit-Log liegt **bewusst außerhalb** des Shadow-Cache (`.hometools-cache/`), da es permanente Daten enthält und `make clean` den gesamten Cache löscht. Beim ersten Server-Start wird automatisch migriert: Falls `<cache_dir>/audit/audit.jsonl` existiert und noch kein neues `<audit_dir>/audit.jsonl` vorhanden ist, wird die Datei kopiert (idempotent, nie überschreibend).

Atomic writes via `threading.Lock()`. Undo-Operation schreibt mit `tmp → rename`-Strategie (atomic replace).

### Eintrag-Schema

```python
AuditEntry(
    entry_id:    str,    # UUID — referenzierbar für Undo
    timestamp:   str,    # ISO 8601 UTC
    action:      str,    # "rating_write" | "tag_write" | "file_rename" | "file_move" | "file_delete"
    server:      str,    # "audio" | "video"
    path:        str,    # relativer Pfad in der Library
    field:       str,    # geändertes Feld ("rating", "title", …)
    old_value:   Any,    # Vorheriger Wert (None bei Erstschreib)
    new_value:   Any,    # Neuer Wert
    undo_payload: dict,  # Body für POST /api/<server>/audit/undo
    undone:      bool,   # True nach Undo
    undone_at:   str,    # ISO 8601 Zeitpunkt des Undos
)
```

### API-Endpoints

Beide Server bieten:
- `GET /api/<media>/audit?limit=&path_filter=&action_filter=&include_undone=` — gefilterte Einträge, neueste zuerst
- `POST /api/<media>/audit/undo` — `{ "entry_id": "…" }` → Undo anwenden + Eintrag als `undone=True` markieren
- `GET /audit` — HTML Control Panel

Undo-Unterstützung:
- **Audio-Server:** `rating_write` → `set_rating_stars(path, old_stars)` (format-bewusst: MP3/M4A/FLAC/OGG) + `patch_items()` + Cache-Invalidierung
- **Audio-Server:** `tag_write` → `write_track_tags(path, field=old_value)` + Cache-Invalidierung
- **Audio-Server:** `file_move` → `shutil.move(new_path, old_path)` (Rück-Verschiebung) + Cache-Invalidierung
- **Video-Server:** noch keine Write-Ops → `POST /api/video/audit/undo` gibt 422 zurück

### Control Panel (`/audit`)

Eigenständige Dark-Theme-HTML-Seite (generiert durch `render_audit_panel_html()`):
- Filterbar nach Dateiname und Aktion
- Tabelle: Zeitpunkt | Aktion | Datei | Änderung (`old → new`) | Rückgängig-Button
- Sterndarstellung für Ratings via SVG-Icons (`IC_STAR_FILLED`/`IC_STAR_EMPTY`) — identisch mit Player- und Inline-Rating-Sternen
- History-Link pro Datei via SVG-Clipboard-Icon (`IC_CLIPBOARD`)
- Alle Icons sind inline SVGs — keine Unicode/Emoji (Regel 13)
- `MEDIA_TYPE` JS-Variable steuert welchen API-Pfad das JS verwendet
- URL-Parameter `?path_filter=…` für Deep-Link in Bewertungshistorie einer Datei

### App-Integration (Undo-Toast)

Nach erfolgreichem Rating-Write gibt der Endpoint `entry_id` zurück. Das JS zeigt einen Toast mit "Rückgängig"-Button (5 s sichtbar). Klick ruft `undoRating(entryId, prevStars)` → `POST /api/audio/audit/undo` → Rating im Player-State zurückgesetzt.

### Design-Regeln

- Audit-Log ist **append-only** — Einträge werden nie gelöscht, nur als `undone` markiert.
- `old_value` wird **vor** dem Schreiben gelesen (via `get_rating_stars()` vor `set_rating_stars()`).
- `undo_payload.rating` enthält den alten Stern-Wert (0.0–5.0), `undo_payload.raw` den POPM-Raw-Wert. Undo verwendet `set_rating_stars(path, old_stars)` (format-bewusst), nicht `set_popm_rating()`.
- `undo_payload.entry_id` enthält die eigene UUID — beim Undo wird die ID aus dem Payload validiert.
- Fehler beim Log-Schreiben unterbrechen **nie** den eigentlichen Write-Vorgang (silent fail + logging).
- Beide Server lesen **denselben** JSONL (shared `audit_dir`) — Audio-Ratings sind im Video-Control-Panel sichtbar.
- **⚠️ Escaping-Pitfall:** In Python-Triple-Quoted-Strings (`"""..."""`) werden `\'`-Escape-Sequenzen zu `'` verarbeitet. Niemals `onclick="..."` mit `\'`-Escaping in Python-Strings erzeugen — führt zu kaputtem JS (`''` statt `\'`) und einem Komplettausfall des `<script>`-Tags. Stattdessen **immer `createElement` + `addEventListener`** für DOM-Interaktionen aus Python-generierten Strings verwenden.

### Service-Worker-Routing (Bugfix 2026-05-16)

**Problem:** Die SW-Fetch-Handler-Reihenfolge war falsch:
```
streaming-check (includes('/audio/'))  ← kam zuerst, fing /api/audio/audit ab
api-check (startsWith('/api/'))         ← wurde nie erreicht für audio/video-API-Pfade
```
Der Streaming-Handler hat keinen `503`-Fallback — Netzfehler des Servers propagierten direkt, lösten `.catch` im Audit-JS aus → Toast "Fehler beim Laden der Einträge".

**Fix:** API-Check (`startsWith('/api/')`) kommt jetzt **vor** dem Streaming-Check. Zusätzlich verwendet der Streaming-Check jetzt `startsWith('/audio/')` statt `includes('/audio/')` (präziser). SW-Cache-Version auf `hometools-v8` erhöht.

**Fehlerbehandlungsverbesserung:** Audit-JS-`loadEntries` gibt jetzt auch bei non-OK HTTP-Antworten (z.B. `503`) den HTTP-Statuscode im Toast aus und zeigt einen "Erneut versuchen"-Button in der Tabelle.

### Exception-Safety in `audit_log.py` (Bugfix 2026-05-16)

**Problem:** `_audit_path(audit_dir)` wurde in `load_entries()`, `get_entry()` und `append_entry()` **außerhalb** des `try/except` aufgerufen. `_audit_path` versucht `audit_dir.mkdir(parents=True, exist_ok=True)` — schlägt das fehl (z.B. Berechtigungsfehler, Read-only-FS), propagiert der `OSError` durch den FastAPI-Endpoint und erzeugt eine `500`-Antwort. Im Browser: "Fehler beim Laden der Einträge".

**Fix:** In allen drei Funktionen wird `_audit_path` jetzt in einem eigenen `try/except`-Block aufgerufen. Bei Fehler: `load_entries` → `[]`, `get_entry` → `None`, `append_entry` → silent return (mit Logging). Alle drei Funktionen sind nun ausnahmslos exception-safe.

### `audit_dir`-Parameter in `create_app()` (Refactor 2026-05-16)

**Motivation:** Tests, die `create_app()` ohne `audit_dir` aufrufen, verwendeten die **echte** `.hometools-audit/` des Repos. Wiederholte Testläufe und Debug-Sessions erzeugten dadurch hunderte Test-Einträge im echten Audit-Log.

**Änderung:** `create_app(audit_dir=None)` in `audio/server.py` und `video/server.py` — wenn `None`, fällt `get_audit_dir()` zurück (Standardverhalten unverändert). Tests übergeben `audit_dir=tmp_path / "audit"` direkt, ohne Monkeypatching. Neuer Test: `test_audio_audit_endpoint_inaccessible_dir_returns_empty` verifiziert die exception-safe Behavior.

## Songwertung Schreiben (POPM-Write, Audio-only)

**Module:** `streaming/audio/server.py` (Endpoint), `audio/metadata.py` (`set_rating_stars`), `streaming/core/server_utils.py` (UI + JS)

### Überblick

Zusätzlich zur Anzeige des Ratings (`.rating-bar` auf dem Thumbnail) können Nutzer im Audio-Player aktiv eine Bewertung vergeben. Der Mechanismus ist analog zu `enable_shuffle` — Feature-Flag im Core, nur Audio-Server aktiviert ihn.

### Feature-Flag

```python
# render_media_page(enable_rating_write=True)   →  Audio
# render_media_page()                            →  Video (Rating nur anzeigen)
```

`render_media_page()` und `render_player_js()` haben einen neuen Parameter `enable_rating_write: bool = False`. Er steuert:
1. Ob `RATING_WRITE_ENABLED = true` in der JS-Payload gesetzt wird (ermöglicht Klick-Interaktion)
2. Den injizier­ten `RATING_API_PATH = '/api/<media>/rating'` (abgeleitet aus `api_path`)

### UI

Ein `<div id="player-rating" hidden>` befindet sich in der `.player-info`-Sektion beider Player-Bar-Varianten (classic + waveform). Beim Abspielen eines Tracks füllt `renderPlayerRating(stars)` es mit 5 klickbaren `<button class="player-rating-star">`-Elementen.

- **Filled Star:** `IC_STAR_FILLED` (Python: `SVG_STAR`) — goldgelb bei aktivem Rating
- **Empty Star:** `IC_STAR_EMPTY` (Python: `SVG_STAR_EMPTY`) — Outline-Stern für nicht-aktive Felder
- **Hover-Preview:** `mouseover`-Delegation färbt Sterne bis zum Cursor vorschauweise
- **Klick → `setRating(n)`** — sendet `POST /api/audio/rating` und zeigt Toast

### API-Endpoint

`POST /api/audio/rating` in `audio/server.py`:
- Body: `{ "path": "<relative_path>", "rating": 0–5 }`
- Dispatcht format-bewusst via `set_rating_stars(path, stars)`:
  - MP3 → `set_popm_rating()` (WMP-Standard: 0→0, 1→1, 2→64, 3→128, 4→196, 5→255)
  - M4A/MP4 → `_write_m4a_rating()` (Freeform-Atom, 0–100 Skala)
  - FLAC/OGG → `_write_vorbis_rating()` (FMPS_RATING + RATING)
- Invalidiert `_audio_index_cache` nach erfolgreichem Schreiben
- Gibt `{ "ok": bool, "rating": float, "raw": int }` zurück

### JS-Architektur

```
RATING_WRITE_ENABLED: bool   ← aus enable_rating_write
RATING_API_PATH: str         ← '/api/audio/rating' (abgeleitet aus api_path)
renderPlayerRating(stars)    ← füllt #player-rating mit 5 Sternen
setRating(stars)             ← POST → API → Toast + rebuild weighted shuffle queue
```

### Design-Regeln

- Der `#player-rating`-Container ist **immer** im HTML (auch ohne `enable_rating_write`), aber `pointerEvents: none` wenn nicht schreibbar — konsistentes Layout.
- Die Rating-Sterne sind **keine** Read-Only-Anzeige des gespeicherten Ratings — nur der Balken (`.rating-bar`) übernimmt diese Rolle in der Liste.
- Nach erfolgreichem Schreiben: `t.rating` im lokalen JS-State aktualisiert, Shuffle-Queue neu aufgebaut (falls `weighted`-Modus aktiv).
- `set_rating_stars()` dispatcht automatisch auf das richtige Format (MP3/M4A/FLAC/OGG). Der Endpoint muss keine Dateiendung prüfen.

## Zuletzt gespielt / Continue Watching

**Module:** `streaming/core/progress.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py`, `config.py`

### Übersicht

Beim Öffnen der App auf der Startseite (Root-Ordneransicht) wird eine horizontale Scroll-Leiste „Zuletzt gespielt" eingeblendet, die die zuletzt abgespielten Titel/Videos zeigt — mit Fortschrittsbalken. Klick startet direkt an der gespeicherten Position.

### Backend

**`get_recent_progress(cache_dir, limit)`** in `progress.py`:
- Liest alle Einträge aus `playback_progress.json`
- Sortiert nach `timestamp` absteigend (neueste zuerst)
- Gibt `[{relative_path, position_seconds, duration, timestamp, ...}]` zurück

**`GET /api/<media>/recent?limit=10`** (Audio + Video):
- Ruft `get_recent_progress()` auf
- Mergt mit Katalog via `get_cached()` (non-blocking) — Einträge ohne Katalog-Match werden übersprungen
- Berechnet `progress_pct = position_seconds / duration * 100`
- Gibt `{items: [{...MediaItem-Felder, position_seconds, duration, progress_pct, timestamp}]}` zurück

### Frontend

**`RECENT_API_PATH`** — JS-Variable injiziert aus `api_path` (z.B. `'/api/audio/recent'`)

**`loadRecentlyPlayed()`** — wird in `showFolderView()` nur auf der Root-Ebene (`isRoot && allItems.length > 0`) aufgerufen:
- Fetcht `RECENT_API_PATH?limit=10`
- Rendert Karten mit Thumbnail, Titel, Artist, Fortschrittsbalken
- Klick → navigiert in den Ordner des Tracks, startet `playItem()`, seekt zur gespeicherten Position via `canplay`-Event

**HTML:** `<div id="recent-section" hidden>` vor dem `folder-grid`, wird von JS sichtbar gemacht wenn Einträge vorhanden

**Design-Regeln:**
- Sektion startet `hidden` — erscheint erst wenn JS Daten geladen hat
- Wird bei Sub-Ordner-Navigation ausgeblendet
- Kein Blocking: `get_cached()` gibt leere Liste zurück wenn noch kein Snapshot, dann bleibt die Sektion leer/hidden

## Hörbuch-Erkennung

**Module:** `config.py` (`get_audiobook_dirs`, `is_audiobook_folder`), `streaming/core/server_utils.py`

### Übersicht

Ordner die als Hörbücher erkannt werden, erhalten in der Ordner-Grid-Ansicht eine blaue Einfärbung (`.audiobook-folder`).

### Erkennung

`is_audiobook_folder(folder_name, dirs)` — case-insensitiver Präfix-Match:
- Default-Präfixe: `Hörbuch`, `Hörbücher` (ü≠u → separater Eintrag!), `Hörspiel`, `Audiobook`, `Spoken Word`
- Override via `HOMETOOLS_AUDIOBOOK_DIRS` (kommagetrennt)
- **Wichtig:** Umlauts im Quellcode als Unicode-Escapes (`\u00f6`, `\u00fc`) für Windows-Kompatibilität

**`AUDIOBOOK_DIRS`** — JS-Array injiziert via `__import__("hometools.config"...)` bei `render_player_js()`-Aufruf, wird in `showFolderView()` per `AUDIOBOOK_DIRS.some(...)` geprüft.

### CSS

`.audiobook-folder .folder-name { color: #a0c4ff; }` — blaue Schriftfarbe als subtiler Hinweis


**Module:** `streaming/core/server_utils.py` (JS + HTML + CSS)  
**Aktiviert von:** `streaming/audio/server.py` (über `enable_shuffle=True` in `render_media_page`)

### Überblick

Der Shuffle-Modus ist ausschließlich im **Audio-Server** aktiviert, aber vollständig im **Shared Core** (`server_utils.py`) implementiert — konform mit Architektur-Regel 1 (keine Duplikation). Der Video-Server erhält den Feature-Flag nicht (`enable_shuffle=False`, default).

### Feature-Flag

```python
# render_media_page(enable_shuffle=True)  →  Audio
# render_media_page()                     →  Video (kein Shuffle-Button)
```

`render_media_page()` hat einen neuen Parameter `enable_shuffle: bool = False`. Er wird an `render_player_js()` weitergegeben und steuert:
1. Ob der Shuffle-Button `<button id="btn-shuffle">` im Player-Bar HTML gerendert wird
2. Ob `SHUFFLE_ENABLED = true` in der JS-Payload gesetzt wird

### Modi

| Modus | Aktivierung | Verhalten |
|---|---|---|
| **Aus** (`false`) | Klick wenn aktiv (weighted → aus) | Sequentielle Reihenfolge |
| **Zufällig** (`'normal'`) | 1. Klick | Fisher-Yates-gemischte Queue |
| **Gewichtet** (`'weighted'`) | 2. Klick oder Long-Press (600 ms) | Tracks mit höherem Rating (`POPM`) erscheinen häufiger |

### JS-Architektur

```
shuffleMode: false | 'normal' | 'weighted'
shuffleQueue: []       ← vorberechnete Index-Reihenfolge
shufflePos: -1         ← aktueller Queue-Zeiger

fisherYates(arr)        ← uniformes Fisher-Yates-Shuffle
buildNormalQueue()      ← uniforme Permutation aller Indizes
buildWeightedQueue()    ← gewichtete Queue: rating 0→Gewicht 1, rating 5→Gewicht 6
rebuildShuffleQueue()   ← bei Playlist-Wechsel und Filter-Änderung
nextIndex()             ← nächster Titel (shuffleQueue oder sequentiell)
prevIndex()             ← vorheriger Titel (shuffleQueue oder sequentiell)
cycleShuffle()          ← aus → normal → weighted → aus (localStorage-Persistenz)
activateWeightedShuffle() ← direkter Sprung zu weighted (Long-Press)
updateShuffleBtn()      ← CSS-Klassen `.shuffle-active` / `.shuffle-weighted`
```

### Offline-Kompatibilität

Die Shuffle-Queue wird **client-seitig** aus `filteredItems` berechnet — keine Netzwerkanfrage nötig. Dadurch funktioniert Shuffle auch im vollständigen Offline-Modus (z. B. wenn die App nur über IndexedDB-Downloads gespielt wird). `rebuildShuffleQueue()` wird nach jedem Filter-Aufruf (`renderTracks`) neu aufgebaut.

### CSS

```css
.ctrl-btn.shuffle-btn.shuffle-active   { color: var(--accent); }
.ctrl-btn.shuffle-btn.shuffle-weighted { color: var(--accent); background: rgba(29,185,84,0.15); }
```

### Button-Interaktion

- **Klick** → `cycleShuffle()` (aus → normal → weighted → aus)
- **Long-Press (600 ms)** → `activateWeightedShuffle()` mit Toast-Meldung
- **localStorage** `ht-shuffle-mode` speichert den Modus sitzungsübergreifend

### Playlist-Integration

`showPlaylist()` ruft `rebuildShuffleQueue(startIdx)` auf, wenn Shuffle aktiv ist. Der `startIndex` wird an die erste Position der Queue gestellt, sodass der aktuelle Titel immer als erstes gespielt wird. `renderTracks()` ruft ebenfalls `rebuildShuffleQueue()` auf, wenn `filteredItems` sich durch Suche/Sortierung ändert.

### Design-Regeln

- Shuffle-Button erscheint **nur** im Audio-Server HTML.
- Shuffle-Logik lebt ausschließlich in `server_utils.py` (Core) — nicht in `audio/server.py`.
- Keine API-Endpunkte für Shuffle — nur client-seitig (offline-fähig).
- `filteredItems` bestimmt die Queue-Basis — Filter und Shuffle kooperieren korrekt.

## Repeat-Modus (Off / Alle / Einzeltitel)

**Modul:** `streaming/core/server_utils.py` (Shared Core, Audio + Video)

Wiederholungs-Button im Player-Bar mit drei Modi.

### Feature-Flag

```python
# render_media_page(enable_repeat=True)  →  Audio + Video
```

`enable_repeat: bool = False` in `render_player_js()` / `render_media_page()`. Steuert:
1. Ob der Button `<button id="btn-repeat">` gerendert wird
2. Ob `REPEAT_ENABLED = true` in der JS-Payload gesetzt wird

### Modi

| Modus | State | `nextIndex()` am Listenende | `playNextItem()` bei `ended` |
|---|---|---|---|
| **Aus** (`false`) | Kein Wiederholungssymbol | Gibt `-1` zurück → Wiedergabe stoppt | Stoppt (`wasPlaying = false`) |
| **Alle** (`'all'`) | Grünes Repeat-Icon | Wraps auf `0` zurück | Nächster Track normal |
| **Einzeltitel** (`'one'`) | Grünes Repeat-Icon + „1" | N/A (wird nicht erreicht) | `player.currentTime = 0; player.play()` |

### JS-Architektur

```
repeatMode: false | 'all' | 'one'

IC_REPEAT          ← Standard Repeat-SVG
IC_REPEAT_ONE      ← Repeat-SVG mit „1"-Text-Overlay

cycleRepeat()       ← off → all → one → off (localStorage-Persistenz)
updateRepeatBtn()   ← CSS-Klassen .repeat-active / .repeat-one, innerHTML ← IC_REPEAT / IC_REPEAT_ONE
```

### Interaktion mit anderen Features

- **Queue:** Hat Vorrang. `playNextItem()` prüft erst `dequeueNext()`, dann `repeatMode`.
- **Shuffle:** Koexistiert. Bei `repeat-all` + Shuffle → Shuffle-Queue wraps normal. Bei `repeat-one` → Shuffle irrelevant (Track startet neu).
- **Crossfade:** Bei `repeat-one` unterdrückt: `repeatMode !== 'one'` Guard im `timeupdate` Crossfade-Trigger.
- **localStorage:** `ht-repeat-mode` speichert den Modus sitzungsübergreifend.

### CSS

```css
.ctrl-btn.repeat-btn.repeat-active { color: var(--accent); }
.ctrl-btn.repeat-btn.repeat-one    { color: var(--accent); background: rgba(29,185,84,0.15); border-radius: 50%; }
```

### Design-Regeln

- Repeat ist in **beiden** Servern aktiviert (Audio + Video) — eine Serie wiederholen ist ebenso nützlich wie ein Lieblingslied.
- Repeat-Logik lebt ausschließlich in `server_utils.py` (Shared Core).
- Keine API-Endpunkte — rein client-seitig.
- `nextIndex()` gibt bei `repeat-off` am Listenende `-1` statt `0` zurück — das ist die einzige Verhaltensänderung gegenüber dem bisherigen Default (immer wrappen).

## Header-Navigation

Der Header besteht aus drei Elementen (Audit-Button ist jetzt im Tools-Panel):

| Element | ID/Klasse | Funktion |
|---|---|---|
| `<button class="logo-home-btn" id="header-logo">` | Emoji (🎬 / 🎵) | Klick → **immer** zurück zur Startseite (`currentPath = ''; showFolderView()`) |
| `<span class="logo-title" id="header-title">` | App-Titel | Reiner Text, **kein Link** — zeigt Ordner-Tiefe oder App-Titel |
| `<button class="back-btn" id="back-btn">` | SVG-Pfeil | Zurück eine Ebene |

**Design-Regeln:**
- Emoji-Button (`logo-home-btn`) navigiert immer zur Root-Ansicht — auch wenn man bereits dort ist.
- `headerTitle` im JS zeigt den aktuellen Pfad-Leaf-Name oder `originalTitle` (App-Titel). Der Titel-Span hat keinen eigenen Click-Handler.
- `originalTitle` wird aus `headerTitle.textContent` gelesen — enthält nur den Titel-Text ohne Emoji.
- Der Audit-Button (`<a class="audit-btn" id="audit-btn" href="/audit">`) ist **im Tools-Panel** oben rechts platziert (`.tools-panel-header`), nicht im Header. Er ist ein `<a>`-Tag — ermöglicht normales Browser-Navigationsverhalten.

## Player-Sichtbarkeit (Bug-Fix: currentSrc statt currentIndex)

**Problem:** `showFolderView()` versteckte die Player-Bar mit `if (currentIndex < 0) playerBar.classList.add('view-hidden')`. Das führte dazu, dass der Player nach Navigation in die Offline-Bibliothek (→ `showPlaylist()` setzt `currentIndex = -1`) und zurück zur Startseite unsichtbar wurde, obwohl noch Musik spielte.

**Fix:** Alle 4 Stellen in `showFolderView()`, `showLoadingState()` und `showCatalogLoadError()` wurden auf `if (!player.currentSrc) playerBar.classList.add('view-hidden')` umgestellt.

**Semantik:**
- `player.currentSrc === ''` → nichts wurde je geladen → Player-Bar verbergen ✓
- `player.currentSrc !== ''` → Quelle geladen (auch wenn pausiert) → Player-Bar sichtbar ✓

**Design-Regel:** Niemals `currentIndex` zur Bestimmung der Player-Sichtbarkeit verwenden — `currentIndex` ist playlist-lokal und wird bei Navigation (`showPlaylist()`) zurückgesetzt. `player.currentSrc` spiegelt den tatsächlichen Lade-Zustand des Media-Elements wider.

## Metadaten-Bearbeitung (Inline-Edit-Modal, Audio-only)

**Module:** `streaming/core/server_utils.py` (UI + JS), `streaming/audio/server.py` (Endpoint), `audio/metadata.py` (`write_track_tags`), `streaming/core/audit_log.py` (`log_tag_write`)

### Überblick

Nutzer können Titel, Interpret und Album direkt aus der Track-Liste heraus bearbeiten. Analog zu `enable_rating_write` ist das Feature hinter einem Feature-Flag (`enable_metadata_edit`) implementiert — aktiviert nur im Audio-Server.

### Feature-Flag

```python
# render_media_page(enable_metadata_edit=True)   →  Audio
# render_media_page()                             →  Video (kein Edit-Button)
```

`render_media_page()` und `render_player_js()` haben beide den neuen Parameter `enable_metadata_edit: bool = False`. Er steuert:
1. `METADATA_EDIT_ENABLED = true` im generierten JS
2. `METADATA_EDIT_PATH = '/api/<media>/metadata/edit'` (abgeleitet aus `api_path`)
3. `IC_EDIT` — Bleistift-SVG-Icon als JS-Variable
4. Einen Edit-Button (`.track-edit-btn`) pro Track in der Liste
5. Das Modal-HTML im HTML-Template (`edit-modal-backdrop`)

### UI-Fluss

1. Klick auf Bleistift-Button → `openEditModal(idx)` → Modal öffnet sich, vorausgefüllt mit aktuellem Titel/Interpret aus `filteredItems[idx]`
2. Album-Feld startet leer (nicht im `MediaItem`-Schema)
3. **Bewertungs-Sterne** werden mit dem aktuellen Rating des Tracks vorausgefüllt (`renderEditModalRating(t.rating)`). Sichtbar nur wenn `RATING_WRITE_ENABLED`. Klick auf Stern setzt Rating, erneuter Klick auf gleichen Stern setzt auf 0 zurück.
4. Speichern → `submitEditModal()` → `POST /api/audio/metadata/edit` + ggf. `POST /api/audio/rating` (parallel via `Promise.all`)
5. Bei Erfolg: lokaler JS-State (`filteredItems`, `allItems`) aktualisiert, Track-Liste neu gerendert, Player-Anzeige aktualisiert (wenn aktuell spielender Track), gewichtete Shuffle-Queue neu aufgebaut
6. `closeEditModal()` bei Backdrop-Klick, Escape-Taste oder Cancel-Button
7. Enter in Eingabefeld triggert `submitEditModal()`

### CSS-Klassen

- `.track-edit-btn` — Kreisförmiger Button neben `.track-pin-btn`, nur sichtbar wenn `METADATA_EDIT_ENABLED`
- `.edit-modal-backdrop` — Fixed-Overlay, schließt bei Klick außerhalb
- `.edit-modal` — Modal-Panel (max 480px Breite)
- `.edit-field` — Label + Input-Zeile
- `.edit-modal-rating` — Flex-Container für 5 Rating-Sterne im Modal
- `.edit-modal-rating-star` — Einzelner klickbarer Stern (22×22 SVG, `.active` = gold, `.hover` = gold)
- `.edit-modal-actions` — Cancel + Save Buttons

### JS-Funktionen (Edit-Modal)

- `_editModalRating` — State-Variable: aktuell im Modal ausgewählte Stern-Anzahl (0–5)
- `renderEditModalRating(stars)` — Rendert 5 Sterne in `#edit-modal-rating`, setzt `_editModalRating`
- `_initEditModalRatingEvents()` — IIFE: Hover-Preview + Klick-Handler auf dem Rating-Container
- `openEditModal(idx)` — Füllt alle Felder inkl. Rating vor, versteckt Rating-Feld wenn `!RATING_WRITE_ENABLED`
- `submitEditModal()` — Parallel: Metadata-POST + Rating-POST (nur wenn Rating geändert) via `Promise.all`

### API-Endpoint

`POST /api/audio/metadata/edit` in `audio/server.py`:
- Body: `{ "path": "<relative_path>", "title": "...", "artist": "...", "album": "..." }`
- Fehlende / `null`-Felder werden übersprungen (kein Überschreiben mit leeren Werten)
- Schreibt via `write_track_tags(path, title=..., artist=..., album=...)` aus `audio/metadata.py`
- Loggt jede geänderte Eigenschaft als separaten `AuditEntry` via `log_tag_write()`
- Gibt `{ "ok": bool, "entry_ids": ["uuid", ...] }` zurück

### `write_track_tags()` — Format-Unterstützung

- **MP3** — ID3v2: `TIT2`, `TPE1`, `TALB`
- **M4A/MP4/AAC** — iTunes Atoms: `©nam`, `©ART`, `©alb`
- **FLAC/OGG/Opus/WMA** — Vorbis Comments / ASF: `title`, `artist`, `album`
- Alle anderen Formate → `False` (kein Crash)
- `None`-Felder werden übersprungen (kein Löschen bestehender Tags)

### Audit-Integration

Jede geänderte Eigenschaft (`title`, `artist`, `album`) erzeugt einen eigenen `AuditEntry` mit:
- `action: "tag_write"`
- `undo_payload`: Body für `POST /api/audio/metadata/edit` mit altem Wert

### Design-Regeln

- Das Feature ist **Audio-only** — Video hat keine `write_track_tags`-Implementierung und kein `enable_metadata_edit`.
- Album ist **nicht** in `MediaItem` — das Feld wird im Modal optional angeboten, startet leer.
- Bei Erfolg: `_audio_index_cache.invalidate()` → nächste API-Abfrage liefert frische Daten.
- **Kein Auto-Refresh der Track-Liste** — der lokale JS-State wird direkt aktualisiert (kein Round-Trip zum Server nötig).
- Der Edit-Button ist nur in der Track-Liste sichtbar, nicht im Player-Bar.

---

## Thumbnail-Größen je Ansichtsmodus

### Regel

Kleine Thumbnails werden **ausschließlich in der Listenansicht** (viewMode `'list'`) verwendet. In allen anderen Ansichten (Galerieansicht `'grid'`, Dateinamen-Ansicht `'filenames'`) werden immer die großen Thumbnails (`thumbnail_lg_url`) bevorzugt – kleine Thumbnails (`thumbnail_url`) dienen dabei als Fallback.

Gleiches gilt für den **Player-Bar-Thumb**: Er zeigt immer die große Version (`thumbnail_lg_url || thumbnail_url`), da er kein Listenkontext ist.

### Umsetzung (`server_utils.py`)

| Kontext | list | grid | filenames |
|---|---|---|---|
| Ordner-Kacheln im Folder-Grid | `thumbnail_url` | `thumbnail_lg_url` | `thumbnail_lg_url` |
| Datei-Kacheln im Folder-Grid | `thumbnail_url` | `thumbnail_lg_url` | `thumbnail_lg_url` |
| Track-Liste (innerhalb Ordner) | `thumbnail_url` | — | — |
| Player-Bar-Thumb | `thumbnail_lg_url \|\| thumbnail_url` | ← immer | ← immer |

Bedingung im JS: `viewMode !== 'list' ? (lg || sm) : sm`

---

## Zuletzt gespielt – Konfiguration und Server-Unterschiede

### Verhalten je Server

| Server | Zuletzt-gespielt-Sektion | Begründung |
|---|---|---|
| **Audio** | **Aus** (`enable_recent=False`) | Keine Empfehlungsliste; Hörbücher steigen via Progress-API automatisch am letzten Punkt ein |
| **Video** | **An** (`enable_recent=True`, Standard) | Zeigt bis zu N zuletzt gesehene Folgen mit Fortschrittsbalken |

### Konfiguration (`.env`)

Alle Werte steuern den `/api/video/recent`-Endpunkt im Video-Server:

| Variable | Default | Bedeutung |
|---|---|---|
| `HOMETOOLS_RECENT_VIDEO_LIMIT` | `3` | Max. angezeigte Folgen |
| `HOMETOOLS_RECENT_MAX_AGE_DAYS` | `14` | Folgen älter als N Tage werden ausgeblendet |
| `HOMETOOLS_RECENT_MAX_PER_SERIES` | `1` | Max. Folgen pro Serie (nur die neueste wird gezeigt) |

### Technische Umsetzung

- `render_player_js()` und `render_media_page()` erhalten neuen Parameter `enable_recent: bool = True`.
- Wenn `False`: kein `<div id="recent-section">` im HTML-Output, kein `loadRecentlyPlayed()`-Aufruf im JS, kein `RECENT_API_PATH` benötigt.
- `render_audio_index_html()` setzt explizit `enable_recent=False`.
- Die Konfigurationsfunktionen `get_recent_video_limit()`, `get_recent_max_age_days()`, `get_recent_max_per_series()` leben in `config.py`.

---

## Ansichtsumschalter (view toggle) – zwei Modi

Der Header-Button `#view-toggle` schaltet zyklisch durch zwei Modi:

| Modus | CSS-Klassen auf `#folder-grid` | Thumbnail | Tooltip |
|---|---|---|---|
| `'list'` | `list-mode` | Klein | „Listenansicht — Klick für Kachelansicht" |
| `'grid'` | — | Groß | „Kachelansicht — Klick für Listenansicht" |

Reihenfolge: `list → grid → list`

Gespeichert in `localStorage` unter `ht-view-mode`. Ein gespeichertes `'filenames'` wird beim Laden auf `'list'` gemappt.

### Tools-Modus-Override

Wenn im Tools-Panel mindestens ein Tool aktiv ist (`_anyToolActive()` = true), wird der View-Toggle **gesperrt**:

- `folderGrid` erhält `list-mode filenames-mode` unabhängig vom gespeicherten `viewMode`
- Ordner- und Track-Karten zeigen den rohen Dateinamen (`f.name` / `t.relative_path`-Basename) statt des Display-Namens
- Der Toggle-Button erhält `.view-toggle-locked` (CSS: `opacity: 0.45; cursor: default; pointer-events: none`)
- Beim Deaktivieren aller Tools wird die normale Ansicht wiederhergestellt

**DnD-Reorder ist nur im `list`-Modus aktiv** (+ Playlist-Kontext). In `grid` ist Drag-and-Drop deaktiviert — Klick auf einen Track spielt ihn ab.

---

## Sort-Option „Liste" (custom)

Die Sort-Dropdown erhält eine neue Option `<option value="custom">Liste ⇅</option>`:

- **In Playlist-Kontext** (`_currentPlaylistId` gesetzt): Behält die Server-Reihenfolge bei (kein Re-Sort). Ermöglicht DnD-Reorder.
- **In Filesystem-Ordner:** Sortiert nach benutzerdefinierter Reihenfolge (server-seitig gespeichert via `custom_order.py`, `localStorage` als Offline-Fallback). Ermöglicht DnD-Reorder.

---

## Genre-Tags (Audio)

**Module:** `audio/metadata.py` (`get_genre`), `streaming/audio/catalog.py` (`build_audio_index`), `streaming/core/models.py` (`MediaItem.genre`), `streaming/core/server_utils.py` (Genre-Filter-Chip)

### Übersicht

Genre-Tags werden aus den eingebetteten Metadaten von Audio-Dateien gelesen und im `MediaItem.genre`-Feld gespeichert. In der UI ermöglicht ein Genre-Filter-Chip das Filtern der Track-Liste nach Genre.

### Tag-Lesung

`get_genre(p: Path) -> str` in `audio/metadata.py`:
- MP3: ID3 `TCON` Frame
- M4A/MP4: `©gen` Atom
- FLAC/OGG: `genre` / `GENRE` Vorbis Comment
- Fehlertolerant: gibt `""` zurück bei fehlenden Tags oder Lesefehlern

### MediaItem-Feld

`genre: str = ""` — am Ende der Felder in `MediaItem` (frozen dataclass). Video-Items haben immer `genre=""`.

### Designregeln

1. Genre-Lesung erfolgt im `build_audio_index()` — kein separater API-Call nötig.
2. Genre wird im JSON-Payload von `/api/audio/items` mitgeliefert (Feld `genre` in jedem Item).
3. Der Genre-Filter-Chip versteckt sich automatisch (`display: none`) wenn keine Items mit Genre-Tag in der aktuellen Playlist sind — z.B. im Video-Server.
4. Genre-Filter verwendet exakte Gleichheit (`t.genre === filterGenre`), nicht Substring-Match.
5. Zyklische Auswahl: Klick auf den Chip durchläuft alphabetisch sortierte Genres → zurück zu „alle".

---

## Schnellfilter-Chips (Quick-Filter)

In der Filter-Bar des Track-View sind Pill-Buttons, die den Track-Filter um **Bewertungs-Filter**, **Favoriten-Filter** und **Genre-Filter** erweitern.

### UI-Elemente

| Element | ID | CSS-Klasse | Verhalten |
|---|---|---|---|
| Bewertungs-Chip | `#filter-rating` | `.filter-chip` / `.active` | Klick zyklisch: 0→1→2→3→4→5→0 (Minimum-Sterne) |
| Favoriten-Chip | `#filter-fav` | `.filter-chip` / `.active` | Toggle: nur Favoriten (Shortcuts-API) anzeigen |
| Genre-Chip | `#filter-genre` | `.filter-chip` / `.active` | Klick zykliert durch verfügbare Genres → leer (alle). Versteckt wenn keine Items mit Genre-Tag vorhanden. |

### Designregeln
- CSS-Klasse `.filter-chip` ist eigenständig (kein Erbe von `.ctrl-btn`).
- Alle Filter werden mit `AND`-Logik kombiniert (Needle-Search + Rating + Favorites + Genre).
- Zustand wird in `localStorage` gespeichert: `ht-filter-rating` (0–5), `ht-filter-fav` (`'1'`/`''`), `ht-filter-genre` (Genre-Name oder leer).
- `updateFilterChips()` synchronisiert Beschriftung + aktiven Zustand aller Buttons. Der Genre-Chip wird nur angezeigt wenn `playlistItems` Genre-Tags enthalten.
- Nach dem Laden von Favoriten via `loadFavorites()` wird bei aktivem Favoriten-Filter automatisch `applyFilter()` erneut aufgerufen.
- Filter bleiben beim Wechsel zwischen Ordnern aktiv (intentional; der Nutzer hat sie bewusst gesetzt).
- Icons: `IC_STAR_FILLED` / `IC_STAR_EMPTY` für den Bewertungs-Chip, `IC_PIN` für den Favoriten-Chip. Genre-Chip hat kein Icon (nur Text).

---

## Songtexte (Lyrics-Panel)

Embedded Songtexte (ID3 USLT, M4A ©lyr, FLAC/OGG LYRICS/UNSYNCEDLYRICS) können im Player angezeigt werden.

### Module
- **Lese-Logik:** `get_lyrics(p: Path) -> str | None` in `audio/metadata.py` (vorhanden).
- **Backend-Endpoint:** `GET /api/audio/lyrics?path=<relative_path>` → `{"path": str, "lyrics": str|null, "has_lyrics": bool}`.
- **Frontend:** Bottom-Drawer `.lyrics-panel` mit glatter CSS-Transition (`translateY`); Inhalt lädt lazy beim ersten Öffnen.

### SVG-Konstanten
- `SVG_LYRICS` (Python) / `IC_LYRICS` (JS) — Seiten-Icon (file-text).

### JS-Design
- `LYRICS_ENABLED` JS-Variable steuert ob Lyrics-Button + Panel gerendert werden (`True` nur im Audio-Server).
- `LYRICS_API_PATH` zeigt auf `/api/audio/lyrics`.
- `_lyricsCache` (dict `relative_path → text`) verhindert wiederholte Netzwerk-Anfragen.
- Beim Track-Wechsel (in `playTrack()`) wird das Panel automatisch aktualisiert wenn es offen ist.
- Keine Lyrics → Benutzerfreundliche Meldung (kein Absturz, kein 404-Anzeige).
- CSS-Klasse `.has-lyrics` am `#btn-lyrics` zeigt an, ob der aktuelle Titel Lyrics hat.

### Designregeln
- `enable_lyrics=False` (Default) → kein Button, kein Panel, kein JS-State. Video-Server bleibt unberührt.
- Lyrics-Panel schließt sich beim Klick auf denselben Button (Toggle).
- Close-Button `×` und der Lyrics-Button selbst schließen das Panel.
- Fehler beim Fetch → Fehlermeldung im Panel, kein unbehandelter Promise-Rejection.

---

## Fernsehsender (Channel-Server)

**Module:** `streaming/channel/server_playlist.py` (aktiv), `streaming/channel/schedule.py`, `config.py`, `cli.py`

### Überblick

Ein dritter FastAPI-Server (neben Audio + Video), der ein **TV-ähnliches Programm** aus dem YAML-Programmplan (`channel_schedule.yaml`) abspielt. Im Gegensatz zur alten HLS-Architektur verwendet der aktuelle Server den **bestehenden Video-Player** mit Auto-Next-Playlist — keine HLS-Segmente, kein ffmpeg-Hintergrundprozess, keine Race Conditions.

### Architektur (Playlist-basiert, 2026-03-31)

```
[schedule.yaml] → parse_schedule_file()
                        ↓
              build_channel_playlist()
         ┌──────────┴──────────────┐
    fill_series (random)    scheduled slots (sequential/random)
         └──────────┬──────────────┘
                    ↓
           list[MediaItem]  (interleaved: fill → slot → fill → ...)
                    ↓
          render_media_page() — same UI as video server
                    ↓
          player.addEventListener('ended', nextIndex()) — auto-advance
                    ↓
          /video/stream?path=... — direct file serve (with remux if needed)
```

**Alte Architektur (HLS, veraltet):** `server.py` + `mixer.py` + `transcode.py` — HLS-Livestream
via concat demuxer. Hatte fundamentale Race Conditions (Segmente werden angefragt bevor ffmpeg
sie schreibt oder nachdem Cleanup sie löscht). Code bleibt als `server.py` erhalten, wird aber
nicht mehr als Default verwendet.

### Module

#### `server_playlist.py` (NEU, 2026-03-31 — aktiver Default)
- **`build_channel_playlist(schedule_data, library_dir, state_dir)`**: Baut die Tages-Playlist:
  1. Scheduled Slots → `resolve_next_episode()` → `MediaItem`
  2. Fill-Series → `list_episodes()` → shuffle → `MediaItem`
  3. Interleaving: Fill-Chunks zwischen den Scheduled-Items verteilt
- **`_media_item_from_path(video_path, library_dir)`**: Konvertiert einen Dateipfad in ein `MediaItem`
- **`create_app(library_dir, schedule_file)`**: FastAPI-App mit Standard-Video-Player-UI
- Playlist wird im Hintergrund-Thread gebaut, TTL 1 Stunde
- Kein ffmpeg, kein HLS, keine Segmente

**Endpoints:**

| Endpoint | Beschreibung |
|---|---|
| `GET /` | Standard-Video-Player-UI (via `render_media_page()`) |
| `GET /health` | Status inkl. `playlist_size` |
| `GET /api/channel/items` | Playlist als `items`-Array (wie Audio/Video) |
| `GET /api/channel/now` | Erstes Playlist-Item (informativ) |
| `GET /api/channel/epg` | Tagesprogramm aus Schedule (via `get_display_schedule()`) |
| `GET /api/channel/schedule` | Roh-Schedule aus YAML |
| `GET /api/channel/metadata` | Metadaten für einzelne Datei |
| `GET /api/channel/status` | Server-Status |
| `GET /api/channel/progress` | Fortschritt laden |
| `POST /api/channel/progress` | Fortschritt speichern |
| `POST /api/channel/rebuild` | Playlist manuell neu bauen |
| `GET /video/stream?path=...` | Video-Stream (mit on-the-fly Remux bei Bedarf) |
| `GET /thumb?path=...` | Thumbnails aus Shadow-Cache |
| `GET /manifest.json` | PWA-Manifest |
| `GET /sw.js` | Service Worker |

#### `schedule.py`
- **`ScheduleSlot`** (frozen dataclass): `start_time`, `series_folder`, `strategy` (sequential/random)
- **`ResolvedSlot`** (frozen dataclass): konkreter Dateipfad + Start/Ende-Zeitpunkt
- **`parse_schedule_file(path)`**: YAML → dict (via PyYAML)
- **`get_slots_for_date(data, dt)`**: Wochentagspezifische Slots, `daily` als Fallback
- **`resolve_next_episode(library_dir, series, state_dir, strategy)`**: Nächste Episode bestimmen, State persistieren
- **`get_display_schedule(data, now)`**: Tagesprogramm für EPG-Anzeige, ohne Episode-State zu ändern
- **`get_fill_series(data)`**: Fill-Series-Ordnernamen aus der Schedule-Konfiguration
- **Episode-State**: `episode_state.json` in `.hometools-cache/channel/` — `{series: next_index}`

#### `server.py` (HLS-Version, veraltet)
- Alter HLS-Livestream-Server mit `ChannelMixer` — wird nicht mehr als Default verwendet
- Code bleibt erhalten für mögliche spätere Nutzung

#### `mixer.py`, `transcode.py`, `filler.py` (HLS-Infrastruktur, veraltet)
- Gehören zur alten HLS-Architektur, werden vom Playlist-Server nicht verwendet

### Schedule-Format (YAML)

```yaml
channel_name: "Haus-TV"
default_filler: "both"

fill_series:
  - "Simpsons"
  - "#Family Guy"
  - "Futurama"

schedule:
  - weekday: "daily"
    slots:
      - time: "20:00"
        series: "Breaking Bad"
        strategy: "sequential"
      - time: "21:00"
        series: "Simpsons"
        strategy: "random"

  - weekday: "saturday"
    slots:
      - time: "19:00"
        series: "Malcolm Mittendrin"
        strategy: "sequential"
```

Spezifische Wochentag-Regeln überschreiben `daily`. Wochentage auf Deutsch oder Englisch.

#### `fill_series` — Dauerprogramm

Wenn kein geplanter Slot aktiv ist (z.B. nachts oder vormittags), spielt der Mixer **zufällige Episoden** aus den `fill_series`-Serien ab.  Dies erzeugt einen kontinuierlichen TV-Stream statt eines Testbilds.

- Jede Iteration wählt zufällig eine Serie aus der Liste, löst eine Episode per `random`-Strategie auf und spielt sie komplett ab.
- Wenn keine der `fill_series`-Ordner existiert oder keine Episoden enthalten, fällt der Mixer auf das SMPTE-Testbild (Sendepause) zurück.
- `fill_series` ist optional — ohne dieses Feld zeigt der Kanal außerhalb der geplanten Slots das Testbild.

### Konfiguration (`.env`)

| Variable | Default | Beschreibung |
|---|---|---|
| `HOMETOOLS_CHANNEL_PORT` | `get_video_port() + 1` (8012) | Server-Port |
| `HOMETOOLS_CHANNEL_SCHEDULE` | `channel_schedule.yaml` (Repo-Root) | Programmplan-Datei |

### Designregeln

1. **Kein Feature-Parity-Test** — der Channel-Server ist ein TV-Programm, kein On-Demand-Browser. Fundamental anderes Paradigma als Audio/Video.
2. **Playlist statt HLS** — der Server baut eine Playlist aus `MediaItem`-Objekten und nutzt den Standard-Video-Player mit Auto-Next. Kein ffmpeg-Hintergrundprozess, keine HLS-Segmente.
3. **`render_media_page()` wiederverwenden** — die Channel-UI ist identisch mit der Video-UI (gleicher Player, gleiche Controls). Kein eigenständiges HTML-Template.
4. **Episode-State ist persistent** — Sequential-Modus merkt sich die letzte Episode über Server-Neustarts hinweg (`episode_state.json`).
5. **Playlist-TTL 1 Stunde** — die Playlist wird im Hintergrund periodisch neu gebaut. Manueller Rebuild via `POST /api/channel/rebuild`.
6. **Fill-Items werden zufällig interleaved** — Fill-Series-Episoden füllen die Lücken zwischen geplanten Slots.
7. **Alle API-Responses nutzen `"items"`-Key** — konsistent mit Audio/Video-Servern.

## Swipe-Gesten (mobile Navigation)

Touch-Swipe-Handler für die Zurück-Navigation auf iPhone/iPad. Implementiert als IIFE am Ende von `render_player_js()` in `server_utils.py`.

### Verhalten

| Kontext | Swipe-Richtung | Aktion |
|---|---|---|
| **Playlist-Ansicht** | Swipe rechts | Zurück zur Ordner-Ansicht (`goBack()`) |
| **Ordner-Ansicht** (nicht Root) | Swipe rechts | Zurück zum Elternordner (`goBack()`) |

Track-Wechsel (nächster/vorheriger) erfolgt **ausschließlich über Buttons**, nicht per Swipe.

### Schwellenwerte

- `SWIPE_MIN_DIST = 60px` — minimale horizontale Distanz
- `SWIPE_MAX_VERT = 80px` — maximale vertikale Abweichung (verhindert Diagonal-Fehlauslösung)
- `SWIPE_MAX_TIME = 400ms` — maximale Touch-Dauer (schnelle Geste, kein Scrollen)

### Ausnahmen (kein Swipe)

Swipe wird **nicht** ausgelöst auf:
- `<input type="range">` (Progress-Bar, Lautstärke)
- `<canvas>` (Waveform)
- `.edit-modal-backdrop` (Metadaten-Editor)
- `.lyrics-panel` (Songtext-Drawer)
- `.offline-library` (Offline-Downloads)

### Designregeln

1. **Kein Feature-Flag** — Swipe ist universell sinnvoll (Audio + Video + Channel).
2. **Passive Event-Listener** — `{ passive: true }` auf `touchstart`/`touchend` für Scroll-Performance.
3. **Rein clientseitig** — keine API-Änderung, kein Backend-Code.
4. **Nur Zurück-Navigation** — Track-Wechsel erfolgt ausschließlich über Buttons, Swipe löst nur `goBack()` aus.

---

## Wiedergabelisten (User Playlists)

**Module:** `streaming/core/playlists.py`, `streaming/core/smart_playlists.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py`

### Übersicht

Benutzer können benannte Playlists erstellen und Medien-Items (Tracks / Videos) hinzufügen. Playlists sind server-spezifisch (Audio und Video getrennt) und werden im Shadow-Cache persistiert. Playlists erscheinen als **Pseudo-Ordner-Karten** auf der Root-Startseite, direkt nach der „Downloaded"-Karte.

### Storage

```
<cache_dir>/playlists/audio.json   ← Audio-Playlists
<cache_dir>/playlists/video.json   ← Video-Playlists
```

Jede Datei enthält ein JSON-Array von Playlist-Objekten:

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "Meine Playlist",
    "created": "2026-04-01T00:00:00+00:00",
    "items": ["artist/song.mp3", "artist/other.mp3"]
  }
]
```

Thread-sicher via `threading.Lock`. Atomare Schreibvorgänge (NamedTemporaryFile + replace). Alle Read-Modify-Write-Operationen halten den Lock für die gesamte Dauer — keine Race Conditions bei konkurrierenden Schreibzugriffen.

### Limits

- Max **50 Playlists** pro Server
- Max **500 Items** pro Playlist
- Duplikate innerhalb einer Playlist werden silently ignoriert

### API-Endpoints (Audio + Video)

| Endpoint | Methode | Beschreibung |
|---|---|---|
| `/api/<media>/playlists` | `GET` | Alle Playlists laden (`{items: [...]}`) |
| `/api/<media>/playlists` | `POST` | Neue Playlist erstellen (`{name}` → `{playlist}`) |
| `/api/<media>/playlists?id=` | `DELETE` | Playlist löschen (`{items: [...]}`) |
| `/api/<media>/playlists/items` | `POST` | Item hinzufügen (`{playlist_id, relative_path}` → `{playlist}`) |
| `/api/<media>/playlists/items?playlist_id=&path=` | `DELETE` | Item entfernen (`{playlist}`) |
| `/api/<media>/playlists/items` | `PATCH` | Item verschieben (`{playlist_id, relative_path, direction}` → `{playlist}`) |
| `/api/<media>/playlists/items` | `PUT` | Item auf Ziel-Index verschieben (`{playlist_id, relative_path, to_index}` → `{playlist}`) |

### Feature-Flag

```python
# render_media_page(enable_playlists=True)   →  Audio + Video
# render_media_page()                         →  Default: False
```

`render_media_page()` und `render_player_js()` haben den Parameter `enable_playlists: bool = False`. Er steuert:
1. `PLAYLISTS_ENABLED = true` im generierten JS
2. `PLAYLISTS_API_PATH = '/api/<media>/playlists'`
3. `IC_PLAYLIST` — SVG-Icon als JS-Variable
4. Playlist-Button (`.track-playlist-btn`) pro Track in der Liste
5. Playlist-Pseudo-Ordner-Karten auf der Root-Startseite (`.playlist-folder-card`)
6. „Neue Playlist…"-Karte (`.playlist-new-card`) — gemeinsam mit „Downloaded" und „Titel" in der kompakten **Tools-Row** (`.playlist-tools-row`)
7. „Zur Playlist hinzufügen"-Modal (`#playlist-modal-backdrop`)

### Tools-Row (Root-Startseite, seit 2026-05-17)

Drei spezielle Aktionen sind oberhalb des Folder-Grids in einer kompakten horizontalen Leiste zusammengefasst (`.playlist-tools-row`, `grid-column: 1 / -1`):

| Element | ID | Aktion |
|---|---|---|
| **Downloaded** | `#offline-folder-card` | Öffnet die Offline-Library (`openOfflineLibrary()`). Count = Anzahl ready-Downloads. |
| **Neue Playlist…** | `#playlist-new-card` | `prompt()` → `POST /api/<media>/playlists` |
| **Titel** | `#all-titles-card` (`data-playlist-id="__alltitles__"`) | Pseudo-Playlist: zeigt alle Titel aus **allen** User-Playlists in einer deduplizierten Liste (`showUserPlaylistView('__alltitles__')`). Nur sichtbar wenn ≥ 1 Titel in irgendeiner Playlist. **Read-only** — Reorder/Remove sind blockiert. |

Helper-Funktionen: `_collectAllPlaylistRelPaths()`, `_countAllPlaylistTitles()`, `_resolveAllPlaylistItems()`.

Die alten großen `folder-card`-Quadrate für „Downloaded" und „Neue Playlist…" wurden ersetzt; die Klassennamen `.offline-folder-card`, `.playlist-new-card`, `.playlist-folder-card` bleiben für Selektor-Kompatibilität (Click-Handler, Feature-Parity-Tests) erhalten.

### UI-Elemente (Redesign 2026-04-02)

| Element | ID/Klasse | Funktion |
|---|---|---|
| **Playlist-Ordner-Karte** | `.playlist-folder-card` | Pro Playlist eine Karte auf der Root-Startseite mit IC_PLAYLIST-Icon, Name, Item-Count, Play- und Delete-Button |
| **Neue-Playlist-Karte** | `#playlist-new-card`, `.playlist-new-card` | Dashed-Border-Karte mit "+"-Icon, öffnet `prompt()` für Playlist-Name |
| **Add-Modal** | `#playlist-modal-backdrop`, `.playlist-modal-backdrop` | „Zur Playlist hinzufügen" mit Dropdown + Inline-Erstellen |
| **Track-Button** | `.track-playlist-btn` | Pro Track, öffnet Add-Modal |
| **Drag Ghost** | `.playlist-drag-ghost` | Floating-Element beim Drag (Thumbnail + Titel), folgt Cursor/Finger |
| **Drag Marker** | `.drag-over-above` / `.drag-over-below` | Farbige Insertion-Line via `box-shadow` auf dem Ziel-Track |

**Entfernte Elemente (seit Redesign):**
- `#playlist-pill` (Header-Button) — Zugang über Pseudo-Ordner statt Header
- `#playlist-library` (Overlay-Panel) — nicht mehr nötig
- `.playlist-lib-*` CSS-Klassen
- `openPlaylistLibrary()`, `closePlaylistLibrary()`, `renderPlaylistLibrary()` JS

### JS-Architektur

```
PLAYLISTS_ENABLED: bool           ← aus enable_playlists
PLAYLISTS_API_PATH: str           ← '/api/<media>/playlists'
IC_PLAYLIST: str                  ← SVG-Icon
_userPlaylists: []                ← lokaler State (geladen via API)
_playlistAddPath: ''              ← relative_path des aktuell hinzuzufügenden Items
_currentPlaylistId: ''            ← ID der aktuell gespielten Playlist (für Reorder)

loadUserPlaylists()               ← GET → _userPlaylists, danach Root-View re-rendern
playUserPlaylist(plId)            ← Playlist-Items in allItems auflösen, playTrack(0), setzt _currentPlaylistId
deleteUserPlaylist(plId)          ← DELETE → _userPlaylists aktualisieren, Folder-View re-rendern
openPlaylistModal(relativePath)   ← Add-Modal anzeigen
addToPlaylist(plId, relativePath) ← POST /items → Toast
createAndAddToPlaylist(name, rp)  ← POST (create) → addToPlaylist
movePlaylistItem(rp, direction)   ← PATCH /items → _applyPlaylistUpdate (Legacy, bleibt für Abwärtskompatibilität)
reorderPlaylistItem(rp, toIndex)  ← PUT /items → _applyPlaylistUpdate (Drag-and-Drop)
_applyPlaylistUpdate(pl)          ← re-resolve Items, currentIndex anpassen, renderTracks()
initPlaylistDragDrop()            ← Bindet Mouse/Touch-Events auf track-list (nur in Playlist-Ansicht + filenames/list-Modus)
```

### Drag-and-Drop

Reordering wird per Drag-and-Drop durchgeführt — keine Pfeil-Buttons.

**DnD ist nur aktiv wenn:**
1. `inPlaylist && _currentPlaylistId` (Playlist-Kontext)
2. `viewMode === 'filenames'` oder `viewMode === 'list'` (Dateinamen- oder Listenansicht)

In `grid`-Modus ist DnD **deaktiviert**. Klick auf einen Track spielt ihn ab.

| Plattform | Aktivierung | Verhalten |
|---|---|---|
| **Desktop** | Mousedown + Mausbewegung > 10px | Drag startet erst nach Schwellenwert, nicht sofort bei Klick |
| **Mobile** | Long-Touch (500 ms) | Haptic-Feedback (`navigator.vibrate`), dann Drag |

**Visuelles Verhalten:** Das gezogene Item wird ausgegraut (`opacity: 0.25`, `pointer-events: none`) und bleibt an seiner Position sichtbar. Ghost-Element folgt dem Cursor. No-Op-Unterdrückung: Wenn die berechnete Zielposition identisch mit der Ausgangsposition wäre (= direkt neben dem gezogenen Item, Richtung Originalplatz), wird die Insertion-Line unterdrückt — das verhindert visuelles Springen der Linie.

**Drop-Target-Berechnung (`updateDropTarget`):**

1. `elementFromPoint(x, y)` → nächstes `.track-item` finden
2. Kein Item gefunden, aber Cursor in Track-List-Bounds → letztes sichtbares Item mit `_dropAbove = false` (Fallback „ans Ende")
3. `target === _dragItem` → Indicator löschen, return (nichts markieren)
4. Cursor-Y < Mitte des Items → `above = true` (Einfügung VOR diesem Item)
5. Cursor-Y ≥ Mitte → `above = false` (Einfügung NACH diesem Item)
6. **Normalisierung:** „below N" wird zu „above N+1" umgerechnet (nächstes sichtbares Sibling, überspringe `missing-episode` und `_dragItem`). Nur wenn N das letzte sichtbare Item ist, bleibt `above = false`. → Es gibt pro logischer Position nur EINE Linie.
7. **No-Op-Unterdrückung:** Effektiven `toIndex` berechnen (same as `endDrag`-Logik). Wenn `toIndex === _dragFromIdx` → Indicator löschen, return.
8. `drag-over-above` bzw. `drag-over-below` auf das Ziel-Item setzen.

**CSS Insertion-Line:** `box-shadow: 0 3px 0 0 var(--accent) inset` für `.drag-over-above` (Linie am oberen Rand) und `0 -3px inset` für `.drag-over-below` (Linie am unteren Rand). `drag-over-below` wird durch die Normalisierung nur noch für die allerletzte Position verwendet (nach dem letzten Item). 

### Sort-Option „Liste" (custom)

Neue Sort-Option `<option value="custom">Liste ⇅</option>` im Sort-Dropdown. **Ist der Default** (erste Option im Dropdown):

- **In Playlist-Kontext:** Behält die Server-Reihenfolge bei (kein Re-Sort). DnD-Reorder verändert die Reihenfolge.
- **In Filesystem-Ordner:** Sortiert nach benutzerdefinierter Reihenfolge (server-seitig gespeichert, localStorage als Offline-Fallback).

---

## Intelligente Wiedergabelisten (Smart Playlists)

**Module:** `streaming/core/smart_playlists.py`, `streaming/core/playlists.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils/_player_js.py`, `streaming/core/server_utils/_css.py`

### Konzept

Eine intelligente Playlist speichert anstelle einer Item-Liste eine **Regelgruppe**.  Beim Anzeigen wird die Playlist clientseitig gegen `allItems` ausgewertet — die `items`-Liste der Playlist bleibt auf dem Server permanent leer.  Beispiele aus iTunes: „Zuletzt hinzugefügt" (`added_at within_days 60`), „Best of Rock" (`in_playlist any_of [Rock, Rock-Alt]` UND `rating >= 4`).

### Storage (v2 Envelope, neues optionales Feld)

```jsonc
{
  "id": "abc123",
  "name": "Best of Rock",
  "created": "…",
  "updated_at": "…",
  "items": [],            // immer leer bei Smart Playlists
  "smart": {
    "match": "all" | "any",
    "rules": [
      {"field": "rating",      "op": "gte",         "value": 4},
      {"field": "in_playlist", "op": "any_of",      "value": ["p1", "p2"]},
      {"field": "added_at",    "op": "within_days", "value": 60},
      {"field": "genre",       "op": "matches",     "value": "^Rock"}
    ],
    "limit": 100,          // optional
    "sort": "rating_desc"  // optional
  }
}
```

Reguläre Playlists haben **kein** `smart`-Feld — die beiden Typen koexistieren in derselben Datei.  `playlists.py` schützt Smart Playlists: `add_item` / `remove_item` / `move_item` / `reorder_item` sind No-Ops (kein Revision-Bump, Warn-Log).

### Operatoren

| Field-Typ | Operatoren |
|---|---|
| Strings (`title`, `artist`, `genre`, `relative_path`, `language`) | `eq`, `contains`, `starts_with`, `matches` (Regex, case-insensitive, ≤ 256 Zeichen) |
| Zahlen (`rating`, `duration`, `season`, `episode`, `bitrate`, `file_size`) | `eq`, `gte`, `lte`, `between` (Liste `[lo, hi]`), `in` |
| `added_at` (Proxy: `MediaItem.mtime`) | `within_days`, `before`, `after` |
| `in_playlist` (Cross-Playlist-Referenz) | `any_of` (OR), `all_of` (AND), `none_of` |
| `is_favorite` (audio-spezifisch) | `eq` (bool) |
| `in_folder` (abgeleitet aus `relative_path`-Prefix) | `eq`, `starts_with` |

`match: "all"` = UND über alle Top-Level-Regeln, `match: "any"` = ODER.  Innerhalb einer Regel realisieren `any_of`/`all_of`/`none_of` (für `in_playlist`) sowie `in` (für Werte-Listen) eine eingebaute Sub-OR-/AND-Semantik — dies reicht für die Phase-1-Use-Cases ohne echtes Sub-Group-Nesting.

### API-Endpoints

| Methode + Pfad | Body | Wirkung |
|---|---|---|
| `POST /api/<media>/playlists/smart` | `{name, smart}` | Neue Smart Playlist anlegen |
| `PUT /api/<media>/playlists/smart` | `{playlist_id, smart}` | `smart`-Block einer (auch regulären) Playlist ersetzen → promotet sie ggf. zur Smart Playlist |

Validierung: `validate_smart_rules()` lehnt fehlende `match`/`rules`/`field`/`op`/`value`-Felder oder eine `limit > 10_000` ab (HTTP 400).

### Auswertung (Client-seitig)

`_evaluateSmartPlaylist(pl)` in [`_player_js.py`](../src/hometools/streaming/core/server_utils/_player_js.py) ist der JS-Mirror von `evaluate_smart()` in `smart_playlists.py`.  Beide:

1. Bauen einen Index `pl_id → set(relative_path)` aus allen **nicht-smarten** User-Playlists (zur Auflösung von `in_playlist`).  Smart-Playlists werden hier übersprungen — siehe Phase-2-Diskussion in `IMPLEMENTATION_PLAN.md`.
2. Iterieren über `allItems` und werten jede Regel via Operator-Dispatch aus.
3. Wenden optional `sort` (`title`, `rating`, `added_at`, `duration`, jeweils auch `_desc`, plus `random`) und `limit` an.
4. Geben eine Liste von `relative_path`-Strings zurück (Python) bzw. `MediaItem`-Objekten (JS).

`_resolvePlaylistItems(plId)` erkennt anhand von `pl.smart` automatisch eine Smart Playlist und füllt `playlistItems` aus der Live-Auswertung — bestehende Track-Render-/Play-/Browse-Pfade brauchen keine Änderung.

### UI-Elemente

| Element | Selektor | Funktion |
|---|---|---|
| **Smart-Playlist-Karte** | `.playlist-folder-card.smart-playlist-card` | Normale Playlist-Karte, plus Lightning-Bolt-Badge (`.smart-pl-badge` mit `SVG_SMART_PLAYLIST`) in der rechten unteren Ecke des Logos |
| **Refresh-Button** | `.playlist-folder-refresh` | Kleiner Button oben links auf Smart-Karten; ruft `refreshSmartPlaylist()` auf (Re-Evaluation + In-Place-Re-Render falls aktuell sichtbar) |
| **Neue-Smart-Playlist-Karte** | `#smart-playlist-new-card` (Klasse `.smart-new-card`) | Zweite „Neu…"-Karte rechts neben „Neue Playlist…" in `.playlist-tools-row`, öffnet den Editor-Modal |
| **Editor-Modal** | `#smart-editor-backdrop`, `.smart-editor-modal` | Reine JS-DOM-Injektion via `openSmartPlaylistEditor(pl?)`.  Name-Feld, AND/OR-Radio, Regelzeilen (`<select field>` + `<select op>` + Wert-Input), „+ Regel"-Button, optionales Limit-Feld, Speichern → `POST` oder `PUT` auf `PLAYLISTS_SMART_PATH` |
| **Wertinput-Varianten** | `.smart-rule-value` | Text/Zahl/`<select multiple>` (für `in_playlist`) / Boolean-Select (für `is_favorite`) / zwei Inputs (für `between`) — automatisch passend zum gewählten Feld+Op |

### Designregeln

- **Keine Server-seitige Re-Evaluation.**  Server speichert nur Regeln; Auswertung lebt 1:1 im Client.  Refresh = lokal neu auswerten.  Bei Wiedergabe-Start auf einer Smart-Karte wird vorher implizit re-evaluiert (kein expliziter API-Call).
- **Kaskaden vermieden in Phase 1.**  `in_playlist`-Referenzen auf Smart Playlists werden beim Index-Bau übersprungen → keine Zyklen, keine Tiefen-Probleme.  Phase 2 plant DAG-Auflösung (siehe Implementation-Plan).
- **`added_at`-Proxy.**  Da kein dediziertes „added_at"-Feld auf `MediaItem` existiert, wird `mtime` (File-Modification-Time) verwendet.  Konsequenz: Tag-Edits oder NAS-Resync können die Zuordnung verschieben.  Phase-2-Verbesserung (persistentes `first_seen_at` im Index-Cache) ist im Implementation-Plan dokumentiert.
- **Regex-Sicherheit.**  Patterns sind auf ≤ 256 Zeichen begrenzt; ungültige Patterns matchen nichts (statt zu crashen).  Compile-Cache pro Pattern.
- **Smart Playlists sind read-only**, was Item-Listen-Mutationen angeht — sowohl an der Storage-Schicht (Guards in `playlists.py`) als auch im Client (kein Add-to-Playlist-Modal-Eintrag für Smart Playlists).

## Tools-Panel (UI-Einstellungen)

**Modul:** `streaming/core/server_utils.py` (CSS + JS + HTML)

Benutzer-steuerbares Panel zum Ein-/Ausblenden von UI-Funktionen. Öffnet sich über die "Tools"-Pill in der Kopfzeile.

### UI

- **Pill:** `<span class="tools-pill" id="tools-pill">Tools</span>` im `<header>`
- **Panel:** Modal-Dialog mit Backdrop (`#tools-panel-backdrop`), Toggle-Switches pro Feature
- **Toggle-Switches:** CSS-only Toggle (`.tools-toggle` mit `<input type="checkbox">` + `.tools-toggle-track`-Slider)
- **State:** `localStorage` unter Key `ht-tools` (JSON-Objekt mit Boolean-Feldern)

### Verfügbare Tools

| Tool-ID | Label | Beschreibung | CSS-Klasse | Status |
|---------|-------|-------------|------------|--------|
| `inlineRatings` | Inline-Ratings | Bewertungssterne direkt in der Track-Liste | `body.tool-inline-ratings` | Implementiert |
| `downloads` | Downloads | Download-Buttons pro Track ein/ausblenden | `body.tool-hide-downloads` | Implementiert |
| `playlists` | Zur Playlist hinzufügen | Playlist-Buttons pro Track ein/ausblenden | `body.tool-hide-playlists` | Implementiert |
| `duplicates` | Duplikate suchen | Doppelte Dateien finden | `body.tool-show-duplicates` | Implementiert |
| `fileMover` | Dateien verschieben | Songs in andere Ordner verschieben | `body.tool-show-file-mover` | Implementiert |

### Globale Tools (Abschnitt im Tools-Panel)

Enthält katalogweite Aktionen und Einstellungen — unabhängig vom Tool-Modus:

- **"Ordnerdaten aller Ordner erneuern"** (`#tools-global-refresh-btn`): Führt sofort `refreshCatalog()` aus und schließt das Panel. Löst ein vollständiges serverseitiges Re-Indexing aller Ordner aus, äquivalent zum manuellen Klick auf die Refresh-Karte in der Startansicht.
- **Auto/Aus-Buttongroup** (`#tool-auto-refresh`): Steuert ob beim Laden der Seite der Hintergrund-Index-Refresh automatisch startet. `"auto"` (Standard) = `scheduleBackgroundRefresh()` wird bei laufendem Index-Build aufgerufen. `"aus"` = kein automatisches Polling; Nutzer muss manuell erneuern. Der Wert wird in `_toolState.autoRefresh` gespeichert.

### Katalog-Refresh-Button (Tools-Row)

Der "Katalog neu laden"-Button **wurde aus dem Header entfernt** und ist jetzt ganz rechts in der `playlist-tools-row` auf der Startansicht (Root) platziert:

- **Karte:** `<button class="tools-row-item refresh-catalog-card" id="refresh-catalog-card">` mit `IC_REFRESH`-Icon
- **Rendering:** Wird in `showFolderView()` immer wenn `isRoot` zum `_toolsRowParts`-Array hinzugefügt
- **Spinner:** `_getRefreshBtn()` (dynamische DOM-Abfrage bei Bedarf) + `.spinning`-Klasse; CSS: `.refresh-catalog-card.spinning .tools-row-icon svg { animation: spin ... }`
- **Click:** Event-Delegation auf `folderGrid` via `.refresh-catalog-card`-Selektor → `refreshCatalog()`
- **Styling:** Gedämpfte Optik (gestrichelte Border, transparent); Square 40×40px, `margin-right: 6px`

### Split-Pill im Header (Tools-Modus-Toggle)

Die `tools-pill` im Seiten-`<header>` ist jetzt ein **zweiteiliger Split-Pill** (`#tools-pill-wrap`):

- **Linker Teil** `#tools-pill` (.tools-pill): "Tools"-Text → öffnet das Tools-Panel (unverändertes Verhalten)
- **Rechter Teil** `#tools-pill-toggle` (.tools-pill-toggle): Kleiner Dot-Indicator-Button → togglet den Tool-Modus **direkt, ohne das Panel zu öffnen**
  - Inaktiv: hohler Kreis (CSS `::before`)
  - Aktiv (`.active`): gefüllter Kreis in Akzentfarbe
  - `e.stopPropagation()` verhindert Bubbling zum linken Tools-Text
- **Wrap** `#tools-pill-wrap` (.tools-pill-wrap): Gemeinsame Border + Hover/`has-active`-Hervorhebung
- **Sync:** `_updateActivateBtn()` aktualisiert sowohl `#tools-activate-all` (Panel) als auch `#tools-pill-toggle` (Header-Split-Pill) — beide zeigen immer denselben Zustand
- **Click-Handler:** `_toolsPillToggle.addEventListener('click', ...)` — identische Toggle-Logik wie `#tools-activate-all`

### Inline-Ratings

Wenn aktiv, werden 5 klickbare Bewertungssterne (`.track-inline-rating`) rechts neben jedem Track-Item angezeigt. Gleichzeitig werden andere Track-Buttons (Download, Pin, Edit, Playlist, Queue) ausgeblendet, um Platz zu schaffen. Die Sterne nutzen dieselben `IC_STAR_FILLED`/`IC_STAR_EMPTY`-Icons und das gleiche `POST /api/<media>/rating`-API wie der Player-Rating im Player-Bar.

- **`renderInlineRating(t, idx)`** — generiert den HTML-String für die 5 Sterne pro Track
- **`setInlineRating(idx, stars)`** — sendet Rating an den Server, aktualisiert Sterne in-place, Toast-Feedback mit Undo
- **Event-Delegation:** Sterne-Clicks werden via `stopPropagation` abgefangen, um Playback-Trigger zu verhindern
- **DnD-Kompatibilität:** `.track-inline-rating-star` ist in den DnD-Exclusion-Selektoren enthalten

### Duplikat-Erkennung (Client-Side)

Rein client-seitige Erkennung von Duplikaten über die bereits geladene `allItems`-Liste. Kein zusätzlicher Backend-Endpoint nötig.

**Algorithmus:**
1. **`_normalizeStem(s)`** — JS-Port von `stem_identifier()` aus `audio/sanitize.py`: Normalisiert `feat.`/`prod.`/`vs.`-Varianten, entfernt Bitrate-Tags, URLs, Emojis, Official-Video-Marker, trimmt Leerzeichen, lowercased.
2. **`_dupeKey(item)`** — Erzeugt stabilen Key aus **Artist + Titel**: Strippt zuerst Download-Duplikat-Suffixe (`_2`, `(2)`, `-2`, `_copy`, `(kopie)` etc.), dann splittet normalisierten Titel an Trennzeichen (`feat.`, `prod.`, `vs.`, `-`, `,`, `&`, Klammern), entfernt aggressiv Musik-Keywords (Remix, Mix, Version, Edit, Remaster, Live, Acoustic, etc.), strippt Non-Word-Chars, filtert Parts ≤ 2 Zeichen, sortiert und joined zu stabilem Key. **Artist-Prefix:** Der normalisierte `item.artist` (>2 Zeichen) wird als `artist::titleKey` vorangestellt, sodass verschiedene Interpreten mit gleichem Titel (z.B. "Blümchen - Nur Geträumt" vs. "Nena - Nur Geträumt") NICHT als Duplikate erkannt werden.
3. **`_buildDuplicateMap()`** — Iteriert einmal über `allItems`, baut `Map<dupeKey, [itemIndex, ...]>`, filtert auf Gruppen mit `length > 1`. Speichert zusätzlich `_dupePaths` (Set aller `relative_path`-Strings) für O(1)-Lookup beim Rendering.
4. **Cache-Invalidierung:** `_invalidateDupeMap()` wird bei jedem `allItems`-Replacement aufgerufen (Background-Refresh, Initial-Catalog-Load, Explicit-Refresh, File-Delete, File-Move). Lazy Re-Build beim nächsten Zugriff. `renderTracks()` ruft `_ensureDupeMap()` auf, wenn `_toolState.duplicates` aktiv ist — dadurch sind Badges sofort beim ersten Rendering und nach Löschvorgängen stabil sichtbar.

**UI-Elemente:**
- **`.dupe-badge`** — kleines orangenes Pill-Badge neben dem Track-Titel; via CSS `body.tool-show-duplicates .dupe-badge { display:inline-flex }` gesteuert. Enthält den Text „Duplikat" und bei Duplikaten den Trash-Button (`.track-delete-btn`).
- **Dupe-Show-Link** — Link unter dem Toggle im Tools-Panel (`"N Duplikat-Gruppen gefunden — anzeigen"`), öffnet das Duplikat-Panel.
- **Duplikat-Panel** — Modal-Dialog (`.dupe-panel-backdrop` + `.dupe-panel`) mit Gruppenübersicht: pro Gruppe Header (Titel + Anzahl), pro Item Thumbnail, Titel, Ordner-Pfad, **Metadaten-Zeile** (Länge · kbps · Dateigröße · Datum). Click navigiert zum Ordner und spielt den Track ab.
- **Metadaten im Dupe-Panel** — Jedes Duplikat-Item zeigt eine `.dupe-group-item-meta`-Zeile mit formatierter Wiedergabelänge (`_fmtDuration`), Bitrate in kbps, Dateigröße (`_fmtFileSize`) und Änderungsdatum (`_fmtDate`). Alle Werte werden aus den neuen `MediaItem`-Feldern `duration`, `bitrate`, `file_size`, `mtime` gelesen. Fehlende Werte (0) werden ausgeblendet.
- **`MediaItem` neue Felder** — `file_size: int = 0` (Bytes), `duration: float = 0.0` (Sekunden), `bitrate: int = 0` (kbps). Werden in Audio- und Video-Catalog befüllt (Audio: mutagen `info.length`/`info.bitrate` via `get_audio_file_info()`; Video: `_read_media_info_fast()` incl. Metadata-Cache). Vorbereitung für konfigurierbare Anzeige in der normalen Ansicht (spätere Erweiterung).
- **"Alle Duplikate abspielen"** — `.dupe-panel-play-all` Button im Panel. `playDuplicates()` sammelt alle Items aus `_dupeMap`-Gruppen, schließt das Panel und zeigt sie als virtuelle Playlist (`_currentPlaylistId = '__duplicates__'`). Header zeigt "Duplikate (N Gruppen)". Items sind nach Dupe-Gruppen geordnet, sodass zusammengehörige Duplikate nacheinander gespielt werden.
- **Trash-Button (Panel)** — Pro Duplikat-Item ein `.dupe-trash-btn` (Mülleimer-Icon `IC_TRASH`/`SVG_TRASH`), nur im Duplikat-Panel sichtbar. Click öffnet `confirm()`-Dialog, bei Bestätigung wird die Datei per Soft-Delete in den Papierkorb verschoben.
- **Inline-Delete-Button** — `.track-delete-btn` (kleines Mülleimer-Icon `IC_TRASH`) sitzt direkt innerhalb der `.dupe-badge`-Pill in `renderTracks()`. Da die Badge nur bei `body.tool-show-duplicates` sichtbar ist, braucht der Button keine eigene Visibility-Regel. Click löst `_deleteTrackFromList(filteredIdx)` aus.

### Duplikat-Löschung (Soft-Delete)

Ermöglicht das Löschen einzelner Duplikat-Dateien direkt aus dem Duplikat-Panel. Dateien werden nie hart gelöscht, sondern per Soft-Delete in das Trash-Verzeichnis (`HOMETOOLS_DELETE_DIR`, Default: `~/Music/DELETE_ME`) verschoben.

**Backend:**
- **`POST /api/audio/delete-file`** in `audio/server.py`: Body `{ "path": "Folder/song.mp3" }`. Validiert Pfad via `resolve_audio_path()`, verschiebt via `attention_delete_files()` (Soft-Delete), loggt `file_delete`-AuditEntry, invalidiert IndexCache. Returns `{ "ok": true, "entry_id": "..." }`.
- **`POST /api/video/delete-file`** in `video/server.py`: Identisch mit `resolve_video_path()` — Feature-Parity.
- **Audit-Log:** `log_file_delete()` in `audit_log.py`, Action `"file_delete"`, `undo_payload` enthält `original_path` und `trash_path`. Kein automatisches Undo im Audit-Panel (Datei manuell aus Trash wiederherstellbar).

**Frontend (JS in `server_utils.py`):**
- **`IC_TRASH`** — JS-Variable mit SVG-Trash-Icon (aus `SVG_TRASH`).
- **`DELETE_API_PATH`** — JS-Variable abgeleitet aus `api_path` (Pattern wie `MOVE_API_PATH`).
- **`_deleteDuplicateFile(allIndex)`** — `confirm()`-Dialog, dann `fetch(DELETE_API_PATH, {method:'POST', body: {path}})`. Bei Erfolg: `allItems[allIndex]._deleted = true` (kein `splice`!), `_invalidateDupeMap()`, `_invalidateFolderCache()`, `showToast()`, `applyFilter()` + `openDupePanel()`. Item bleibt in `allItems`, Dupe-Gruppe bleibt sichtbar. Playback-aware: erkennt ob der gelöschte Track aktuell spielt und springt ggf. zum nächsten.
- **`_deleteTrackFromList(filteredIdx)`** — Wie `_deleteDuplicateFile`, aber nutzt `filteredItems[idx]`. Findet das Item per `relative_path` in `allItems` und setzt `._deleted = true`. Re-render via `applyFilter()`.
- **`.dupe-trash-btn`** — Icon-Button mit `stopPropagation()` (verhindert Click-to-Play des Parent-Items). Nur für nicht-gelöschte Items gerendert (`._deleted` → Badge statt Button). CSS: transparent, rot-auf-hover.
- **`.track-delete-btn`** — Inline-Delete-Button in der Track-Liste, nur für Duplikate gerendert.

**Ghost-Anzeige nach Löschung:**
- Gelöschte Items bleiben mit `._deleted = true` in `allItems` und fließen durch `applyFilter()`.
- `renderTracks()`: `_deleted`-Items gehören NICHT zu `filteredItems` (= nicht abspielbar). Sie werden als separate Ghost-Zeile in `displayTracks` re-injiziert (identisches Muster wie `_movedTo`-Ghosts).
- Ghost-Zeile hat Klasse `.track-item--deleted`: ausgegraut (`opacity: 0.35`), `pointer-events: none`, Titel durchgestrichen, **× statt Numbering**, rotes "Gelöscht"-Badge.
- Der Track-Zähler zeigt `(N gelöscht)` wenn gelöschte Items vorhanden sind.
- `applyFilter()`: `_deleted`-Items werden durch alle Filter (Threshold, Quick-Filter, Text) durchgelassen, damit sie immer sichtbar bleiben.
- Im Duplikat-Panel: gelöschte Items haben Klasse `.dupe-group-item--deleted` (ausgegraut, `pointer-events: none`, Titel durchgestrichen, rotes Badge im Titel). Kein Trash-Button, kein Click-to-Play. Die Gruppe bleibt sichtbar (beide Items: gelöschtes + überlebendes), bis die Seite neu geladen wird.

**Design-Prinzipien:**
1. **Nur Duplikate löschbar** — Kein allgemeiner Delete-Button in der UI. Trash im Duplikat-Panel und als Inline-Button (`.track-delete-btn`) in der Track-Liste, nur für als Duplikat erkannte Items gerendert. Soft-Delete via `attention_delete_files()`, Bestätigung via `confirm()`.
2. **Soft-Delete** — Datei wird verschoben, nie gelöscht. Trash-Verzeichnis konfigurierbar.
3. **Bestätigung erforderlich** — `confirm()`-Dialog vor jeder Löschung.
4. **Feature-Parity** — Beide Server (Audio + Video) haben den Endpoint.
5. **Session-Sichtbarkeit** — Gelöschte Items bleiben bis zum nächsten Page-Reload sichtbar (Ghost-Zeile). Nach Reload ist das Item weg (Backend hat es aus dem Index entfernt).

### Dateien verschieben (File Mover)

Inline-Widget zum Verschieben von Audio-Dateien in einen anderen Ordner der Bibliothek. Kombiniert Schnellwahl mit Vollauswahl.

**Backend:**
- **`POST /api/audio/move-file`** in `audio/server.py`: Body `{ "path": "OLD/song.mp3", "target_folder": "NEW" }`. Validiert Quell-/Zielpfad, prüft Traversal-Schutz, verhindert Überschreiben, verschiebt via `shutil.move`, loggt `file_move`-AuditEntry, invalidiert IndexCache. Returns `{ "ok": true, "new_path": "NEW/song.mp3", "entry_id": "..." }`.
- **`GET /api/audio/folders`** in `audio/server.py`: Gibt alle Top-Level-Ordnernamen als `{ "folders": [...] }` zurück.
- **Audit-Log:** `log_file_move()` in `audit_log.py`, Action `"file_move"`, undo_payload enthält `old_path` und `new_path` für Rück-Verschiebung.
- **Undo:** Im `audio_audit_undo()`-Handler wird `file_move` unterstützt: Datei wird von `new_path` zurück nach `old_path` verschoben.

**Frontend (JS in `server_utils.py`):**
- **`_getRecentMoveTargets()`** — Liest die letzten 4 Zielordner aus `localStorage` Key `ht-move-recent`.
- **`_saveRecentMoveTarget(folder)`** — Speichert einen Ordner als MRU-Eintrag (max. 4, neuester zuerst).
- **`_getAllFolders()`** — Berechnet alle Top-Level-Ordner aus `allItems` (lazy, mit `_allFoldersCache`). Wird bei `allItems`-Replacement invalidiert via `_invalidateFolderCache()`.
- **`renderMoveWidget(t, idx)`** — Generiert pro Track: (1) aktueller Ordner als farbiges Tag, (2) 2×2-Grid der letzten 4 Ordner als Quick-Pick-Buttons, (3) `<select>` Dropdown mit allen Ordnern.
- **`moveFileToFolder(idx, targetFolder)`** — Sendet `POST /api/audio/move-file`, aktualisiert `allItems` in-place (neuer `relative_path`, `stream_url`, `artist`), invalidiert Caches, rendert View neu.

**CSS:**
- `.track-move-widget` — `display:none` default, via `body.tool-show-file-mover .track-move-widget { display:flex }` sichtbar.
- Wenn File-Mover aktiv, werden andere Track-Buttons ausgeblendet (analog Inline-Ratings).
- `.move-current-folder` — grüner Tag mit aktuellem Ordnernamen.
- `.move-quick-grid` — 2×2 CSS-Grid für Schnellwahl-Buttons.
- `.move-quick-btn` — kompakter Button pro MRU-Ordner, `.is-current` bei aktuellem Ordner (disabled, dimmed).
- `.move-folder-select` — Dropdown mit allen Ordnern.

### Designregeln

1. **Shared-Core-UI** — Tools-Panel lebt in `server_utils.py`, nicht pro Server dupliziert
2. **Keine Feature-Flags nötig** — Tools sind client-seitig (localStorage), kein Server-Flag
3. **CSS-only Visibility** — `body`-Klassen steuern Sichtbarkeit via CSS, kein JS-DOM-Manipulation pro Element
4. **Inline-Ratings exklusiv** — Wenn aktiv, werden andere Track-Buttons ausgeblendet (kein Platzproblem auf Mobile)
5. **State persistent** — `ht-tools` in localStorage, überlebt Page-Reloads und Server-Restarts
6. **Duplikat-Erkennung rein client-seitig** — Kein zusätzlicher Backend-Endpoint, keine Server-Last. Dupe-Map wird lazy berechnet und bei Catalog-Wechsel invalidiert.
7. **File-Mover exklusiv** — Wenn aktiv, werden andere Track-Buttons ausgeblendet (wie Inline-Ratings). MRU-Ordner in `localStorage`, Ordnerliste aus `allItems` gecached.
8. **Duplikat-Löschung nur für Duplikate** — Trash-Button im Duplikat-Panel und als Inline-Button (`.track-delete-btn`) in der Track-Liste, nur für als Duplikat erkannte Items gerendert. Soft-Delete via `attention_delete_files()`, Bestätigung via `confirm()`.

## iOS-kompatibler Video-Stream (Faststart-Cache)

### Problem

iOS Safari erfordert zwingend HTTP Range Requests (`Accept-Ranges: bytes` + `206 Partial Content`), um Video-Playback zu starten. FastAPI's `StreamingResponse` unterstützt diese nicht nativ. MP4-Dateien, deren `moov`-Atom am Ende liegt (kein Faststart), wurden bisher on-the-fly per ffmpeg geremuxed — was auf iOS komplett stumm scheitert.

### Lösung

Für `.mp4`-Dateien ohne Faststart wird **einmalig eine gecachte Faststart-Kopie** im Shadow Cache erstellt (`ffmpeg -c copy -movflags +faststart`). Diese wird per `FileResponse` ausgeliefert, das Range Requests vollständig unterstützt. Für MKV/AVI/andere Container bleibt der bestehende `StreamingResponse`-Pfad (fragmented MP4) als Fallback aktiv.

### Module

- `streaming/core/remux.py` — `ensure_faststart_cache()`, `get_faststart_cache_path()`
- `streaming/video/server.py` — `GET /video/stream` entscheidet zwischen Cache-Pfad und Remux-Pfad

### Cache-Pfad

```
{cache_dir}/video/{relative_path}.faststart.mp4
```

### Entscheidungslogik in `/video/stream`

1. `.mp4` + Faststart vorhanden → `FileResponse` (direkt, Range-konform)
2. `.mp4` + **kein** Faststart → `ensure_faststart_cache()` → `FileResponse` (Cache, Range-konform)  
   Fallback wenn ffmpeg fehlt: `StreamingResponse` (wie vorher)
3. Nicht-native Container (MKV, AVI…) → `remux_stream()` → `StreamingResponse`

### Designregeln

- Faststart-Konvertierung ist **-c copy** (keine Neukodierung), dauert Sekunden auch für große Dateien.
- MTime-basierte Invalidierung: Cache wird neu erzeugt, wenn die Quelldatei neuer ist.
- `ensure_faststart_cache()` ist idempotent, thread-safe über tmp→rename-Pattern.
- Fehler (ffmpeg fehlt, Timeout, Disk-Fehler) werden geloggt; die Funktion gibt `None` zurück und der Aufrufer fällt auf den alten Remux-Pfad zurück — kein Absturz.

### Background-Prewarm (2026-05-29)

Der erste Stream-Request einer großen MP4-Datei ohne Faststart blockierte
mehrere Sekunden im Request-Handler, weil `ensure_faststart_cache()` synchron
lief (besonders spürbar bei Serien-Episoden auf langsamem NAS-Storage).
`thumbnailer._prewarm_faststart_if_needed()` läuft jetzt innerhalb des
Hintergrund-Thumbnail-Workers nach jeder erfolgreich erzeugten Video-Thumbnail
und baut die Faststart-Kopie proaktiv. Bedingungen für den Lauf:

1. Datei ist Browser-nativ (kein Remux nötig) und besitzt **kein** moov-at-start.
2. Cache fehlt oder ist älter als die Quelldatei (mtime).
3. Quelldatei ≥ 8 MiB (kleinere Dateien bauen ohnehin sofort).

Best-Effort, exception-safe, blockiert weder den Server-Start noch den
Catalog-Scan. Zur Pflege via CLI siehe `make video-prewarm` /
`hometools stream-prewarm --server video --mode missing` — dort wird der
gleiche Worker explizit aufgerufen.

---

## UI-Layout-Änderungen: Suchleisten-Umstrukturierung (2026-05-15)

### Bibliotheks-Suchleiste (Global Search) im Header

Die globale Bibliotheks-Suchleiste (`#global-search-input`) wurde aus dem `#folder-filter-bar`-Container (der dynamisch bestückt wurde) in den `<header>` direkt verschoben. Sie erscheint dauerhaft als letztes Element im Header-Flex-Container, rechts ausgerichtet.

- **CSS-Klasse:** `.header-search` — `flex: 0 1 200px`, `border-radius: 20px`, Pill-Form
- **Sichtbarkeit:** Gesteuert über `view-hidden`-Klasse. `initGlobalSearch()` entfernt die Klasse (zeigt an). `_hideGlobalSearch()` fügt sie wieder hinzu (versteckt).
- **Event-Wiring:** Nur einmalig via `_globalSearchListenersInit`-Flag — verhindert doppelte Listener-Registrierung.
- **`#folder-filter-bar`:** Bleibt im DOM (Tests prüfen `id="folder-filter-bar"`), aber immer `hidden`. Kein HTML-Inhalt mehr.

### Track-Count in der Filter-Bar

Der `<span id="track-count">` wurde aus dem `<header>` in die `.filter-bar` (Listen-Suchleiste) verschoben — als letztes Element mit `margin-left: auto`. Er zeigt die Anzahl der gefilterten Tracks direkt neben den Suchfiltern an.

### Filter-Bar Scroll-Reveal (erscheint beim Hochscrollen)

Die Listen-Suchleiste (`.filter-bar`) ist standardmäßig verborgen, wenn eine Playlist/Ordner-Ansicht geöffnet wird, und erscheint erst beim Hochscrollen.

**Mechanismus:**
1. Wenn `filterBar.classList.remove('view-hidden')` aufgerufen wird (in `showPlaylist`, `showUserPlaylistView`, `playDuplicates`), wird **sofort** `filterBar.classList.add('fb-scroll-hidden')` gesetzt — damit startet die Filter-Bar versteckt.
2. `_initFilterBarScrollReveal()` registriert (einmalig, via `_fbScrollInitDone`-Flag) einen `scroll`-EventListener auf `#track-view`.
3. Der Listener: wenn `scrollTop < 10` oder der User nach oben scrollt → `fb-scroll-hidden` entfernen (einblenden). Wenn nach unten gescrollt wird → `fb-scroll-hidden` hinzufügen (ausblenden).

**CSS:**
```css
.filter-bar {
  overflow: hidden;
  max-height: 100px;
  transition: max-height 0.22s ease, padding-top 0.22s ease, padding-bottom 0.22s ease, border-bottom-width 0.22s ease;
}
.filter-bar.fb-scroll-hidden {
  max-height: 0; padding-top: 0; padding-bottom: 0; border-bottom-width: 0;
}
```

**Alle Eintrittspunkte** (die die Filter-Bar sichtbar machen) rufen jetzt auch `_hideGlobalSearch()` auf und setzen `fb-scroll-hidden`, damit der Zustand konsistent ist.

---

## Waveform-Peak-Caching (Shadow Cache)

**Module:** `streaming/core/waveform.py`, `streaming/audio/server.py` (Endpunkt)

### Zweck

256 normalisierte Amplitude-Peak-Werte pro Kanal (L + R) werden via ffmpeg aus Audio-Dateien extrahiert und im Shadow-Cache gespeichert. Das ermöglicht eine stereo-bewusste Wellenform-Visualisierung im Classic-Mode Progress-Bar ohne client-seitiges Audio-Decoding.

### Pfad-Konvention

`<cache_dir>/audio/<relative_path>.waveform.json` — spiegelt die Library-Struktur exakt wider, analog zu Thumbnails (`.thumb.jpg`).

### Extraction (Stereo)

`extract_waveform_peaks(media_path, segments=256)` dekodiert via ffmpeg (`-ac 2 -f f32le -ar 1000 pipe:1`), deinterleaved die L/R-Samples (`all_samples[0::2]` / `all_samples[1::2]`), berechnet Peak-Absolutwert pro Segment-Block, normalisiert **gemeinsam** (relative Lautstärke zwischen Kanälen bleibt erhalten). Mono-Quellen werden von ffmpeg automatisch auf Stereo hochgemischt (beide Kanäle identisch). Gibt `(peaks_l, peaks_r) | None` zurück.

### Cache-Format

```json
{"peaks_l": [...256 floats 0.0–1.0...], "peaks_r": [...256 floats...], "segments": 256}
```

Backward-Kompatibilität: alte Caches mit nur `"peaks"`-Key → Client rendert Mono-Fallback.

### Cache-Lebenszyklus

- **MTime-Invalidierung:** Nur regeneriert wenn `source.mtime > cache.mtime`.
- **Background-Only:** `start_background_waveform_generation(items)` → Daemon-Thread `waveform-bg`.
- **On-Demand-Fallback:** `GET /api/audio/waveform?path=...` generiert synchron wenn Cache kalt ist.

### API-Endpunkt

`GET /api/audio/waveform?path=<relative_path>`
- Response: `{"peaks_l": [...], "peaks_r": [...], "segments": 256}`
- 404: Datei nicht im Cache + Generierung fehlgeschlagen
- 400: leerer `path`-Parameter

### Frontend-Integration (Classic-Modus)

- `var waveformData = null` (L-Kanal oder Legacy-Mono-Peaks)
- `var waveformDataR = null` (R-Kanal; `null` = Mono-Modus)
- `generateWaveform(url, relativePath)` fetcht `/api/audio/waveform`, befüllt beide Variablen
- `drawWaveform(progress)` zeichnet drei Zustände:

| Zustand | Layer 1 | Layer 2 |
|---------|---------|---------|
| **Stereo** | 1px weisse Mittellinie | L wächst nach oben, R nach unten; gespielt = Akzentfarbe α0.72, ungespielt = #999 α0.28 |
| **Mono** | 5px Progressbar (grau/Akzent) | Zentrierte Balken, weiss semi-transparent |
| **Leer** | 5px Progressbar | — |

Layer 3 (immer): weißer Playhead-Dot am aktuellen Fortschritt.

---

## `server_utils` Paket-Split

**Modul:** `streaming/core/server_utils/` (Paket, vorher monolithische Datei `server_utils.py` mit ~9000 Zeilen)

Die UI-Generierung lebte ursprünglich in einer einzigen `server_utils.py`-Datei,
die durch Wachstum auf >9000 Zeilen für Agent-gestützte Entwicklung
(Kontextfenster-Druck, Edit-Risiko, Navigations-Latenz) zum Problem wurde.
Die Datei wurde in ein Paket aufgeteilt — **rein strukturell, keine
Verhaltensänderung**.

### Struktur

| Datei | Inhalt | Zweck |
|-------|--------|-------|
| `__init__.py` | Re-Exports, `logger` | Backward-Compatible Public-API |
| `_svg.py` | 37 `SVG_*`-Konstanten (Icons + Flaggen) | Zentrale Icon-Bibliothek |
| `_css.py` | `render_base_css` | Komplettes dark-theme CSS als Python-String |
| `_player_js.py` | `render_player_js` | Großer JS-Generator (Player + Listen + Modals) |
| `_html.py` | `render_media_page` | Einziges HTML-Skelett für Audio + Video |
| `_pwa.py` | `render_pwa_manifest`, `render_pwa_service_worker`, `render_pwa_icon_svg`, `render_pwa_icon_png`, `render_pwa_head_tags` | PWA-Assets |
| `_audit.py` | `render_audit_panel_html` | Audit-Log-Panel |
| `_library.py` | `build_index_status_payload`, `check_library_accessible`, `render_error_page` | Status- & Fehlerseiten |
| `_paths.py` | `resolve_media_path`, `safe_resolve` | Pfad-Validierung gegen Traversal |

### Backward-Compatibility

`__init__.py` re-exportiert sämtliche öffentlichen Symbole. Externe Importe
wie `from hometools.streaming.core.server_utils import render_player_js`
oder `from hometools.streaming.core.server_utils import SVG_PLAY`
funktionieren **unverändert** — kein Aufruferkode wurde angepasst.

### Designregeln

- **Keine Quer-Imports zwischen den Submodulen außer für `_svg`.** `_player_js`
  importiert `SVG_*`-Konstanten via `from ._svg import ...`. Sonst keine
  Abhängigkeiten zwischen den Submodulen.
- **`__init__.py` enthält keine Logik**, nur Re-Exports. Wenn neue Helpers
  hinzukommen, gehören sie in eines der Submodule (oder ein neues).
- **Public-API-Drift vermeiden:** Wer ein neues Public-Symbol exportieren
  will, muss es explizit in `__init__.py` ergänzen.
- **Bestehende Architektur-Regeln (insb. Regel 13 SVG-Icons) gelten weiterhin.**
  Neue `SVG_*`-Konstanten kommen in `_svg.py` (nicht in `_player_js.py`).
- Architecture-Doku-Verweise auf `server_utils.py` bleiben gültig (das Paket
  trägt denselben Namen wie die alte Datei) und werden nicht massenhaft
  umgeschrieben.

## Library-Scan (`streaming/core/library_scan.py`)

Read-only Bibliotheks-Analyse für den CLI-Befehl `hometools scan-library`.

### Zweck

Kein ffprobe, keine External-APIs — rein dateisystembasiert. Hilft beim Erkennen
von Organisations-Problemen in der Videobibliothek, die durch `hometools_overrides.yaml`
oder Ordnerumbenennung gelöst werden könnten.

### Checks (Video)

| Check-Code          | Schwere     | Beschreibung |
|---------------------|-------------|--------------|
| `episode_naming`    | `warning`   | Ordner mit ≥ 4 Videodateien, aber < 50 % enthalten S##E##-Muster. Hinweis auf `generate-overrides`. |
| `oversized_folder`  | `info`      | Direktordner mit > 30 Videodateien ohne Unterordner-Struktur. |
| `untagged_language` | `info`      | Top-Level-Ordner ohne Sprach-Tag im Namen UND ohne `language`/`language_group`-Override. |

### Checks (Audio)

| Check-Code          | Schwere     | Beschreibung |
|---------------------|-------------|--------------|
| `oversized_folder`  | `info`      | Direktordner mit > 100 Audiodateien ohne Unterordner-Struktur. |

### API

```python
report = scan_video_library(library_dir, overrides=None)
report = scan_audio_library(library_dir)
```

`ScanReport.to_dict()` liefert JSON-serialisierbares Dict. `--fail-on-warning` gibt Exit-Code 1.

### CLI

```bash
hometools scan-library [--media video|audio] [--library-dir PATH] [--json] [--fail-on-warning]
```

### Designregeln

- Niemals originale Mediendateien modifizieren.
- Exception Safety: alle Public-Funktionen geben bei Fehler leere `ScanReport`-Instanz zurück.
- Overrides können pre-geladen übergeben werden (Effizienz-Optimierung für Tests und Batches).
- Schwellen (`oversized_threshold`, `min_files`, `min_ratio`) sind keyword-only Parameter
  für testbare Konfigurierbarkeit.

## Video-Server UI-Anpassungen

Der Video-Server unterscheidet sich an zwei Stellen bewusst vom Audio-Server.
Beide Anpassungen erfolgen im gemeinsamen `_player_js.py` über die Laufzeit-
flag `_isVideo = (ITEM_NOUN === 'video')`, sodass kein duplizierter Code in
`streaming/video/` entsteht.

### Tools-Row ohne Playlist-Aktionen

Auf dem Root-Screen des Video-Servers werden die Tools-Row-Karten
„Neue Playlist…", „Intelligente Playlist…" und „Titel" nicht gerendert.
Begründung: Playlists und Smart Playlists sind im Video-Streaming aktuell
ohne Mehrwert (keine Queue-Mechanik wie im Audio-Player), und „Titel" als
flache Liste aller Videos ist redundant zur Ordneransicht.

Die Karten existieren weiterhin im Audio-Server.  Der Block wird über
`if (isRoot && PLAYLISTS_ENABLED && !_isVideo)` geschützt.  Der „Neu laden"-
Button und „Downloaded"-Karte bleiben auch auf Video sichtbar.

### Sprachflagge am Folder-Card

Für Video-Folder wird **immer** eine einzelne Sprachflagge gerendert — auch
für mono-linguale Ordner ohne erkannte Sprache, die dann auf
`DEFAULT_LANG` zurückfallen.  Position: feste obere rechte Ecke der Karte
über die neue CSS-Klasse `.folder-lang-corner` (absolute Positionierung,
halbtransparenter dunkler Background damit die Flagge auf hellen Thumbnails
lesbar bleibt).

Verhalten:

- **Mono-Lingual** (`!hasVariants`): Flagge = `f.languages[0] || DEFAULT_LANG`,
  ggf. mit Sub-Sprache als Composite-Flagge.  Der bisherige inline
  `langBadges`-Span neben dem Folder-Namen wird auf Video unterdrückt, um
  keine doppelte Anzeige zu erzeugen.
- **Multi-Variant** (`hasVariants`): keine Eck-Flagge — die Variant-Flag-
  Buttons im `folder-count`-Bereich übernehmen die Sprachanzeige (jede
  Variante als klickbarer Button).

Audio-Server bleibt unverändert: die bisherigen kleinen Inline-Badges neben
dem Folder-Namen werden weiterhin nur bei tatsächlich erkannten Sprachen
gezeigt.


### iOS-Background-Playback (Auto-PiP)

Das `<video>`-Element trägt das Attribut `autopictureinpicture`.  Auf iOS
Safari (≥ 14) schiebt das System das Video beim Backgrounden der App
(Home-Button / App-Switcher) automatisch in das System-PiP-Overlay — ohne
User-Geste, ohne expliziten Aufruf.

**Voraussetzung:** Das Video muss zum Zeitpunkt von `visibilitychange`
*noch laufen*.  Der `visibilitychange`-Handler in `_player_js.py` darf
auf iOS daher **nicht** `player.pause()` aufrufen, da Safari die
PiP-Transition sonst abbricht (Regression sichtbar ab iOS 17).

Implementierung:

- iOS-Detection via UA + `MacIntel + maxTouchPoints>1` (`isIOS`-Flag).
- Bei `document.hidden && wasPlaying`:
  - PiP-Status prüfen: `document.pictureInPictureElement === player`
    bzw. `player.webkitPresentationMode === 'picture-in-picture'`.
  - `player.pause()` nur auf **Nicht-iOS** und nur wenn **nicht** in PiP.
  - Background-Audio-Mirror nur aktivieren wenn **nicht** in PiP
    (sonst Doppel-Ton parallel zum PiP-Video).
- Beim Zurückkehren in den Vordergrund: PiP explizit beenden,
  Video-Position aus Mirror synchronisieren, Mirror stummschalten.

Desktop-Verhalten unverändert: pause + bg-audio-mirror verhindert
Doppel-Ton bei Tab-Wechsel.


## Cast-Button (HTML5 Remote Playback API)

Im Video-Overlay-Header rechts neben dem Fullscreen-Button platzierter
`#video-cast-btn` (Icon `SVG_CAST`).  Erlaubt das Streamen des laufenden
`<video>` auf jedes erreichbare Cast-Ziel im Netzwerk — auf Philips
Android TV (Chromecast-built-in) oder Apple TV (AirPlay).

**Implementierung:** ausschließlich Standard-Browser-APIs, kein Google-Cast-
SDK, keine App-ID, kein zusätzlicher Netzwerk-Code im Server.

| Browser                                  | API                                                      |
|------------------------------------------|----------------------------------------------------------|
| Chromium (Android-Chrome, Desktop-Chrome, Edge) | `player.remote.watchAvailability()` + `player.remote.prompt()` |
| iOS Safari                               | `webkitplaybacktargetavailabilitychanged` + `webkitShowPlaybackTargetPicker()` |
| Firefox / Safari (macOS) / WebViews ohne Support | Button bleibt `hidden` — keine Regression                 |

**Sichtbarkeit:** Der Button startet `hidden` und wird **nur** entblendet,
wenn der Browser ein Cast-Ziel im Netzwerk gefunden hat.  Verbindungs-
status (`connect`/`disconnect`-Events) setzt die CSS-Klasse `.active`
am Button.

**Designregeln:**

- Cast ist **video-only** — der Button ist nur im Video-Overlay vorhanden,
  da nur `<video>` die Remote Playback API hat.
- Server-Container muss für das Cast-Gerät **erreichbar** sein.  Bei VLAN-
  Trennung scheitert das Casting, auch wenn der Picker das Ziel anbietet.
  Workaround dokumentiert in `docs/docker.md` (`network_mode: host`).
- Keine Native-TV-App nötig.  Bedienung bleibt am Handy/Tablet, Wiedergabe
  läuft am TV.  Falls später erweiterte Steuerung (Queue, Lautstärke)
  gewünscht ist, kann das Google-Cast-SDK additiv geladen werden, ohne
  diesen Pfad zu brechen.


## Docker-Deployment

Multi-Stage-Image (Python 3.12-slim + ffmpeg + tini, Non-Root-User
`hometools` mit konfigurierbarer UID/GID via Build-Arg).  `docker-compose.yml`
startet pro Service einen eigenen Container vom gleichen Image:

| Service | Port | Command         | Library-Mount                                       |
|---------|------|-----------------|------------------------------------------------------|
| audio   | 8010 | `serve-audio`   | `${AUDIO_LIBRARY_PATH}:/media/audio:ro`              |
| video   | 8011 | `serve-video`   | `${VIDEO_LIBRARY_PATH}:/media/video:ro`              |
| channel | 8012 | `serve-channel` | `${VIDEO_LIBRARY_PATH}:/media/video:ro` + Schedule   |

Gemeinsame Named-Volumes `hometools-cache` und `hometools-audit` halten
Shadow-Cache (`/data/cache`) und Audit-Log (`/data/audit`) getrennt von
der Library und überleben Container-Rebuilds.

**Konfigurations-Mapping (`.env`):**

| `.env`-Variable          | Wirkt auf                                | Default          |
|--------------------------|------------------------------------------|------------------|
| `PUID`, `PGID`           | Build-Arg, Owner für `/data` und Prozess | `1000` / `1000`  |
| `AUDIO_LIBRARY_PATH`     | Host-Pfad → `/media/audio`               | **pflicht**      |
| `VIDEO_LIBRARY_PATH`     | Host-Pfad → `/media/video`               | **pflicht**      |
| `AUDIO_PORT`/`VIDEO_PORT`/`CHANNEL_PORT` | Port-Mapping auf Host       | `8010/8011/8012` |
| `HOMETOOLS_*`            | Direkt durchgereichte Server-Env-Vars    | wie im Image     |

**Designregeln:**

1. Mounts standardmäßig `:ro` — Write-Features (Rating-POPM, Tag-Edit,
   File-Move, Soft-Delete) erfordern bewussten Wechsel auf `rw`.
2. `HOMETOOLS_STREAM_HOST=0.0.0.0` ist im Image fixiert; Erreichbarkeit
   regelt das Host-Port-Mapping.
3. `HOMETOOLS_CACHE_DIR=/data/cache`, `HOMETOOLS_AUDIT_DIR=/data/audit`
   sind im Image fixiert — die Volumes folgen dieser Konvention.
4. ffmpeg/ffprobe sind Pflicht-Runtime-Deps (Faststart-Cache,
   Channel-Transcode, Waveforms, Thumbnails).  Image-Bau ohne ffmpeg
   würde Features still ausfallen lassen.
5. `tini` als PID 1 sorgt für saubere SIGTERM-Weiterleitung an uvicorn,
   damit `docker compose down` nicht in den Kill-Timeout läuft.
6. Healthcheck nutzt den existierenden `/health`-Endpoint via `HC_PORT`-
   Env-Variable je Container (audio = 8010, video = 8011, channel = 8012).
7. Tests werden über `.dockerignore` aus dem Build ausgeschlossen — das
   Runtime-Image enthält ausschließlich Produktcode.
8. `serve-all`-Variante steht als auskommentierter `all-in-one`-Service
   im Compose zur Verfügung, ist aber nicht Default (drei separate
   Container = sauberere Logs und Restarts).


## Global Search — Ordner-/Serien-Treffer (2026-05-29)

`globalSearch(needle)` in `streaming/core/server_utils/_player_js.py`
durchsucht zuerst alle Ordner-Pfade und zeigt passende Ordner (bei Video
typischerweise Serien-Titel) **vor** den einzelnen Tracks/Episoden an.

**Vorgehen:**

1. Iteriere alle `allItems`, splitte `relative_path` in Segmente, sammle
   jeden Pfad-Prefix, dessen Leaf-Segment (oder dessen `cleanFolderName()`)
   den Such-Begriff enthält.
2. Zähle Items unter jedem Folder-Prefix → `count`.
3. Sortiere: flache Tiefe zuerst, dann größere Count, dann alphabetisch.
4. `renderSearchResults(results, folderMatches)` rendert Ordner-Items
   (CSS-Klasse `.search-folder-item`, Folder-Icon, "Ordner"-Label,
   Klick → `navigateToSearchFolder(path)` → verlässt Search-Modus und
   navigiert in den Ordner) **vor** den Track-Items.

Header zeigt z. B. `"3 Ordner · 27 Videos"` statt nur Track-Count.

## Indexing-Toast — antippen zum Ausblenden (2026-05-29)

Die „Building index…"-Benachrichtigung (`.ht-indexing-toast`) verdeckte
auf schmalen Viewports die Header-Suchleiste. Lösung:

- **Auf Mobile** (`max-width: 600px`) positioniert per Media-Query an
  `bottom: calc(env(safe-area-inset-bottom) + 84px); right: 0.5rem;`
  also direkt über der Player-Bar.
- **Tap-to-dismiss:** `pointer-events: auto; cursor: pointer`, Click
  setzt `_indexToastDismissed = true`. Solange das Flag steht, ruft
  `showIndexingToast()` früh `return` — der Hintergrund-Poll
  (`scheduleBackgroundRefresh`) läuft weiter, zeigt aber nichts.
- **Reset:** `hideIndexingToast()` (Index ist fertig) setzt das Flag
  zurück → nächste Indexing-Runde zeigt den Toast wieder an.
