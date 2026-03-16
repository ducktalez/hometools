"""Instruction system for hometools.

Generates `.github/INSTRUCTIONS.md` (compact router) and four sub-instruction
files in `.github/instructions/`.  The sub-files are regenerated from templates
embedded below so that structural changes (new modules, renamed files) are
picked up automatically.  Domain-specific logic rules live as inline code
comments; these files focus on architecture, module maps and conventions.
"""

from __future__ import annotations

import os
from pathlib import Path

GITHUB_DIR = Path(".github")
INSTRUCTIONS_DIR = GITHUB_DIR / "instructions"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_py_modules(root: Path, package: str) -> list[str]:
    """Return basenames of .py files in *root/src/hometools/<package>* (no __init__)."""
    pkg_dir = root / "src" / "hometools" / package.replace(".", os.sep)
    if not pkg_dir.is_dir():
        return []
    return sorted(
        f.stem
        for f in pkg_dir.iterdir()
        if f.suffix == ".py" and f.stem != "__init__" and not f.stem.startswith("__")
    )


def _list_test_files(root: Path, prefix: str) -> list[str]:
    """Return test file names matching *prefix* in the tests/ directory."""
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(f.name for f in tests_dir.iterdir() if f.name.startswith(prefix) and f.suffix == ".py")


# ---------------------------------------------------------------------------
# Main INSTRUCTIONS.md (hand-crafted, not auto-generated tree dump)
# ---------------------------------------------------------------------------

MAIN_TEMPLATE = """\
# INSTRUCTIONS — hometools

> Auto-generated. Run `hometools update-instructions` after structural changes.

## Scope

hometools = media library tools + local streaming prototypes (audio & video).
One shared core, two servers, common dark-theme UI.

## Architecture

| Domain | Package | Instruction file |
|--------|---------|-----------------|
| **Audio/Video file tools** | `audio/`, `video/` | [tools.instructions.md](instructions/tools.instructions.md) |
| **Streaming** | `streaming/` | [streaming.instructions.md](instructions/streaming.instructions.md) |

## Rules (global)

1. **Keep instructions lean.** Only include what an AI assistant needs to make correct changes. Avoid repeating information that is obvious from the code. Overly verbose instructions distort task focus.
2. **No hardcoded paths.** Use `config.py` helpers or CLI args.
3. **No secrets in source.** Use `.env` (gitignored).
4. **No side effects at import time.** Code behind CLI commands or explicit calls.
5. **Pure functions first.** Separate I/O from transformation; test the logic.
6. **Tests for every new pure function.** `tests/`, run `pytest`.
7. **Logging, not print.** `logging.getLogger(__name__)` in library code.
8. **Sync only on explicit command.** Never auto-pull from NAS.
9. **Update instructions after structural changes.** `hometools update-instructions`.
10. **Robust exception handling.** Every public function must handle errors gracefully and never crash the caller. Use try/except with logging — return sensible defaults (e.g. empty list, `None`, `False`) on failure.
11. **No blocking on long-running operations.** Expensive work (thumbnail extraction, network I/O, large file scans) must run in background threads or be deferred. Use dummy/placeholder values until results are ready so the UI stays responsive on first start.

## CLI

```
hometools serve-audio / serve-video [--library-dir] [--host] [--port]
hometools sync-audio  / sync-video  [--source] [--target] [--dry-run]
hometools serve-all [--host] [--audio-port] [--video-port]
hometools streaming-config
hometools setup-pycharm [--project-root]
hometools update-instructions [--repo-root]
```

## Config (env vars → `config.py`)

```
TMDB_API_KEY, HOMETOOLS_DELETE_DIR,
HOMETOOLS_AUDIO_LIBRARY_DIR, HOMETOOLS_AUDIO_NAS_DIR,
HOMETOOLS_VIDEO_LIBRARY_DIR, HOMETOOLS_VIDEO_NAS_DIR,
HOMETOOLS_STREAM_HOST, HOMETOOLS_AUDIO_PORT, HOMETOOLS_VIDEO_PORT
```
"""


# ---------------------------------------------------------------------------
# Sub-instruction templates
# ---------------------------------------------------------------------------

def _render_tools(root: Path) -> str:
    audio_modules = _list_py_modules(root, "audio")
    video_modules = _list_py_modules(root, "video")
    test_files = _list_test_files(root, "test_sanitize") + _list_test_files(root, "test_utils") + _list_test_files(root, "test_video")

    audio_rows = "\n".join(f"| `{m}.py` | |" for m in audio_modules)
    video_rows = "\n".join(f"| `{m}.py` | |" for m in video_modules)
    test_rows = "\n".join(f"| `{t}` |" for t in test_files)

    return f"""\
# Audio/Video File Tools

> Part of [INSTRUCTIONS.md](../INSTRUCTIONS.md). Covers `audio/` and `video/`.
> Auto-generated module list. Edit descriptions in `instructions.py` or as code comments.

## audio/ modules

| Module | Notes |
|--------|-------|
{audio_rows}

## video/ modules

| Module | Notes |
|--------|-------|
{video_rows}

## Conventions

- `sanitize.py` is **pure** — no I/O, no side effects. Every new transform needs a test.
- `metadata.py` — `audiofile_assume_artist_title(path)` splits `"Artist - Title"` from stems. Used by `streaming/audio/catalog.py`.
- `compare.py`, `merger.py` perform I/O — wrap behind CLI commands.
- `silence.py` requires **ffmpeg** on PATH.

## Tests

| File |
|------|
{test_rows}
"""


def _render_streaming(root: Path) -> str:
    core_modules = _list_py_modules(root, "streaming.core")
    audio_modules = _list_py_modules(root, "streaming.audio")
    video_modules = _list_py_modules(root, "streaming.video")
    test_files = (
        _list_test_files(root, "test_streaming_core")
        + _list_test_files(root, "test_streaming_audio")
        + _list_test_files(root, "test_streaming_video")
    )

    def _mod_rows(mods: list[str]) -> str:
        return ", ".join(f"`{m}.py`" for m in mods)

    test_rows = "\n".join(f"| `{t}` |" for t in test_files)

    return f"""\
# Streaming

> Part of [INSTRUCTIONS.md](../INSTRUCTIONS.md). Covers `streaming/`.

## Modules

| Sub-package | Modules |
|-------------|---------|
| `core/` | {_mod_rows(core_modules)} |
| `audio/` | {_mod_rows(audio_modules)} |
| `video/` | {_mod_rows(video_modules)} |

## Core design rules

- **`MediaItem` is frozen.** Never mutate; create new instances.
- **`artist` is overloaded.** Audio: actual artist. Video: folder name. Handle empty strings.
- **`render_media_page()`** is the single HTML skeleton — never duplicate.
- **API responses use `items` key** (not `tracks`).

## API pattern (same for audio & video)

```
GET /api/<type>/tracks?q=&artist=&sort= → {{ "items": [...] }}
GET /<type>/stream?path=<encoded>       → FileResponse
```

## Audio specifics

- Catalog: scan `AUDIO_SUFFIX` → `audiofile_assume_artist_title()` → `MediaItem(media_type="audio")`
- `AudioTrack = MediaItem` alias kept for back-compat.

## Video specifics

- Catalog: scan `VIDEO_SUFFIX` → `_title_from_filename()` → `_folder_as_artist()` → `MediaItem(media_type="video")`
- Default sort: **title**. No transcoding, no subtitles yet.

## Adding a new media type

1. `streaming/<type>/catalog.py` → `list[MediaItem]`
2. `streaming/<type>/sync.py` → delegate to `core.sync`
3. `streaming/<type>/server.py` → call `render_media_page()`
4. CLI in `cli.py`, config in `config.py`, tests in `tests/`

## Tests

| File |
|------|
{test_rows}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SUB_INSTRUCTIONS = {
    "tools.instructions.md": _render_tools,
    "streaming.instructions.md": _render_streaming,
}

# Old sub-instruction files that should be removed on update.
_OBSOLETE_FILES = [
    "streaming-core.instructions.md",
    "streaming-audio.instructions.md",
    "streaming-video.instructions.md",
]


def render_instructions(root: Path) -> str:
    """Render the main INSTRUCTIONS.md content."""
    return MAIN_TEMPLATE


def update_instructions_file(repo_root: Path, output_path: Path | None = None) -> Path:
    """Write the main INSTRUCTIONS.md and all sub-instruction files.

    Returns the path to the main file.
    """
    repo_root = repo_root.resolve()

    # Main file
    main_target = repo_root / (output_path or GITHUB_DIR / "INSTRUCTIONS.md")
    main_target.parent.mkdir(parents=True, exist_ok=True)
    main_target.write_text(render_instructions(repo_root), encoding="utf-8")

    # Sub-instruction files
    sub_dir = repo_root / INSTRUCTIONS_DIR
    sub_dir.mkdir(parents=True, exist_ok=True)
    for filename, renderer in SUB_INSTRUCTIONS.items():
        target = sub_dir / filename
        target.write_text(renderer(repo_root), encoding="utf-8")

    # Remove obsolete files from earlier layout
    for old_name in _OBSOLETE_FILES:
        old_path = sub_dir / old_name
        if old_path.exists():
            old_path.unlink()

    return main_target
