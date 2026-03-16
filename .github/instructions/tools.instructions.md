# Audio/Video File Tools

> Part of [INSTRUCTIONS.md](../INSTRUCTIONS.md). Covers `audio/` and `video/`.

## audio/ modules

| Module | Notes |
|--------|-------|
| `compare.py` | Duplicate detection, batch sanitization. I/O-heavy — behind CLI. |
| `merger.py` | MP3 merging via pydub. I/O-heavy — behind CLI. |
| `metadata.py` | `audiofile_assume_artist_title(path)` splits `"Artist - Title"` from stems. Used by `streaming/audio/catalog.py`. |
| `sanitize.py` | **Pure** — no I/O, no side effects. Every new transform needs a test. |
| `silence.py` | Silence detection/trimming. Requires **ffmpeg** on PATH. |

## video/ modules

| Module | Notes |
|--------|-------|
| `organizer.py` | TMDB-based renaming for films and series. |

## Tests

| File |
|------|
| `test_sanitize.py` |
| `test_utils.py` |
| `test_video_organizer.py` |
