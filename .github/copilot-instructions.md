# Copilot Instructions — hometools

Python CLI tool collection + two local FastAPI streaming servers (audio & video) with a shared core, dark-theme PWA UI, and NAS sync. Python 3.10+, setuptools, src-layout.

## Build & Validate

Always run commands from the repo root. The virtualenv is `hometools-env/`.

**No GitHub Actions / CI pipeline.** Validation is pre-commit only (ruff lint+format, pytest, feature-parity tests).

## Project Layout

- **Entry point:** `src/hometools/cli.py` → `hometools = hometools.cli:main`
- **Config:** `config.py` — all paths/ports from `HOMETOOLS_*` env vars, never hardcode.
- **Streaming:** `streaming/core/` is shared, `streaming/audio/` and `streaming/video/` are thin wrappers with `catalog.py`, `server.py`, `sync.py` each.
- **UI:** `streaming/core/server_utils/` package generates all HTML/CSS/JS as Python strings — no separate frontend files. Split into `_svg.py` (icon/flag constants), `_css.py` (`render_base_css`), `_player_js.py` (`render_player_js`), `_html.py` (`render_media_page`), `_pwa.py` (manifest/SW/icons), `_audit.py` (`render_audit_panel_html`), `_library.py` (status/error pages), `_paths.py` (path validation). `__init__.py` re-exports everything for backward compatibility.
- **Native clients:** `clients/` holds native apps (Android TV active in `clients/androidtv/`; `android/`, `ios/` reserved). They are **thin API clients** of the Python backend — never re-implement business logic. Admin tools (rating/tag/move/delete/playlists) stay web-only; clients use only the read/playback subset. Contract = `clients/shared/openapi/*.json`, regenerated via `hometools export-openapi --server {video,audio}`. See `.github/instructions/clients*.instructions.md`.
- **All config** (deps, ruff, pytest) lives in `pyproject.toml`. Pre-commit in `.pre-commit-config.yaml`.

## Architecture Rules

1. **Audio ↔ Video share `streaming/core/`.** Before adding a feature to one server, check if it applies to the other. Never duplicate endpoints or UI logic — extend core instead.
2. **`MediaItem` is frozen** (dataclass, `frozen=True`). Never mutate; create new instances.
3. **API responses always use `"items"` key** — not `tracks` or `videos`.
4. **No side effects at import time.** All work behind CLI commands or explicit calls.
5. **Robust exception handling.** Every public function returns sensible defaults on failure (`None`, `False`, `[]`). Never crash the caller.
6. **No blocking.** Thumbnail generation, network I/O, file scans → background threads or deferred. Server startup must be instant.
7. **Shadow cache (`.hometools-cache/`)** in the repo root mirrors library structure. Override with `HOMETOOLS_CACHE_DIR`. Never modify original media files. MTime-based invalidation. Failure registry (`thumbnail_failures.json`) prevents infinite retries.
8. **Caching coordination.** Server-side (shadow cache), client-side (Service Worker, IndexedDB), and PWA caching must stay in sync. API response shape changes require updating both `server_utils.py` (generated JS) and the Service Worker.
9. **File renames must be proposed, never auto-applied.** User confirms explicitly.
10. **Sync only on explicit CLI command.** Never auto-pull from NAS.
11. **Logging, not print.** `logging.getLogger(__name__)` in library code.
12. **ffmpeg/ffprobe** are optional runtime deps (thumbnail extraction, silence trimming). Always handle `FileNotFoundError` gracefully.
13. **No Unicode/Emoji for UI controls.** All buttons use inline SVGs (defined as `SVG_*` constants in `server_utils.py` and `IC_*` JS variables). Never use Unicode chars like `▶ ◄ ► ⏸ ⊞ ↓` or HTML entities like `&#9733;` — iOS renders them as coloured emojis. Current SVG constants: `SVG_PLAY`, `SVG_PAUSE`, `SVG_PREV`, `SVG_NEXT`, `SVG_PIP`, `SVG_BACK`, `SVG_MENU`, `SVG_DOWNLOAD`, `SVG_CHECK`, `SVG_FOLDER_PLAY`, `SVG_PIN`, `SVG_STAR`, `SVG_STAR_EMPTY`, `SVG_SHUFFLE`, `SVG_REPEAT`, `SVG_HISTORY`, `SVG_BOARD`, `SVG_EDIT`, `SVG_LYRICS`, `SVG_PLAYLIST`, `SVG_SMART_PLAYLIST`, `SVG_QUEUE`, `SVG_REFRESH`, `SVG_DUPLICATE`, `SVG_MOVE`, `SVG_TRASH`, `SVG_CAST`, `SVG_FLAG_DE`, `SVG_FLAG_EN`, `SVG_FLAG_FR`, `SVG_FLAG_ES`, `SVG_FLAG_IT`, `SVG_FLAG_JA`, `SVG_FLAG_KO`, `SVG_FLAG_ZH`, `SVG_FLAG_PT`, `SVG_FLAG_RU`.
14. **Event-listener lifecycle.** Any feature that registers `document`-level or long-lived DOM event listeners (e.g. Drag-and-Drop) **must** provide a cleanup/destroy function that removes all listeners via `removeEventListener` (requires named handler references, not anonymous functions). The cleanup must be called **before re-initializing** the feature and **when leaving the view** (e.g. `showFolderView`, `showPlaylist`). Pattern: `var _cleanup = null; function init() { destroy(); ... _cleanup = function() { removeEventListener(...); }; } function destroy() { if (_cleanup) { _cleanup(); _cleanup = null; } }`. Current instances: `initPlaylistDragDrop` / `destroyPlaylistDragDrop` / `_dndCleanup`, `initQueueDragDrop` / `destroyQueueDragDrop` / `_queueDndCleanup`.

## Validation Checklist

After any change, run in this order:
1. `ruff check src/ tests/ --fix` — auto-fix lint issues
2. `ruff format src/ tests/` — format
3. `python -m pytest tests/ -q` — all tests must pass
4. If you changed streaming UI or API: also run `python -m pytest tests/test_feature_parity.py -v` — catches audio↔video drift

## Working Behaviour
- **Proactive code review**: When working on a task, report any **bugs**, **code smells**, or **questionable patterns** discovered along the way — even if unrelated to the current task. Include a brief suggestion for each finding.
- **Don't silently fix ambiguous findings**: Only fix a discovered issue directly if it is **unambiguously wrong** (missing import, typo, off-by-one). If the intent is unclear, or a comment/print suggests ongoing work — **ask first** or add a `# TODO` instead of removing/rewriting it. Debug prints or markers like `# discuss` are investigation aids, not dead code.
- **Open tasks → implementation plan**: Add new TODOs to `docs/implementation-plan.md` instead of writing `# TODO` in source code.
- **Design discussions → implementation plan**: Open architectural questions and trade-off decisions go into the **Design Discussions** section of `docs/implementation-plan.md`. Do not embed them inline in source code.
- **Raise concerns**: If an approach seems risky, fragile, or architecturally problematic, voice the concern explicitly before or alongside the implementation.
## Maintaining these docs

**MANDATORY: Every code change must be documented. No exceptions.**

- **When implementing a feature or fix**, immediately update `docs/architecture.md` with a new section describing the design, modules involved, and design rules.
- **When moving a task to "Done" in `IMPLEMENTATION_PLAN.md`**, always add or update the corresponding section in `docs/architecture.md`. No Done-item without architecture entry.
- **When you identify fundamental changes** (new modules, new fields on MediaItem, new endpoints, changed CSS conventions), update `docs/architecture.md`.
- **When you identify an open task**, add it to `docs/IMPLEMENTATION_PLAN.md`.
- **When adding new SVG constants** (`SVG_*` / `IC_*`), update the list in Architecture Rule 13 in this file AND in the SVG-Icons section of `docs/architecture.md`.
- **After every session**, verify that `docs/IMPLEMENTATION_PLAN.md` Done-section and `docs/architecture.md` are in sync with the actual code.

