# Implementation Plan

## Current Sprint — Backlog High Items

- **Management-Server & Scheduler** — Status-Dashboard, Auto-NAS-Sync, zyklische Aufgaben
- **Metadata-Editing vom Handy** — Änderungen in Review-Queue, Schreiben erst nach Akzeptanz

## Backlog — High

- **Phase 3: Native iOS Apps** — Hybrid WebView Wrapper für Video + Audio → [plans/native_app_plan.md](plans/native_app_plan.md)

## Backlog — Medium

### Streaming UI (Audio + Video)
- Shuffle-Modus (+ gewichteter Shuffle nach Bewertung bei Long Touch) ← **in Arbeit: nur Audio, Core-implementiert** ✅ erledigt
- Songwertung (1–5 Sterne) in UI + ID3-POPM-Tags speichern ✅ erledigt
- Wiedergabelisten erstellen und verwalten
- Crossfade für nahtlose Song-Übergänge
- Swipe-Gesten für mobile Navigation
- Filteroptionen für die Suche
- Offline-Downloads-Liste (alle heruntergeladenen Dateien anzeigen)
- Songtexte anzeigen (aus ID3-Tags)
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

## Backlog — Low / Experimental

- **DJ-Extension** — Mixing, Stems (Gesang/Instrumental/Beat), BPM-Analyse, Auto-DJ-Modus
- **„Fernsehsender"** — automatische Wiedergabe nach Plan, mit Werbe-Einspielern
- **„MTV"-Modus** — Musikvideos + visuelle Begleitung zu Musik
- **„Sleep Mode"** — nur Audio aus Serien, kein Bildschirm
- **Photo-Management-Server**
- **HTTP-Obscurification** — Port-Knock statt HTTPS für Privat-Server
- **Pro-Nutzer Ordnerstruktur** (N8N-Integration)
- **Lennyface-Board**

## Done

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
