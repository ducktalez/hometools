# Copilot Instructions — hometools

Python CLI tool collection + two local FastAPI streaming servers (audio & video), shared core, dark-theme PWA UI, NAS sync. Python 3.10+, setuptools, src-layout.

## Communication Style

**Caveman mode always active** (see skill `caveman`, level `full`). Applies to chat replies AND code comments / commit messages / docs written by the agent. Terse fragments, no filler, no long prose explanations. Example of what NOT to do: multi-sentence comment explaining rationale in full grammar — write the short version instead. Code itself, error messages, and identifiers stay exact/normal.

## Build & Validate

Run from repo root. Venv: `hometools-env/`. No CI — validation is pre-commit (ruff lint+format, pytest, feature-parity tests).

## Project Layout

- **Entry point:** `src/hometools/cli.py` → `hometools = hometools.cli:main`
- **Config:** `config.py` — paths/ports from `HOMETOOLS_*` env vars, never hardcode.
- **Streaming:** `streaming/core/` shared, `streaming/audio/` + `streaming/video/` thin wrappers (`catalog.py`, `server.py`, `sync.py` each).
- **UI:** `streaming/core/server_utils/` generates all HTML/CSS/JS as Python strings — no separate frontend files. `_svg.py` (icons/flags), `_css.py` (`render_base_css`), `_player_js.py` (`render_player_js`), `_html.py` (`render_media_page`), `_pwa.py` (manifest/SW/icons), `_audit.py` (`render_audit_panel_html`), `_library.py` (status/error pages), `_paths.py` (path validation). `__init__.py` re-exports all.
- **Native clients:** `clients/` (Android TV active, `android/`/`ios/` reserved) — thin API clients, never re-implement backend logic. Admin tools (rating/tag/move/delete/playlists) web-only; clients get read/playback subset only. Contract = `clients/shared/openapi/*.json`, regen via `hometools export-openapi --server {video,audio}`. See `.github/instructions/clients*.instructions.md`.

## Architecture Rules

1. **Audio ↔ Video share `streaming/core/`.** New feature → check if applies to both. Never duplicate endpoints/UI logic — extend core.
2. **`MediaItem` frozen** (dataclass). Never mutate; new instances only.
3. **API responses use `"items"` key** — not `tracks`/`videos`.
4. **No side effects at import time.** Work behind CLI commands / explicit calls only.
5. **Robust exceptions.** Public functions return sensible defaults on failure (`None`/`False`/`[]`). Never crash caller.
6. **No blocking.** Thumbnails, network I/O, file scans → background threads. Server startup instant.
7. **Shadow cache** (`.hometools-cache/`, override `HOMETOOLS_CACHE_DIR`) mirrors library. Never touch original media files. MTime-based invalidation. Failure registry (`thumbnail_failures.json`) stops infinite retries.
8. **Caching coordination.** Shadow cache, Service Worker/IndexedDB, PWA stay in sync. API shape change → update `server_utils.py` JS + Service Worker together.
9. **Renames proposed, never auto-applied.** User confirms.
10. **Sync only on explicit CLI command.** No auto-pull from NAS.
11. **Logging, not print.** `logging.getLogger(__name__)`.
12. **ffmpeg/ffprobe optional.** Always handle `FileNotFoundError`.
13. **No Unicode/Emoji for UI controls.** Inline SVGs only (`SVG_*` in `server_utils.py`, `IC_*` JS vars). No chars like `▶ ◄ ► ⏸ ⊞ ↓`, no entities like `&#9733;`.
14. **Event-listener lifecycle.** `document`-level/long-lived listeners (e.g. Drag-and-Drop) need cleanup/destroy via `removeEventListener` (named handlers, not anonymous). Call cleanup before re-init and on view leave (`showFolderView`, `showPlaylist`). Pattern: `var _cleanup = null; function init() { destroy(); ... _cleanup = function() { removeEventListener(...); }; } function destroy() { if (_cleanup) { _cleanup(); _cleanup = null; } }`. Instances: `initPlaylistDragDrop`/`destroyPlaylistDragDrop`/`_dndCleanup`, `initQueueDragDrop`/`destroyQueueDragDrop`/`_queueDndCleanup`.

## Working Behaviour

- **Proactive review:** report bugs/code smells/questionable patterns found along the way, even unrelated. Brief suggestion each.
- **Don't silently fix ambiguous findings.** Only fix if unambiguously wrong (missing import, typo, off-by-one). Unclear intent / ongoing-work markers (`# discuss`, debug prints) → ask first or add `# TODO`, don't remove.
- **Open tasks → `docs/IMPLEMENTATION_PLAN.md`,** not `# TODO` in source.
- **Design discussions → `docs/IMPLEMENTATION_PLAN.md`** (Design Discussions section), not inline.
- **Raise concerns** before/alongside implementation if approach risky/fragile.

## Maintaining these docs

- **`docs/architecture.md`** = architecture reference, not rule file. Fast overview (module map, core concepts, request lifecycle) + location index (§8). Short relationship/concept lines OK; no bugfix narratives or "lessons learned" — those go in `git log`/PRs.
- **After every feature/fix:** update relevant section + location index (§8). Never leave features unlisted or removed ones listed.
- **`docs/IMPLEMENTATION_PLAN.md` task done → remove it** (history stays in `git log`).
- **Instruction files** (`.github/instructions/*.instructions.md`) = behavior rules scoped to path glob only — no architecture re-description, link to `docs/architecture.md` instead.
