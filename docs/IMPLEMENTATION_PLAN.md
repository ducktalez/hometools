# Implementation Plan

## Next tasks

- **Auto-Rename-Service für Serien** — Automatische Umbenennung von Serien-Dateien anhand von TMDB-Metadaten. Soll als `hometools rename-series <path>` CLI-Befehl funktionieren und die bestehende `series_rename_episodes()` in `video/organizer.py` als Backend nutzen. Vorher `hometools_overrides.yaml` aus dem Ordner lesen und als zusätzliche Quelle für korrekte Namen verwenden. Renames werden vorgeschlagen, nie auto-angewendet (Architektur-Regel #9).
  - Mögliche Erweiterung: `hometools generate-overrides <path>` — YAML-Vorlage mit TMDB-Daten generieren, die der User prüfen und dann als Override-Datei ablegen kann.

## Done

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

