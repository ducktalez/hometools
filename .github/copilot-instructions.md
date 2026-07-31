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
13. **No Unicode/Emoji for UI controls.** All buttons use inline SVGs (defined as `SVG_*` constants in `server_utils.py` and `IC_*` JS variables). Never use Unicode chars like `▶ ◄ ► ⏸ ⊞ ↓` or HTML entities like `&#9733;`.
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
- **Open tasks → implementation plan**: Add new TODOs to `docs/IMPLEMENTATION_PLAN.md` instead of writing `# TODO` in source code.
- **Design discussions → implementation plan**: Open architectural questions and trade-off decisions go into the **Design Discussions** section of `docs/IMPLEMENTATION_PLAN.md`. Do not embed them inline in source code.
- **Raise concerns**: If an approach seems risky, fragile, or architecturally problematic, voice the concern explicitly before or alongside the implementation.

## Maintaining these docs

- **`docs/architecture.md` is the architecture reference, not a rule file.**
  It gives a fast conceptual overview (module map, core concepts, request
  lifecycle) *and* a compact "where does X live" location index (its §8).
  Short explanatory lines are fine when they convey a relationship or
  concept; avoid step-by-step bugfix narratives, root-cause deep-dives, or
  "lessons learned" — those belong in `git log`/PR descriptions.
- **After every feature or fix**, update the relevant section: concept text
  if it changes a relationship, the location index (§8) if it's a new
  file/endpoint. Never leave an implemented feature unlisted; never leave a
  removed one listed.
- **When a task in `docs/IMPLEMENTATION_PLAN.md` is done**, remove it (history only in `git log`).
- **Instruction files (`.github/instructions/*.instructions.md`) stay
  behavior rules scoped to a path glob** — never re-describe architecture
  there; link to the relevant `docs/architecture.md` section instead. 

