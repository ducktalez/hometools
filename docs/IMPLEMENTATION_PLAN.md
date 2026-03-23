# Implementation Plan

## Next tasks

- **Phase 2: PWA Shortcuts** — Einzelne Filme/Songs auf Home-Bildschirm speichern (Deep Linking + Quick Access)

## Done

- FastStart-Erkennung für MP4-Dateien — `has_faststart()` in `streaming/core/remux.py` parst die MP4-Atom-Struktur (ftyp/moov/mdat) und erkennt Dateien mit `moov`-Atom am Ende; `/video/stream`-Endpoint leitet solche Dateien automatisch durch `remux_stream()` (`-c copy -movflags frag_keyframe+empty_moov`) statt per `FileResponse` — Browser kann sofort abspielen statt die gesamte Datei herunterzuladen; 7 neue Tests für `has_faststart()` und Endpoint-Integration

- SVG-Icons statt Unicode/Emoji — Alle Player-Buttons (Play/Pause/Prev/Next/PiP), Folder-Play, Download, Back, View-Toggle und Menu von Unicode-Zeichen auf inline SVGs umgestellt; rendert auf iOS/Android/Desktop konsistent ohne Emoji-Darstellung; CSS und JS für `innerHTML`-Swap angepasst; `IC_PLAY`/`IC_PAUSE`/`IC_DL`/`IC_CHECK`/`IC_GRID`/`IC_LIST` als JS-Variablen
- Shadow-Cache ins Repository — Default von `get_cache_dir()` auf `.hometools-cache/` im Repo-Root geändert (war `~/hometools-cache`); `.gitignore` aktualisiert; `HOMETOOLS_CACHE_DIR` überschreibt weiterhin; Copilot-Instructions und `architecture.md` aktualisiert
- Große Thumbnails (480 px) — Zweite Thumbnail-Größe (`THUMB_LG_MAX_PX = 480`, Suffix `.thumb-lg.jpg`) neben den kleinen (120 px); `_generate_large_thumbnail()` im Background-Worker; `/thumb?size=lg` Endpoint auf Audio- und Video-Server; `thumbnail_lg_url`-Feld auf `MediaItem`; Ordner-Karten nutzen große Thumbnails (Fallback auf kleine); Tests und Feature-Parity erweitert

- Wiedergabe-Fortschritt speichern — Neues Shared-Core-Modul `streaming/core/progress.py` mit thread-sicherem, atomarem JSON-Storage im Shadow-Cache (`progress/playback_progress.json`); `POST /api/<media>/progress` speichert `{relative_path, position_seconds, duration}`, `GET /api/<media>/progress?path=…` lädt gespeicherten Stand; Client-JS sendet debounced Progress alle 5s via `timeupdate`, speichert sofort bei Pause, löscht bei `ended`; beim Track-Wechsel wird letzte Position geladen und mit Toast „Fortfahren bei X:XX" angezeigt; Feature-Parity für Audio und Video
- Recently Added-Sektion — `MediaItem` um `mtime`-Feld erweitert (Unix-Timestamp der Datei); `sort_items()` um `"recent"`-Sortieroption ergänzt (absteigend nach `mtime`, Titel als Tiebreaker); Audio-, Video- und Quick-Folder-Scan befüllen `mtime` per `stat()`; Sort-Dropdown im UI um „Neueste ⇅"-Option erweitert; Client-JS sortiert ebenfalls nach `mtime`; Service-Worker-Cache-Version hochgezählt (v5→v6)
- Server-seitige Transkodierung für nicht-streambare Formate — `streaming/core/remux.py` mit `needs_remux()`, `probe_codecs()`, `can_copy_codecs()`, `remux_stream()`; `/video/stream`-Endpoint remuxed (container-copy) oder transkodiert (XviD→H.264) on-the-fly zu fragmented MP4; UI zeigt ⚡-Badge bei Dateien, die Konvertierung benötigen; `NON_STREAMABLE_EXT`-Markierung entfernt (alle Formate jetzt streambar)
- Serien-Episoden-Ordnung — `parse_season_episode()` in `streaming/core/catalog.py` als zentrale Parsing-Funktion; `MediaItem` um `season`/`episode` erweitert; `sort_items()` und Client-JS sortieren Serien chronologisch statt alphabetisch; `serie_path_to_numbers()` in `video/organizer.py` refactored auf Shared-Funktion
- YAML-Overrides (`hometools_overrides.yaml`) — Per-Ordner YAML-Dateien für Anzeigenamen, Staffel/Episode und Serientitel; `streaming/core/media_overrides.py` mit `load_overrides()`, `load_all_overrides()`, `apply_overrides()`; Integration in `build_video_index()` und `quick_folder_scan()`
- Action Hints — Scheduler und Task-Kandidaten enthalten strukturierte `action_hints` mit `action_id`, `cli_command` und `make_target` pro Kategorie (thumbnail → prewarm, cache → reindex, sync → check-nas, usw.)
- Noise-Unterdrückung — quellspezifische `_NOISE_RULES` filtern niedrigschwellige Tasks (z. B. Thumbnail-WARNINGs); CRITICALs passieren immer; `noise_suppressed_count` in Payload und Dashboard
- Root-Cause-Deduplizierung — `_ROOT_CAUSE_PATTERNS` gruppieren Issues über Sources und Kategorien hinweg nach Root-Cause (z. B. `library-unreachable`, `ffmpeg-missing`, `permission-denied`)
- CLI-Dashboard (`stream-dashboard`) — kombinierte Ansicht aus Issues, Task-Kandidaten und letztem Scheduler-Lauf als Box-Drawing-Tabelle; `--json` und `--fail-on-match` Flags; Makefile-Targets `dashboard` / `dashboard-json`
- Verwaiste `.tmp_*`-Testverzeichnisse aufgeräumt und in `.gitignore` eingetragen
- Issues/Tasks-Leiste aus der Browser-UI entfernt — Issues/Tasks werden nur noch serverseitig geloggt und über API-Endpunkte bereitgestellt
- Katalog-API-Endpunkte optimiert: Cache-First statt Library-Check-First → Server ist sofort nutzbar während Index-Rebuild

