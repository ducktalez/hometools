---
applyTo: "src/hometools/audio/**,src/hometools/video/**"
---
# Audio/Video File Tools

## Key rules

- **`sanitize.py` is pure.** No I/O, no side effects. Every new transform needs a test.
- **`metadata.py` bridges streaming and file tools.** `audiofile_assume_artist_title(path)` is used by `streaming/audio/catalog.py` — changes here affect catalog building.
- **I/O-heavy tools** (`compare.py`, `merger.py`, `silence.py`) must stay behind CLI commands — never call them at import time or during server startup.
- **TMDB calls** (`organizer.py`) require a network — always handle timeouts and missing API keys gracefully.
- **File renames must be proposed, never auto-applied.** Generate a rename list that the user explicitly confirms. Never modify the filesystem without explicit user action.
- **ffmpeg dependency:** `silence.py` and video thumbnail extraction require ffmpeg on PATH. Always check for `FileNotFoundError` and return a sensible fallback.
