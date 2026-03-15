# INSTRUCTIONS – hometools Developer Guide

> **Auto-generated overview.** Update this file when you add modules or change the project structure.
> Last updated: 2026-03-15

## Project Structure

```
hometools/
├── src/hometools/              # Main package
│   ├── __init__.py             # Package metadata (__version__)
│   ├── config.py               # Environment-based configuration (TMDB key, paths)
│   ├── constants.py            # Shared constants (suffixes, mediainfo keys)
│   ├── logging_config.py       # Centralized logging setup
│   ├── print_tools.py          # ANSI colors & diff highlighting
│   ├── utils.py                # File/path utilities (rename, delete, discover)
│   ├── audio/                  # Audio processing tools
│   │   ├── sanitize.py         # Filename cleaning (stem_identifier, sanitize_track_to_path)
│   │   ├── metadata.py         # Tag reading/writing (mutagen, POPM ratings)
│   │   ├── compare.py          # Duplicate detection, batch sanitization
│   │   ├── merger.py           # MP3 merging (pydub)
│   │   └── silence.py          # Silence detection & removal (pydub + ffmpeg)
│   └── video/                  # Video organizing tools
│       └── organizer.py        # TMDB-based renaming for movies & series
├── tests/                      # pytest test suite
│   ├── test_sanitize.py        # Tests for audio.sanitize
│   ├── test_utils.py           # Tests for utils
│   ├── test_video_organizer.py # Tests for video.organizer helpers
│   └── test_print_tools.py     # Tests for print_tools
├── pyproject.toml              # Build config, dependencies, pytest settings
├── requirements.txt            # Pip-installable dependency list
├── .env.example                # Template for local secrets
├── .gitignore                  # Ignored files
└── README.md                   # User-facing documentation
```

## Setup

```bash
# 1. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Install in development mode
pip install -e ".[dev]"

# 3. Copy environment template and fill in your values
cp .env.example .env
# Edit .env: set TMDB_API_KEY, HOMETOOLS_DELETE_DIR

# 4. Run tests
pytest
```

## Module Responsibilities

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `config.py` | Load secrets from `.env` | `get_tmdb_api_key()`, `get_delete_dir()` |
| `constants.py` | Shared constants | `AUDIO_SUFFIX`, `VIDEO_SUFFIX`, `MEDIAINFO_DEL_KEYS` |
| `utils.py` | File operations | `get_files_in_folder()`, `rename_path()`, `fix_spaces()` |
| `audio/sanitize.py` | Pure string transforms | `stem_identifier()`, `sanitize_track_to_path()`, `split_stem()` |
| `audio/metadata.py` | Mutagen wrappers | `get_audio_metadata()`, `get_popm_rating()`, `set_popm_rating()` |
| `audio/compare.py` | Library management | `find_all_dupes()`, `delete_song_dupes()`, `sanitize_all_track_names_batch()` |
| `audio/merger.py` | MP3 concat | `mp3merge_list()`, `merge_mp3files_in_folder()` |
| `audio/silence.py` | Silence removal | `remove_silence_with_ffmpeg()`, `process_audio_folder()` |
| `video/organizer.py` | TMDB renaming | `get_tmdbid_from_path()`, `series_rename_episodes()` |

## Conventions

- **No hardcoded paths.** Use `config.py` or CLI arguments.
- **No secrets in source.** Use `.env` (gitignored).
- **No module-level side effects.** Code that "does something" goes behind `if __name__ == '__main__':` or in explicit entry-point functions.
- **Pure functions first.** Keep business logic testable by separating I/O from transformation.
- **Logging, not print.** Use `logging.getLogger(__name__)` in every module.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hometools --cov-report=term-missing

# Run a specific test file
pytest tests/test_sanitize.py -v
```

Tests focus on pure functions (string transformations, path parsing) that don't require external tools or audio files.

## Updating This File

When you add a new module:
1. Add it to the **Project Structure** tree above.
2. Add a row to the **Module Responsibilities** table.
3. Write tests in `tests/` for any pure functions.
4. Update the version in `src/hometools/__init__.py`.
