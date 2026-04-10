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
- Python-Konstanten: `SVG_PLAY`, `SVG_PAUSE`, `SVG_PREV`, `SVG_NEXT`, `SVG_PIP`, `SVG_BACK`, `SVG_MENU`, `SVG_DOWNLOAD`, `SVG_CHECK`, `SVG_FOLDER_PLAY`, `SVG_PIN`, `SVG_STAR`, `SVG_PLAYLIST`, `SVG_QUEUE`, `SVG_REFRESH` in `server_utils.py`
- JS-Variablen: `IC_PLAY`, `IC_PAUSE`, `IC_DL`, `IC_CHECK`, `IC_GRID`, `IC_LIST`, `IC_PIN`, `IC_STAR`, `IC_FOLDER_PLAY`, `IC_PLAYLIST`, `IC_QUEUE`, `IC_REMOVE`, `IC_REFRESH` — über `innerHTML` gesetzt (nicht `textContent`)
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

**Audio:** `get_popm_rating(path)` liest den rohen ID3-POPM-Tag (Popularimeter, 0–255). Die Konvertierung in Sterne erfolgt über `popm_raw_to_stars()` mit dem **Windows Media Player Standard-Mapping** (nicht linear!):

| Raw-Bereich | Sterne | Kanonischer Wert |
|-------------|--------|-----------------|
| 0           | 0 (unbewertet) | 0 |
| 1–31        | 1★     | 1   |
| 32–95       | 2★     | 64  |
| 96–159      | 3★     | 128 |
| 160–223     | 4★     | 196 |
| 224–255     | 5★     | 255 |

Umgekehrt schreibt `stars_to_popm_raw()` die kanonischen WMP-Werte. Dadurch sind Bewertungen mit foobar2000, MusicBee, Mp3tag und Windows Explorer kompatibel.

Nur MP3/ID3-Dateien werden ausgelesen — M4A/FLAC und andere Formate geben `0.0` zurück ohne Exception. Der `/api/audio/metadata`-Endpoint gibt das Rating ebenfalls zurück.

**Video:** Kein Rating-Lesen; Defaultwert `0.0`.

**UI:** Eine 3px hohe Verlaufsleiste (orange–gelb) erscheint am unteren Rand des Thumbnail-Bilds — sowohl in Track-Listen als auch in Folder-Grid-Karten. Die Breite entspricht `rating / 5 * 100 %`. Unbewertet = keine Leiste. CSS-Klasse `.rating-bar`.

**Design-Regeln:**
- `popm_raw_to_stars()` und `stars_to_popm_raw()` in `audio/metadata.py` sind die einzigen Stellen für POPM↔Sterne-Konvertierung. Niemals manuell `raw/255*5` oder `stars/5*255` rechnen.
- `get_popm_rating()` prüft vor dem ID3-Lesen die Dateiendung; gibt bei M4A/FLAC `0` zurück um den `can't sync to MPEG frame`-Fehler zu vermeiden.
- **Snapshot-Versionierung:** `_SNAPSHOT_VERSION` in `index_cache.py` muss gebumpt werden, wenn sich das Datenformat ändert (z.B. Rating-Mapping). Alte Snapshots werden beim Laden verworfen, erzwingen frischen Rebuild vom Dateisystem. Aktuell: v2 (WMP-Mapping).

### Rating-Schwellenwert (Min-Rating)

Konfigurierbar über `HOMETOOLS_MIN_RATING` (Env-Var, Default `0`, Bereich 0–5).

Bewertete Tracks mit Rating **≤ Schwellenwert** werden aus der Track-Liste ausgeblendet. Unbewertete Tracks (`rating == 0`) sind immer sichtbar — sie gelten als „nicht bewertet", nicht als „schlecht bewertet".

**Implementierung:** Die Funktion `get_min_rating()` in `config.py` liest den Wert. Er wird als `min_rating` Parameter durch `render_media_page()` → `render_player_js()` durchgereicht und als JS-Variable `MIN_RATING_THRESHOLD` injiziert. Die Filterung erfolgt in `applyFilter()` (JS) **vor** allen anderen Quick-Filtern:
```js
if (MIN_RATING_THRESHOLD > 0) {
  items = items.filter(function(t) {
    var r = t.rating || 0;
    return r === 0 || r > MIN_RATING_THRESHOLD;
  });
}
```

**Beispiel:** `HOMETOOLS_MIN_RATING=2` blendet alle 1★ und 2★ Tracks aus, zeigt aber unbewertete und 3★+ Tracks.

### Lazy Per-Folder Rating Refresh

Beim Öffnen eines Ordners (Leaf-Folder → `showPlaylist`) werden die POPM-Ratings der angezeigten Tracks on-demand vom Dateisystem neu gelesen — **ohne** den gesamten Katalog neu zu bauen. Das löst das Problem, dass ein Full-Rebuild von 5 000+ Songs mehrere Sekunden dauert und alte Ratings bis dahin sichtbar bleiben.

**Ablauf:**
1. `showPlaylist(items, ...)` rendert sofort mit den gecachten Daten (kein Delay).
2. JS `refreshFolderRatings(items)` feuert einen asynchronen `POST /api/audio/refresh-ratings` mit den `relative_path`-Werten der Folder-Items.
3. Der Server liest nur die übergebenen Dateien (typisch 10–50) via `get_popm_rating()` + `popm_raw_to_stars()`.
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

**Begründungstexte:** z.B. `"Rating 2★ ≤ Schwelle 3"`, `"Quick-Filter: Rating < 4★"`, `"Kein Favorit"`, `"Genre ≠ Rock"`

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
- Python-Konstanten: `SVG_*` in `server_utils.py` (inkl. `SVG_STAR`, `SVG_STAR_EMPTY`, `SVG_SHUFFLE`, `SVG_REPEAT`, `SVG_HISTORY`, `SVG_PLAYLIST`)
- JS-Variablen: `IC_*` in der generierten JS-Seite (inkl. `IC_STAR`, `IC_STAR_FILLED`, `IC_STAR_EMPTY`, `IC_SHUFFLE`, `IC_PLAYLIST`)
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
- Beide Server lesen **denselben** JSONL (shared `audit_dir`) — Audio-Ratings sind im Video-Control-Panel sichtbar.
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
- Konvertiert `stars → POPM raw` via `stars_to_popm_raw()` (WMP-Standard: 0→0, 1→1, 2→64, 3→128, 4→196, 5→255)
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

## Ansichtsumschalter (view toggle) – drei Modi

Der Header-Button `#view-toggle` schaltet zyklisch durch drei Modi:

| Modus | CSS-Klassen auf `#folder-grid` | Thumbnail | Anzeigename | Tooltip |
|---|---|---|---|---|
| `'list'` | `list-mode` | Klein | Listenansicht | „Listenansicht — Klick für Kachelansicht" |
| `'grid'` | — | Groß | Galerieansicht / Kacheln | „Kachelansicht — Klick für Dateinamen" |
| `'filenames'` | `list-mode filenames-mode` | Groß | Original-Dateinamen | „Dateinamen — Klick für Listenansicht" |

Im Modus `'filenames'` werden die rohen Dateinamen angezeigt (kein Display-Name/Override). Dieses Verhalten ersetzt jegliche separate „\[ \] Original"-Checkbox – der Toggle ist die einzige UI-Stelle für dieses Feature.

**DnD-Reorder ist nur im `filenames`-Modus aktiv** (+ Playlist-Kontext). In `list` und `grid` ist Drag-and-Drop deaktiviert — Klick auf einen Track spielt ihn ab.

Reihenfolge: `list → grid → filenames → list`

Gespeichert in `localStorage` unter `ht-view-mode`.

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

**Module:** `streaming/core/playlists.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py`

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
6. „Neue Playlist…"-Karte (`.playlist-new-card`)
7. „Zur Playlist hinzufügen"-Modal (`#playlist-modal-backdrop`)

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

### Server-seitige Ordner-Reihenfolge (Custom Order)

Neues Core-Modul `streaming/core/custom_order.py` persistiert benutzerdefinierte Item-Reihenfolgen pro Ordner (und für Favoriten) auf dem Server. Damit überlebt die Sortierung Browser-Clear und funktioniert geräteübergreifend.

**Storage:** `<cache_dir>/custom_order/<server>/<md5_hash>.json` — MD5-Hash des normalisierten Ordner-Pfads als Dateiname. Für Favoriten wird `__favorites__` als Pfad verwendet.

**API-Endpoints:**
- `GET /api/<media>/folder-order?path=<folder>` — Reihenfolge laden
- `PUT /api/<media>/folder-order` (`{folder_path, items: [...]}`) — Reihenfolge speichern
- `DELETE /api/<media>/folder-order?path=<folder>` — Reihenfolge löschen

**Dual-Source-Strategie (JS):**
- **Speichern:** `_saveFolderOrder()` / `_saveFavoritesOrder()` schreiben sowohl in `localStorage` (sofort) als auch per `PUT` an den Server (fire-and-forget).
- **Laden:** Synchron aus `localStorage` für sofortige Anzeige. Parallel `_loadFolderOrderAsync()` / `_loadFavoritesOrderAsync()` fetcht vom Server. Wenn der Server eine andere Reihenfolge hat, wird `localStorage` aktualisiert und die Ansicht re-sortiert.
- **Offline-Fallback:** Bei Server-Fehler wird ausschließlich auf `localStorage` zurückgegriffen.

**JS-Variable:** `FOLDER_ORDER_API_PATH` (abgeleitet aus `api_path`).

**Thread-Sicherheit:** Module-level Lock, atomare Schreibvorgänge via `NamedTemporaryFile` + `replace` (analog zu `playlists.py`).

## Crossfade (Audio-only)

**Modul:** `streaming/core/server_utils.py` (JS), `config.py` (Env-Var), rein client-seitig.

Nahtlose Übergänge zwischen Songs: Der aktuelle Track wird ausgeblendet (fade-out) während der nächste Track parallel eingeblendet wird (fade-in). Nur für Audio, nicht für Video.

### Konfiguration

- `HOMETOOLS_CROSSFADE_DURATION` Env-Var: Dauer in Sekunden (Default `0` = deaktiviert, Max `12`)
- `get_crossfade_duration()` in `config.py` — clamped auf 0–12
- `crossfade_duration` Parameter durchgereicht: `render_media_page()` → `render_player_js()` → `CROSSFADE_DURATION` JS-Variable
- Audio-Server liest aus Config, Video-Server nutzt Default `0` (kein Crossfade)

### JS-Architektur

**State-Variablen:**
- `_xfadeAudio` — Zweites `<audio>`-Element (lazy erstellt, `display: none`)
- `_xfading` — Boolean, ob ein Crossfade läuft
- `_xfadeTimer` — `setInterval`-ID für die Volume-Rampe
- `_xfadeNextItem` / `_xfadeNextIndex` — Das Item/Index in das übergefadet wird

**Funktionen:**
- `_resolveNextForCrossfade()` — Bestimmt den nächsten Track **ohne** Queue zu konsumieren oder State zu ändern (Queue-Peeking)
- `_startCrossfade()` — Erstellt/konfiguriert `_xfadeAudio`, startet Playback bei `volume=0`, initiiert Volume-Rampe
- `_finishCrossfade()` — Speichert Progress des alten Tracks, konsumiert Queue-Item falls nötig, ruft `playTrack()`/`playFromQueue()` auf, setzt `player.volume = 1`
- `_xfadeCleanup()` — Bricht laufenden Crossfade ab, stoppt Timer, pausiert xfade-Audio

### Trigger

- **`timeupdate`-Event:** Wenn `CROSSFADE_DURATION > 0 && !_xfading && !isVideoPlayer`, verbleibende Zeit ≤ `CROSSFADE_DURATION`, und Track lang genug (`duration > CROSSFADE_DURATION + 5`), wird `_startCrossfade()` aufgerufen
- **Schutz gegen kurze Tracks:** Tracks kürzer als `CROSSFADE_DURATION + 5s` werden ohne Crossfade abgespielt (verhindert Overlap-Chaos)

### Volume-Rampe

- 20 Schritte über `CROSSFADE_DURATION` Sekunden (50ms pro Schritt bei 1s, 250ms bei 5s)
- Sinusoide Ease-Kurve: `ease = 0.5 - 0.5 * cos(π * progress)` für natürlichen Übergang
- Ausgehender Track: `player.volume = 1 - ease`
- Eingehender Track: `_xfadeAudio.volume = ease`

### Abbruch-Szenarien

- **Manueller Track-Wechsel** (`playItem`): `_xfadeCleanup()` + `player.volume = 1`
- **User-Pause**: `_xfadeCleanup()` + `player.volume = 1`
- **Track endet während Crossfade**: `_finishCrossfade()` wird aufgerufen statt `playNextItem()`

### Designregeln

1. **Audio-only** — `!isVideoPlayer`-Guard im Trigger. Video hat kein Crossfade.
2. **Queue-kompatibel** — `_resolveNextForCrossfade()` peeked in die Queue, `_finishCrossfade()` konsumiert via `playFromQueue()`.
3. **Kein Einfluss auf Progress-Speicherung** — Progress wird weiterhin normal gespeichert. `_finishCrossfade()` ruft `saveProgressNow()` + `clearProgressFor()` für den ausgehenden Track.
4. **Volume statt muted** — Crossfade nutzt `player.volume` (0–1), nicht `muted`. Das ist korrekt weil Audio (nicht Video) kein `bgAudio`-Element benötigt und iOS-Volume-Beschränkungen nur `bgAudio` betreffen.
5. **Konfigurierbar bis deaktiviert** — Default `0` = aus. Nutzer wählt Dauer selbst. Max 12s Obergrenze.

## Katalog-Refresh (manuell)

**Module:** `streaming/core/server_utils.py` (UI + JS), `streaming/audio/server.py`, `streaming/video/server.py`

Ermöglicht dem Benutzer, den In-Memory-Index-Cache manuell zu invalidieren und eine frische Neuindexierung vom Dateisystem zu erzwingen.

### API

- `POST /api/audio/refresh` — Audio-Index invalidieren, Background-Rebuild starten
- `POST /api/video/refresh` — Video-Index invalidieren, Background-Rebuild starten

Response: `{"ok": true, "detail": "Refresh started"}`

Beide Endpoints invalidieren den `IndexCache` (`invalidate()`), setzen den Quick-Scan-Cache zurück und starten `ensure_background_refresh()`. Das nächste `GET /api/<media>/tracks` (bzw. `/items`) liefert dann frische Filesystem-Daten.

### Frontend

- **Button:** `#refresh-btn` im `<header>`, SVG-Icon `SVG_REFRESH` / `IC_REFRESH`
- **CSS:** `.refresh-btn` (gleicher Style wie `.view-toggle`), `.refresh-btn.spinning svg` rotiert via `@keyframes spin`
- **JS:** `refreshCatalog()` → `POST` an `/api/<media>/refresh` → `fetch(API_PATH)` → `allItems` aktualisieren → aktuelle Ansicht neu rendern. Toast-Feedback: „Katalog aktualisiert — N Titel"

### Designregeln

1. **Shared-Core-UI** — Button und JS leben in `server_utils.py`, nicht dupliziert pro Server
2. **POST statt GET** — Refresh ist eine Zustandsänderung (Cache-Invalidierung), daher POST
3. **Debounce via Spinning** — Während des Refresh dreht das Icon; kein Doppelklick nötig
4. **Ansichts-bewahrend** — Nach dem Refresh wird die aktuelle Ansicht (Folder oder Playlist) beibehalten
