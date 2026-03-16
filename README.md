# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.

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
- **Browser-based audio player** — dark-theme web UI with search, artist filter, sort, and bottom player bar (⏮ ▶ ⏭ + progress)
- **Browser-based video player** — same UI as audio but with an inline `<video>` element, folder-based filtering
- **Track discovery controls** — search by title/artist/path, filter by artist or folder, sort by multiple fields
- **iPhone-friendly MVP** — no native iOS client, no Xcode project, just local web apps accessible via Safari

## Quick Start

```bash
# Clone and set up
git clone https://github.com/ducktalez/hometools.git
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets and paths
Copy-Item .env.example .env
# Edit .env with your TMDB_API_KEY and library paths

# Run tests
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
HOMETOOLS_STREAM_PORT=8000
```

### Audio

```powershell
hometools sync-audio --dry-run    # preview
hometools sync-audio              # copy files
hometools serve-audio             # start web UI → http://127.0.0.1:8000/
```

### Video

```powershell
hometools sync-video --dry-run    # preview
hometools sync-video              # copy files
hometools serve-video --port 8001 # start web UI → http://127.0.0.1:8001/
```

Both servers share the same dark-theme UI. Open them from any device on your home network (including Safari on iPhone).

## Project Structure

See [INSTRUCTIONS.md](.github/INSTRUCTIONS.md) for detailed module documentation and developer guidelines.

Regenerate the developer instructions after structural changes:

```powershell
hometools update-instructions
```

```
src/hometools/
├── audio/              # Sanitization, metadata, silence removal, merging
├── streaming/
│   ├── core/           # Shared MediaItem model, catalog, sync, UI helpers
│   ├── audio/          # Audio catalog, sync and FastAPI server
│   └── video/          # Video catalog, sync and FastAPI server
├── video/              # TMDB-based movie & series renaming
├── cli.py              # CLI commands for sync, streaming and maintenance
├── config.py           # Environment-based configuration
├── constants.py        # Shared constants
├── utils.py            # File/path utilities
└── print_tools.py      # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming)
- A mounted NAS/share path if you want to use the manual sync workflow

## License

See [LICENSE](LICENSE).

## TODOs

- [ ] Add more unit tests for edge cases (e.g. weird filename patterns, missing metadata)
- [ ] Implement a "Recently Added" section in the streaming UI
- [ ] Während des Scans der Files für den Audio- und Video Streaming Server: Hinweise wenn die Organisation mit dem Filesystem genügend Informationen gibt oder ob es Probleme 
