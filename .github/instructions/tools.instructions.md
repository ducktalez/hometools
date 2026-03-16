# Audio/Video File Tools

> Part of [INSTRUCTIONS.md](../INSTRUCTIONS.md). Covers `audio/` and `video/`.
> Auto-generated module list. Edit descriptions in `instructions.py` or as code comments.

## audio/ modules

| Module | Notes |
|--------|-------|
| `compare.py` | |
| `merger.py` | |
| `metadata.py` | |
| `sanitize.py` | |
| `silence.py` | |

## video/ modules

| Module | Notes |
|--------|-------|
| `organizer.py` | |

## Conventions

- `sanitize.py` is **pure** — no I/O, no side effects. Every new transform needs a test.
- `metadata.py` — `audiofile_assume_artist_title(path)` splits `"Artist - Title"` from stems. Used by `streaming/audio/catalog.py`.
- `compare.py`, `merger.py` perform I/O — wrap behind CLI commands.
- `silence.py` requires **ffmpeg** on PATH.

## Tests

| File |
|------|
| `test_sanitize.py` |
| `test_utils.py` |
| `test_video_organizer.py` |
