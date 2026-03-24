# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.

## 📚 Dokumentation

- **[docs/plans/](docs/plans/)** — Roadmap, Feature-Pläne (Offline, Native App, Server Refactoring, PWA Shortcuts, ...)
- **[docs/ios/](docs/ios/)** — iOS/PWA-Entscheidungen, Gerätetests, Test-Runbooks
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Coding-Regeln für Copilot/Agents

## Plan/TODOs

- TV-Idee: Stream der Wer wird Millionär Show aus dem Quiz Repository. Hier kann eine zufällige Person online teilnehmen. 
- Check if audiobook from metadata is possible too 
- Option zur Erweiterung/Anreicherung mit YouTube Downloads. 

---

Vollständiger Implementierungsplan mit Backlog: **[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)**

**Aktuell:** Management-Server & Scheduler, Metadata-Editing
**Nächste:** Phase 3 — Native iOS Apps

- Für folgende Medien soll der letzte Abspielzeitpunkt gespeichert werden
  - Serien: Die letzte Folge + Zeitstempel
  - Hörbücher: Das letzte Kapitel + Zeitstempel. Hörbücher müssen markiert werden, befinden sich in passenden Ordnern befinden sich in passenden Ordnern (einstellbar) oder werden erkannt (Bei abspielzeit > 15min?)

## PyCharm Run-Konfigurationen

Im Repo unter `.idea/runConfigurations/` liegen fertige Konfigurationen:

| Konfiguration | Beschreibung |
|---|---|
| **Serve All** | Audio + Video + Channel Server starten |
| **Serve Audio** | Nur Audio-Server |
| **Serve Video** | Nur Video-Server |
| **Serve Channel** | Nur Channel (TV)-Server |
| **Run Tests** | Vollständige Test-Suite (`pytest -q`) |
| **Feature Parity Tests** | Audio↔Video Drift-Erkennung |
| **Ruff Check + Format** | Lint + Auto-Fix |
| **Dashboard** | CLI-Issues/TODOs Dashboard |
| **Streaming Config** | Aktuelle Konfiguration anzeigen |
## Features

### Music Library
- **Filename sanitization** — normalize `feat.`/`prod.`/`vs.` variants, remove emojis, website URLs, bitrate tags, and fix spacing
- **Duplicate detection** — find and remove duplicate audio files across folders
- **Silence trimming** — losslessly remove leading/trailing silence using ffmpeg
- **MP3 merging** — concatenate multi-part audio files
- **Metadata management** — read/write ID3 tags, POPM ratings, BPM analysis

### Video Library
- **TMDB integration** — automatically match movie & series files against [The Movie Database](https://www.themoviedb.org/)
- **Smart renaming** — rename files to `Title (Year) [tmdbid-ID].ext` format, compatible with Jellyfin/Plex
- **Series support** — parse `S01E03` patterns and fetch episode names

### Streaming (Audio & Video)
- **Shared streaming core** — common `MediaItem` model, catalog query/sort/filter, NAS sync and dark-theme UI used by both servers
- **Manual NAS sync** — copy new or changed media files from a mounted NAS folder into a local library on demand
- **Browser-based audio player** — dark-theme web UI with search, artist filter, sort, and bottom player bar
- **Browser-based video player** — same UI as audio but with an inline `<video>` element, folder-based filtering
- **PWA offline support** — download tracks/videos for offline playback via IndexedDB
- **Shadow cache** — thumbnails, failure tracking, and metadata caches in a mirror directory

## Quick Start

```bash
git clone https://github.com/ducktalez/hometools.git
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets and paths
Copy-Item .env.example .env
# Edit .env with your TMDB_API_KEY and library paths

pytest
```

## Streaming

Configure library paths, NAS sources and bind address in `.env`:

```dotenv
HOMETOOLS_AUDIO_LIBRARY_DIR=C:/Media/audio-library
HOMETOOLS_AUDIO_NAS_DIR=Z:/Music
HOMETOOLS_VIDEO_LIBRARY_DIR=C:/Media/video-library
HOMETOOLS_VIDEO_NAS_DIR=Z:/Video
HOMETOOLS_STREAM_HOST=0.0.0.0
HOMETOOLS_AUDIO_PORT=8010
HOMETOOLS_VIDEO_PORT=8011
```

```powershell
hometools streaming-config        # show current config overview
hometools serve-all               # start audio (:8010) + video (:8011)
hometools sync-audio --dry-run    # preview audio sync
hometools sync-video              # copy video files from NAS
```

### Wartung / Debugging

- `make reset-hard SERVER=audio` — löscht generierte Audio-Artefakte (Logs, Index-Snapshot, Thumbnails, Failure-Registry-Einträge)
- `make reset-all-hard` — harter Reset für beide Streaming-Server
- `make prewarm SERVER=video MODE=missing SCOPE=all` — baut Index-Snapshot + fehlende Thumbnails vor, ohne den Server zu starten
- `make video-reindex` — erzwingt kompletten Neuaufbau des Video-Index-Snapshots
- `make serve-all-safe` — startet beide Server im Safe-Mode
- `make issues` — zeigt aktuell offene Unregelmäßigkeiten aus Warnungen/Errors an
- `make issues-json` — gibt offene Unregelmäßigkeiten als JSON für Scheduler aus
- `make issues-errors` — liefert Exit-Code `1`, wenn offene Error/Critical-Issues existieren
- `make todos` — leitet priorisierte TODO-Kandidaten aus offenen Unregelmäßigkeiten ab
- `make scheduler-once` — führt den ersten Scheduler-Stub einmal aus, schreibt `todo_candidates.json` und berücksichtigt den TODO-Cooldown
- `make todo-state TODO_KEY=... TODO_ACTION=acknowledge|snooze|clear` — verwaltet manuelle TODO-Zustände

Für Automatisierung/Scheduler:

```powershell
hometools stream-issues --json
hometools stream-todos --json
hometools stream-scheduler --json
hometools stream-todo-state --todo-key todo::... --action acknowledge --reason "known issue"
hometools stream-todo-state --todo-key todo::... --action snooze --seconds 7200 --reason "later"
hometools stream-issues --only-errors --fail-on-match
```

Die Status-Endpunkte (`/api/audio/status`, `/api/video/status`) enthalten zusätzlich kompakte `issues`- und `todos`-Summaries, damit spätere Dashboards offene Unregelmäßigkeiten und aktive/snoozed/acknowledged Aufgaben direkt mit anzeigen können.

Die gemeinsame Streaming-UI nutzt diese `todos`-Summary inzwischen direkt und kann den obersten Task über denselben Shared-Core-Flow bestätigen, snoozen oder zurücksetzen. Beide Server verwenden dafür identische Endpunkte: `POST /api/audio/todos/state` bzw. `POST /api/video/todos/state`.

Safe-Mode (`HOMETOOLS_STREAM_SAFE_MODE=true` oder `--safe-mode`) deaktiviert absichtlich Snapshot-/Thumbnail-Warmups sowie Service-Worker-/Offline-Features. Gedacht als robuster Fallback, wenn NAS/UNC-Pfade oder Cache-Artefakte Probleme machen.

## Project Structure

```
src/hometools/
├── audio/              # Sanitization, metadata, silence removal, merging
├── streaming/
│   ├── core/           # Shared MediaItem model, catalog, sync, UI helpers
│   ├── audio/          # Audio catalog, sync and FastAPI server
│   └── video/          # Video catalog, sync and FastAPI server
├── video/              # TMDB-based movie & series renaming
├── cli.py              # CLI commands
├── config.py           # Environment-based configuration
├── constants.py        # Shared constants
├── utils.py            # File/path utilities
└── print_tools.py      # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming / video thumbnails)
- A mounted NAS/share path if you want to use the manual sync workflow

## License

See [LICENSE](LICENSE).