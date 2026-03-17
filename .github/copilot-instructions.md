# Copilot Instructions — hometools

Python CLI tool collection + two local FastAPI streaming servers (audio & video) with a shared core, dark-theme PWA UI, and NAS sync. Python 3.10+, setuptools, src-layout.

## Build & Validate

Always run commands from the repo root. The virtualenv is `hometools-env/`.

```powershell
# Install (editable + dev deps) — always do this after pulling or changing pyproject.toml
pip install -e ".[dev]"

# Lint (ruff) — must pass before commit
ruff check src/ tests/              # lint
ruff format --check src/ tests/     # format check

# Test — must pass before commit (~6 s, 280+ tests)
python -m pytest tests/ -q

# Pre-commit runs both ruff + pytest automatically
pre-commit run --all-files
```

**No GitHub Actions / CI pipeline.** Validation is pre-commit only (ruff lint+format, pytest, feature-parity tests).

## Project Layout

- **Entry point:** `src/hometools/cli.py` → `hometools = hometools.cli:main`
- **Config:** `config.py` — all paths/ports from `HOMETOOLS_*` env vars, never hardcode.
- **Streaming:** `streaming/core/` is shared, `streaming/audio/` and `streaming/video/` are thin wrappers with `catalog.py`, `server.py`, `sync.py` each.
- **UI:** `streaming/core/server_utils.py` (~2500 lines) generates all HTML/CSS/JS as Python strings — no separate frontend files.
- **All config** (deps, ruff, pytest) lives in `pyproject.toml`. Pre-commit in `.pre-commit-config.yaml`.

## Architecture Rules

1. **Audio ↔ Video share `streaming/core/`.** Before adding a feature to one server, check if it applies to the other. Never duplicate endpoints or UI logic — extend core instead.
2. **`MediaItem` is frozen** (dataclass, `frozen=True`). Never mutate; create new instances.
3. **API responses always use `"items"` key** — not `tracks` or `videos`.
4. **No side effects at import time.** All work behind CLI commands or explicit calls.
5. **Robust exception handling.** Every public function returns sensible defaults on failure (`None`, `False`, `[]`). Never crash the caller.
6. **No blocking.** Thumbnail generation, network I/O, file scans → background threads or deferred. Server startup must be instant.
7. **Shadow cache (`~/hometools-cache/`)** mirrors library structure. Never modify original media files. MTime-based invalidation. Failure registry (`thumbnail_failures.json`) prevents infinite retries.
8. **Caching coordination.** Server-side (shadow cache), client-side (Service Worker, IndexedDB), and PWA caching must stay in sync. API response shape changes require updating both `server_utils.py` (generated JS) and the Service Worker.
9. **File renames must be proposed, never auto-applied.** User confirms explicitly.
10. **Sync only on explicit CLI command.** Never auto-pull from NAS.
11. **Logging, not print.** `logging.getLogger(__name__)` in library code.
12. **ffmpeg/ffprobe** are optional runtime deps (thumbnail extraction, silence trimming). Always handle `FileNotFoundError` gracefully.

## Validation Checklist

After any change, run in this order:
1. `ruff check src/ tests/ --fix` — auto-fix lint issues
2. `ruff format src/ tests/` — format
3. `python -m pytest tests/ -q` — all tests must pass
4. If you changed streaming UI or API: also run `python -m pytest tests/test_feature_parity.py -v` — catches audio↔video drift


