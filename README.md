# hometools

A collection of Python tools for managing personal media libraries — music file sanitization and video organizing with TMDB.

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

## Quick Start

```bash
# Clone and set up
git clone <repo-url>
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets
cp .env.example .env
# Edit .env with your TMDB_API_KEY

# Run tests
pytest
```

## Project Structure

See [INSTRUCTIONS.md](.github/INSTRUCTIONS.md) for detailed module documentation and developer guidelines.

```
src/hometools/
├── audio/          # Sanitization, metadata, silence removal, merging
├── video/          # TMDB-based movie & series renaming
├── config.py       # Environment-based configuration
├── constants.py    # Shared constants
├── utils.py        # File/path utilities
└── print_tools.py  # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming)

## License

See [LICENSE](LICENSE).
