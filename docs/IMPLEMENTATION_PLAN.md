# Implementation Plan

## Current Sprint — Backlog High Items

- **Management-Server & Scheduler** — Status-Dashboard, Auto-NAS-Sync, zyklische Aufgaben

## Backlog — High

- **Phase 3: Native iOS Apps** — Hybrid WebView Wrapper für Video + Audio → [plans/native_app_plan.md](plans/native_app_plan.md)

## Backlog — Medium

### Streaming UI (Audio + Video)
- Shuffle-Modus (+ gewichteter Shuffle nach Bewertung bei Long Touch) ← **in Arbeit: nur Audio, Core-implementiert** ✅ erledigt
- Songwertung (1–5 Sterne) in UI + ID3-POPM-Tags speichern ✅ erledigt
- Wiedergabelisten erstellen und verwalten
- Crossfade für nahtlose Song-Übergänge
- Swipe-Gesten für mobile Navigation
- Offline-Downloads-Liste (alle heruntergeladenen Dateien anzeigen)
- „Ähnliche Titel" vorschlagen (Artist/Genre/Album bzw. TMDB)
- Tags bei Musik nutzen

### Video-spezifisch
- Sprache/Untertitel/Auflösung taggen und auswählbar machen
- Multi-Language-Linking („Malcolm Mittendrin" ↔ „Malcolm in the Middle")
- Englische Serien: Metadaten + Titel in Englisch laden
- „Intro überspringen" (TMDB-Daten oder manuelle Markierung)
- Scan-Hinweise: Filesystem-Organisation ausreichend?
- Untertitelfiles + TMDB-Integration bei Umbenennungen

### Infrastruktur
- Tools-Code restrukturieren + umfassende Tests (Edge Cases, Dummy-Dateien)
- Optionales HTTPS
- Geräteübergreifende Fortschritts-Synchronisation
- iOS Background Video Playback → [plans/background_video_playback.md](plans/background_video_playback.md)
- **Audit-Log aus Cache-Verzeichnis herauslösen** — `audit/audit.jsonl` liegt aktuell unter `HOMETOOLS_CACHE_DIR` (`.hometools-cache/audit/`). Das ist irreführend, da der Cache-Ordner wegwerfbar ist (z.B. `make clean`). Langfristig eigene Env-Var `HOMETOOLS_AUDIT_DIR` einführen und das Log dauerhaft vom regenerierbaren Cache trennen. Bis dahin: `make clean` schont `audit/` explizit.

## Backlog — Low / Experimental

- **DJ-Extension** — Mixing, Stems (Gesang/Instrumental/Beat), BPM-Analyse, Auto-DJ-Modus
- **„MTV"-Modus** — Musikvideos + visuelle Begleitung zu Musik
- **„Sleep Mode"** — nur Audio aus Serien, kein Bildschirm
- **Photo-Management-Server**
- **HTTP-Obscurification** — Port-Knock statt HTTPS für Privat-Server
- **Pro-Nutzer Ordnerstruktur** (N8N-Integration)
- **Lennyface-Board**

## Done

- **Channel-Server: Playlist-basiert (Rewrite)** (2026-03-31) — HLS-Livestream-Architektur (`server.py` + `mixer.py`) durch einfachen **Playlist-basierten Server** (`server_playlist.py`) ersetzt. Der neue Server baut eine Tagesplaylist aus dem YAML-Schedule (`fill_series` + geplante Slots → interleaved `MediaItem`-Liste) und nutzt den bestehenden Video-Player mit Auto-Next (`player.addEventListener('ended', nextIndex())`). Kein ffmpeg-Hintergrundprozess, keine HLS-Segmente, keine Race Conditions. Standard-UI via `render_media_page()`, gleiche Endpoints wie Audio/Video (`/api/channel/items`, `/api/channel/progress`, etc.). Alter HLS-Code bleibt als `server.py` erhalten, wird nicht mehr als Default verwendet. 13 neue Tests (`test_channel_playlist.py`).
- **Channel-Mixer Rewrite: Concat Demuxer + Pre-Transcode** (2026-03-25) — Fundamentale Architekturänderung: Alte Multi-Prozess-Architektur (ein ffmpeg pro Video) durch **Concat Demuxer** ersetzt. Neues Modul `streaming/channel/transcode.py` mit `prepare_video()`, `prepare_testcard()`, `build_concat_file()`, `cleanup_prepared()`. Videos werden in `.hometools-cache/channel/tmp/` vorab auf H.264/AAC 1280×720 25fps konvertiert, dann über **einen** ffmpeg-Prozess (`-f concat -c copy → -f hls`) lückenlos gestreamt. Temporäre Dateien werden nach Wiedergabe gelöscht. Entfernte Workarounds: `_sync_segment_counter_from_disk()`, `_cleanup_stale_manifest()`, globale `_segment_counter`-Variable. Config: `get_channel_tmp_dir()`. 88 Tests (davon 15 neue für Transcode/Concat). **Veraltet — abgelöst durch Playlist-Server (2026-03-31).**
- **Fernsehsender (Channel-Server)** — Dritter Server auf Port 8012 (`serve-channel`), kontinuierlicher HLS-Livestream via ffmpeg; YAML-Programmplan (`channel_schedule.yaml`) mit Tages-/Wochentag-Slots; pünktlicher Serienstart mit automatischer Seek-Berechnung bei Late-Join; Filler-Content (Clips/Musik) für Lücken; Episode-State-Tracking (sequential/random); `ChannelMixer` Background-Thread; Browser-UI mit hls.js + EPG + „Jetzt läuft"; `HOMETOOLS_CHANNEL_PORT`, `HOMETOOLS_CHANNEL_SCHEDULE`, `HOMETOOLS_CHANNEL_FILLER_DIR`, `HOMETOOLS_CHANNEL_ENCODER` Env-Vars; 36 Tests
- **Schnellfilter-Chips (Track-Liste)** — Pill-Buttons „Bewertung" (zyklisch 1–5★ Minimum) und „Favoriten" (Toggle) in der Filter-Bar; AND-Logik mit Textsuche; `localStorage`-Persistenz; `updateFilterChips()` in `server_utils.py`; CSS-Klasse `.filter-chip` + `.active`.
- **Songtexte anzeigen (Lyrics-Panel)** — Bottom-Drawer `.lyrics-panel` im Audio-Player; lazy Fetch via `GET /api/audio/lyrics?path=`; `_lyricsCache` verhindert Mehrfachfetches; auto-Update beim Track-Wechsel wenn Panel offen; `SVG_LYRICS` / `IC_LYRICS`; `enable_lyrics=True` nur im Audio-Server; `LYRICS_ENABLED` / `LYRICS_API_PATH` JS-Variablen.
- **`make clean`** — löscht alle generierten Cache-Dateien (Thumbnails, Indexes, Progress, Issues, Logs, Shortcuts, `video_metadata_cache.json`, `thumbnail_failures.json`) unter `.hometools-cache/` und schont dabei `audit/` explizit. Python-basiert, Windows-kompatibel. Hinweis im `help`-Target und `get_cache_dir()`-Docstring.
- **Thumbnail-Größen je Ansichtsmodus** — Kleine Thumbs nur in Listenansicht (`viewMode === 'list'`); Grid- und Filenames-Modus verwenden große Thumbnails (`thumbnail_lg_url`). Player-Bar zeigt immer große Version.
- **Zuletzt gespielt — server-spezifisch** — Audio: `enable_recent=False` (kein UI-Abschnitt; Hörbücher steigen via Progress-API ein). Video: max. 3 Folgen, 14 Tage, 1 je Serie — konfigurierbar via `HOMETOOLS_RECENT_VIDEO_LIMIT`, `HOMETOOLS_RECENT_MAX_AGE_DAYS`, `HOMETOOLS_RECENT_MAX_PER_SERIES` (in `.env.example` dokumentiert).
- **Ansichtsumschalter (3 Modi)** — list → grid → filenames zyklisch; `filenames`-Modus ersetzt separate „Original"-Checkbox; in `architecture.md` dokumentiert.
- **Metadaten-Bearbeitung (Audio)** — `POST /api/audio/metadata/edit` Endpoint, `write_track_tags()` (MP3/M4A/FLAC/OGG), `enable_metadata_edit=True` in Audio-Server, Bleistift-Button (`.track-edit-btn`, `IC_EDIT`) pro Track in Liste, Edit-Modal (`.edit-modal-backdrop`, Titel/Interpret/Album), lokaler JS-State-Update ohne Server-Round-Trip, Audit-Integration via `log_tag_write()`, 7 neue Tests
- **Zuletzt gespielt / Continue Watching** — `get_recent_progress()` in `progress.py`, `GET /api/<media>/recent` (Audio + Video), „Zuletzt gespielt"-Scroll-Sektion auf Startseite mit Fortschrittsbalken + direkter Seek-Wiederaufnahme, `RECENT_API_PATH` JS-Variable
- **Hörbuch-Ordner-Erkennung** — `get_audiobook_dirs()` + `is_audiobook_folder()` in `config.py`, `HOMETOOLS_AUDIOBOOK_DIRS` Env-Var, `AUDIOBOOK_DIRS` JS-Array, blaue Einfärbung (`.audiobook-folder`) im Ordner-Grid
- Audit-Log & Change-Log — `streaming/core/audit_log.py`, JSONL append-only, `GET/POST /api/<media>/audit`, `POST /api/<media>/audit/undo`, Control Panel `/audit`, Undo-Toast in App mit `entry_id`, Bewertungsverlauf pro Datei über `?path_filter=`
- Songwertung-Schreiben (Audio-only) — `POST /api/audio/rating` Endpoint, `enable_rating_write=True` in Audio-Server, 5 klickbare Sterne im Player (`SVG_STAR_EMPTY`, `IC_STAR_FILLED`/`IC_STAR_EMPTY`), Hover-Preview, POPM-Write via `set_popm_rating()`, Index-Invalidierung, Weighted-Shuffle-Queue-Rebuild nach Rating-Änderung
- Shuffle-Modus (Audio-Server) — `enable_shuffle=True` in `render_media_page()`, Shuffle-Button im Player-Bar (Classic + Waveform), Fisher-Yates + gewichteter Shuffle nach POPM-Rating, Long-Press für Weighted-Modus, localStorage-Persistenz, Offline-kompatibel (client-seitige Queue), implementiert in Core (`server_utils.py`)
- Header-Navigation: Emoji-Symbol als Startseiten-Button (`logo-home-btn`), Titel als reiner Text (`logo-title`) — kein Link mehr
- Favoriten-Badge SVG (Fix 1: `IC_STAR`/`SVG_STAR` statt `&#9733;` Unicode-Stern; `.fav-badge` CSS auf SVG umgestellt)
- Verwaiste CSS-Zeilen entfernt (Fix 2: orphaned `padding`/`}` nach `.track-dl-btn svg`)
- Rating-System POPM (`get_popm_rating()`, ID3-POPM → 0–5 Sterne, `MediaItem.rating`, `.rating-bar` UI)
- Server-Logging in Datei (`get_log_dir()`, `RotatingFileHandler`, `<cache_dir>/logs/hometools.log`)
- Folder-Favorites (Namens-Konvention `#`-Prefix, SVG-Badge, alphabetisch zuerst sortiert)
- Phase 2: PWA Shortcuts — Deep Linking (`?id=`), Shortcuts API + JSON-Storage, Manifest-Generator, Pin-Button pro Item, Share-Sheet/Clipboard
- Phase 1: Offline-Download Feature (PWA) — Service Worker, IndexedDB, Offline-Playback
- FastStart-Erkennung für MP4-Dateien (`has_faststart()`, Auto-Remux)
- SVG-Icons statt Unicode/Emoji (alle Buttons, iOS-kompatibel)
- Shadow-Cache ins Repository (`.hometools-cache/`, `HOMETOOLS_CACHE_DIR`)
- Große Thumbnails 480 px (`/thumb?size=lg`, Background-Worker)
- Wiedergabe-Fortschritt speichern (`progress.py`, Resume-Toast)
- Recently Added Sortierung (`mtime`-Feld, „Neueste ⇅")
- On-the-fly Remux/Transcode (`remux.py`, FLV/AVI/MKV → frag-MP4)
- Serien-Episoden-Ordnung (`parse_season_episode()`, S##E## / ##x##)
- YAML-Overrides (`hometools_overrides.yaml`, Anzeigenamen/Staffel/Episode)
- Action Hints (strukturierte CLI-Empfehlungen pro Task-Kategorie)
- Noise-Unterdrückung (quellspezifische Schwellen, `_NOISE_RULES`)
- Root-Cause-Deduplizierung (`_ROOT_CAUSE_PATTERNS`)
- CLI-Dashboard (`stream-dashboard`, Box-Drawing, `--json`)
- Issues/Tasks aus Browser-UI entfernt (nur API + CLI)
- Cache-First API (Server sofort nutzbar während Index-Rebuild)
- Verwaiste `.tmp_*`-Testverzeichnisse aufgeräumt
