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

- `audio/` — Audio-Thumbnails (Cover-Art, 120px + 480px)
- `video/` — Video-Thumbnails (Frame-Extraktion via ffmpeg, 120px + 480px)
- `indexes/` — Persisted Index-Snapshots (JSON, library-dir-spezifisch via MD5-Hash)
- `progress/` — Wiedergabe-Fortschritt (JSON)
- `issues/` — Issue-Registry, TODO-Kandidaten, Scheduler-Logs
- `logs/` — Server-Log-Dateien
- `thumbnail_failures.json` — Failure-Registry für fehlgeschlagene Thumbnails
- `video_metadata_cache.json` — Persistierter Metadaten-Cache (ffprobe-Ergebnisse)

### Index-Snapshots

Der vollständige Index wird nach einem erfolgreichen Rebuild atomar als JSON-Snapshot gespeichert (`_save_snapshot`). **Es gibt kein inkrementelles Speichern während des Builds** — wird der Server während der Indizierung beendet, geht der laufende Scan-Fortschritt verloren. Der **letzte erfolgreiche Snapshot bleibt erhalten** und wird beim nächsten Start als Fallback geladen, sodass der Server sofort funktionsfähig ist (ohne Scan-Wartezeit).

### Thumbnails

Zwei Größen pro Mediendatei:
- **Klein** (120px, `.thumb.jpg`) — für Listen- und Grid-Ansichten, schnell ladend
- **Groß** (480px, `.thumb-lg.jpg`) — für Serien-Vorschauen und Detail-Ansichten, nachladend

Beide werden im Hintergrund-Thread generiert (`start_background_thumbnail_generation`). MTime-basierte Invalidierung: Thumbnails werden regeneriert wenn die Quelldatei neuer ist.

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
- Beim Track-Wechsel: letzte Position laden, Toast „Fortfahren bei X:XX" anzeigen

## Recently Added (Sortierung nach Neuheit)

`MediaItem` trägt ein `mtime`-Feld (Unix-Timestamp der Datei, via `stat()`). Die Sortier-Option `"recent"` sortiert absteigend nach `mtime` mit Titel als Tiebreaker. Sowohl server-seitig (`sort_items()`) als auch client-seitig (`applyFilter()`) implementiert.

## SVG-Icons

Alle Player-Buttons und UI-Controls verwenden **inline SVGs** statt Unicode-Zeichen. iOS rendert Unicode-Steuerzeichen (▶ ◄ ► ⏸ ⊞ ↓) als farbige Emojis, was das Layout zerstört.

**Konvention:**
- Python-Konstanten: `SVG_PLAY`, `SVG_PAUSE`, `SVG_PREV`, `SVG_NEXT`, `SVG_PIP`, `SVG_BACK`, `SVG_MENU`, `SVG_DOWNLOAD`, `SVG_CHECK`, `SVG_FOLDER_PLAY`, `SVG_PIN`, `SVG_STAR` in `server_utils.py`
- JS-Variablen: `IC_PLAY`, `IC_PAUSE`, `IC_DL`, `IC_CHECK`, `IC_GRID`, `IC_LIST`, `IC_PIN`, `IC_STAR`, `IC_FOLDER_PLAY` — über `innerHTML` gesetzt (nicht `textContent`)
- Alle SVGs nutzen `currentColor` für Theme-Kompatibilität
- **Nie** Unicode-Zeichen oder HTML-Entities (`&#9733;`, `&#9654;` etc.) — iOS rendert sie als Emoji

## PWA Shortcuts & Deep Linking

**Module:** `streaming/core/shortcuts.py`, `streaming/core/server_utils.py` (JS)

Benutzer können einzelne Medien-Items als Favoriten „pinnen" und auf den Home-Bildschirm speichern.

### Deep Linking

URL-Parameter `?id=<relative_path>` auf der Root-Route (`/`) beider Server. Das JS liest den Parameter nach dem Catalog-Load, navigiert automatisch zum Ordner des Items und startet die Wiedergabe. Die URL wird danach via `history.replaceState` bereinigt.

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

**Audio:** `get_popm_rating(path)` liest den ID3-POPM-Tag (Popularimeter, 0–255) und konvertiert ihn linear auf 0.0–5.0 Sterne. Nur MP3/ID3-Dateien werden ausgelesen — M4A/FLAC und andere Formate geben `0.0` zurück ohne Exception. Der `/api/audio/metadata`-Endpoint gibt das Rating ebenfalls zurück.

**Video:** Kein Rating-Lesen; Defaultwert `0.0`.

**UI:** Eine 3px hohe Verlaufsleiste (orange–gelb) erscheint am unteren Rand des Thumbnail-Bilds — sowohl in Track-Listen als auch in Folder-Grid-Karten. Die Breite entspricht `rating / 5 * 100 %`. Unbewertet = keine Leiste. CSS-Klasse `.rating-bar`.

**Design-Regeln:**
- Schreiben von Ratings aus dem Browser ist nicht implementiert (kein Write-Endpoint).
- `get_popm_rating()` prüft vor dem ID3-Lesen die Dateiendung; gibt bei M4A/FLAC `0` zurück um den `can't sync to MPEG frame`-Fehler zu vermeiden.

## Server-Logging

**Modul:** `logging_config.py`

`get_log_dir()` gibt `<cache_dir>/logs/` zurück und erstellt das Verzeichnis bei Bedarf. Beide Server-Commands (`serve-audio`, `serve-video`, `serve-all`) leiten Logs an eine rotierende Datei `hometools.log` (5 MB max, 3 Backups) weiter. Logs erscheinen gleichzeitig auf stdout. Sync-Commands (`sync-audio`, `sync-video`) schreiben nur auf stdout (kein `log_file`).

## Folder-Favorites (Namens-Konvention)

Ordner, deren Name mit `#` beginnt, werden als Favoriten behandelt:
- Sie erscheinen im Folder-Grid **zuerst** (vor alphabetischer Sortierung).
- Sie erhalten den CSS-Border `.fav-folder` (accent-farbener Rahmen).
- Ein **SVG-Stern-Badge** (`IC_STAR`, `.fav-badge`) wird absolut oben-rechts auf der Folder-Karte angezeigt (kein Unicode `&#9733;` — iOS-Emoji-Kompatibilität).
- Das `#`-Prefix wird im `displayName` entfernt, sodass in der UI nur der eigentliche Name erscheint.

Folder-Favorites sind **nicht** interaktiv toggle-bar aus dem Browser. Änderungen erfordern Umbenennen des Verzeichnisses auf dem NAS (via separatem `rename`-Workflow — Regel 9: „File renames must be proposed, never auto-applied").

**CSS-Konvention für SVG-Icons:**
- Python-Konstanten: `SVG_*` in `server_utils.py` (inkl. `SVG_STAR`, `SVG_STAR_EMPTY`, `SVG_SHUFFLE`, `SVG_REPEAT`, `SVG_HISTORY`)
- JS-Variablen: `IC_*` in der generierten JS-Seite (inkl. `IC_STAR`, `IC_STAR_FILLED`, `IC_STAR_EMPTY`, `IC_SHUFFLE`)
- Alle SVGs nutzen `currentColor` für Theme-Kompatibilität
- Kein Unicode/HTML-Entities (`&#9733;`, `&#9654;` etc.) — sie rendern auf iOS als farbige Emojis

## Audit-Log & Change-Log

**Module:** `streaming/core/audit_log.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py` (`render_audit_panel_html`)

### Zweck

Jede Dateisystem-Änderung (Rating-Schreiben, künftig: Tag-Edits, Umbenennen) wird als unveränderlicher JSONL-Eintrag protokolliert. Das ermöglicht:
- **Undo** — Versehentliche Änderungen rückgängig machen (aus App oder Control Panel)
- **Bewertungsverlauf** — Alle Rating-Änderungen eines Songs nachvollziehen (inkl. Zeitstempel)
- **Audit** — Vollständige, manipulationssichere Protokollierung aller Writes

### Storage

```
<cache_dir>/audit/audit.jsonl    ← append-only JSONL, eine JSON-Zeile pro Eintrag
```

Atomic writes via `threading.Lock()`. Undo-Operation schreibt mit `tmp → rename`-Strategie (atomic replace).

### Eintrag-Schema

```python
AuditEntry(
    entry_id:    str,    # UUID — referenzierbar für Undo
    timestamp:   str,    # ISO 8601 UTC
    action:      str,    # "rating_write" | "tag_write" | "file_rename"
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
- **Audio-Server:** `rating_write` → `set_popm_rating(path, old_raw)` + Cache-Invalidierung
- **Video-Server:** noch keine Write-Ops → `POST /api/video/audit/undo` gibt 422 zurück

### Control Panel (`/audit`)

Eigenständige Dark-Theme-HTML-Seite (generiert durch `render_audit_panel_html()`):
- Filterbar nach Dateiname und Aktion
- Tabelle: Zeitpunkt | Aktion | Datei | Änderung (`old → new`) | Rückgängig-Button
- Sterndarstellung für Ratings (★☆ statt Zahlen)
- `MEDIA_TYPE` JS-Variable steuert welchen API-Pfad das JS verwendet
- URL-Parameter `?path_filter=…` für Deep-Link in Bewertungshistorie einer Datei

### App-Integration (Undo-Toast)

Nach erfolgreichem Rating-Write gibt der Endpoint `entry_id` zurück. Das JS zeigt einen Toast mit "Rückgängig"-Button (5 s sichtbar). Klick ruft `undoRating(entryId, prevStars)` → `POST /api/audio/audit/undo` → Rating im Player-State zurückgesetzt.

### Design-Regeln

- Audit-Log ist **append-only** — Einträge werden nie gelöscht, nur als `undone` markiert.
- `old_value` wird **vor** dem Schreiben gelesen (via `get_popm_rating()` vor `set_popm_rating()`).
- `undo_payload.entry_id` enthält die eigene UUID — beim Undo wird die ID aus dem Payload validiert.
- Fehler beim Log-Schreiben unterbrechen **nie** den eigentlichen Write-Vorgang (silent fail + logging).
- Beide Server lesen **denselben** JSONL (shared `cache_dir`) — Audio-Ratings sind im Video-Control-Panel sichtbar.
- **⚠️ Escaping-Pitfall:** In Python-Triple-Quoted-Strings (`"""..."""`) werden `\'`-Escape-Sequenzen zu `'` verarbeitet. Niemals `onclick="..."` mit `\'`-Escaping in Python-Strings erzeugen — führt zu kaputtem JS (`''` statt `\'`) und einem Komplettausfall des `<script>`-Tags. Stattdessen **immer `createElement` + `addEventListener`** für DOM-Interaktionen aus Python-generierten Strings verwenden.

## Songwertung Schreiben (POPM-Write, Audio-only)

**Module:** `streaming/audio/server.py` (Endpoint), `audio/metadata.py` (`set_popm_rating`), `streaming/core/server_utils.py` (UI + JS)

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
- Konvertiert `stars → POPM raw (0–255)` via `round(stars / 5 * 255)`
- Schreibt via `set_popm_rating(path, raw)` aus `audio/metadata.py`
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
- `set_popm_rating()` prüft nicht die Dateiendung — Caller (Endpoint) muss sicherstellen, dass nur MP3-Dateien übergeben werden (POPM ist ID3-spezifisch).

## Shuffle-Modus (Audio-only)
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

## Header-Navigation

Der Header besteht aus vier Elementen:

| Element | ID/Klasse | Funktion |
|---|---|---|
| `<button class="logo-home-btn" id="header-logo">` | Emoji (🎬 / 🎵) | Klick → **immer** zurück zur Startseite (`currentPath = ''; showFolderView()`) |
| `<span class="logo-title" id="header-title">` | App-Titel | Reiner Text, **kein Link** — zeigt Ordner-Tiefe oder App-Titel |
| `<button class="back-btn" id="back-btn">` | SVG-Pfeil | Zurück eine Ebene |
| `<a class="audit-btn" href="/audit">` | `SVG_HISTORY` (Uhr-Icon) | Öffnet das Audit/Control-Panel in derselben Registerkarte |

**Design-Regeln:**
- Emoji-Button (`logo-home-btn`) navigiert immer zur Root-Ansicht — auch wenn man bereits dort ist.
- `headerTitle` im JS zeigt den aktuellen Pfad-Leaf-Name oder `originalTitle` (App-Titel). Der Titel-Span hat keinen eigenen Click-Handler.
- `originalTitle` wird aus `headerTitle.textContent` gelesen — enthält nur den Titel-Text ohne Emoji.
- Der Audit-Button ist ein `<a>`-Tag (kein `<button>`) — ermöglicht normales Browser-Navigationsverhalten (Back-Button funktioniert). CSS-Klasse `.audit-btn` hat denselben Stil wie `.view-toggle`.

## Player-Sichtbarkeit (Bug-Fix: currentSrc statt currentIndex)

**Problem:** `showFolderView()` versteckte die Player-Bar mit `if (currentIndex < 0) playerBar.classList.add('view-hidden')`. Das führte dazu, dass der Player nach Navigation in die Offline-Bibliothek (→ `showPlaylist()` setzt `currentIndex = -1`) und zurück zur Startseite unsichtbar wurde, obwohl noch Musik spielte.

**Fix:** Alle 4 Stellen in `showFolderView()`, `showLoadingState()` und `showCatalogLoadError()` wurden auf `if (!player.currentSrc) playerBar.classList.add('view-hidden')` umgestellt.

**Semantik:**
- `player.currentSrc === ''` → nichts wurde je geladen → Player-Bar verbergen ✓
- `player.currentSrc !== ''` → Quelle geladen (auch wenn pausiert) → Player-Bar sichtbar ✓

**Design-Regel:** Niemals `currentIndex` zur Bestimmung der Player-Sichtbarkeit verwenden — `currentIndex` ist playlist-lokal und wird bei Navigation (`showPlaylist()`) zurückgesetzt. `player.currentSrc` spiegelt den tatsächlichen Lade-Zustand des Media-Elements wider.
