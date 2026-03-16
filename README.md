# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and a minimal local audio streaming prototype.

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

### Streaming Prototype
- **Manual NAS sync** — copy new or changed audio files from a mounted NAS folder into a local library on demand
- **Browser-based audio player** — open a local web UI and stream copied tracks to devices on your home network
- **Track discovery controls** — search by artist/title/path, filter by artist, and choose sorting in the web UI
- **iPhone-friendly MVP** — no native iOS client, no Xcode project, just a local web app in Safari
- **Video-ready structure** — a matching video streaming area already exists as a placeholder for later expansion

## Quick Start

```bash
# Clone and set up
git clone <repo-url>
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets
Copy-Item .env.example .env
# Edit .env with your TMDB_API_KEY

# Run tests
pytest
```

## Audio Streaming MVP

Configure the local library, NAS source and bind address in `.env`:

```dotenv
HOMETOOLS_AUDIO_LIBRARY_DIR=C:/Media/audio-library
HOMETOOLS_AUDIO_NAS_DIR=Z:/Music
HOMETOOLS_STREAM_HOST=0.0.0.0
HOMETOOLS_STREAM_PORT=8000
```

Sync audio manually from the mounted NAS share into the local library:

```powershell
hometools sync-audio --dry-run
hometools sync-audio
```

Start the local audio streaming UI:

```powershell
hometools serve-audio
```

Then open:

```text
http://127.0.0.1:8000/
```

If the server runs on your home network and your firewall allows access, you can also open it from Safari on your iPhone using your PC or server IP.

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
│   ├── audio/          # Audio catalog, sync and FastAPI server
│   └── video/          # Placeholder for future video streaming work
├── video/              # TMDB-based movie & series renaming
├── cli.py              # CLI commands for sync and local streaming
├── config.py           # Environment-based configuration
├── constants.py        # Shared constants
├── utils.py            # File/path utilities
└── print_tools.py      # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming)
- A mounted NAS/share path if you want to use the manual audio sync workflow

## License

See [LICENSE](LICENSE).
