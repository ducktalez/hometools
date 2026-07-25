# Architecture

Concise, English, current-state documentation. History and dated bugfix
narratives live in `CHANGELOG.md` — this file describes *what exists today*,
not how it evolved. Keep sections short (3–6 sentences); link to code instead
of re-explaining it.

## Layout

- `src/hometools/cli.py` — CLI entry point (`hometools = hometools.cli:main`).
- `src/hometools/config.py` — all paths/ports from `HOMETOOLS_*` env vars.
- `src/hometools/streaming/core/` — shared catalog, sync, UI generation, caching.
- `src/hometools/streaming/audio/`, `streaming/video/` — thin per-media wrappers
  (`catalog.py`, `server.py`, `sync.py`).
- `src/hometools/streaming/channel/` — HLS "TV channel" server (see below).
- `clients/` — native apps consuming the JSON API (Android TV active).
- `docs/architecture.md` (this file), `docs/CHANGELOG.md` (history),
  `docs/IMPLEMENTATION_PLAN.md` (backlog + open design discussions).

## `MediaItem` and the catalog

`MediaItem` (`streaming/core/models.py`) is a **frozen dataclass** — every
mutation creates a new instance. Key fields: `relative_path`, `title`,
`artist` (audio: real artist; video: folder name — handle empty strings),
`season`/`episode` (from `parse_season_episode()`, `(0, 0)` if undetected),
`language`/`subtitle_language`, `genre`, `rating`, `duration`, `bitrate`,
`file_size`, `mtime`, `intro_start`/`intro_end`. `build_video_index()` /
`build_audio_index()` populate the catalog; `sort_items()` orders by
`(season, episode, title)` within a folder so episodes stay chronological.
All API responses use the `items` key, never `tracks`/`videos`.

`hometools_overrides.yaml` (per folder, `media_overrides.py`) lets users
correct display names, season/episode numbers and the series title without
renaming files — applied before sorting, never mutates originals.

## `server_utils` — UI generation

`streaming/core/server_utils/` generates all HTML/CSS/JS as Python strings
(no separate frontend build). Originally one ~9000-line file, now a package:

| Module | Content |
|---|---|
| `__init__.py` | Re-exports — the only supported import path stays unchanged |
| `_svg.py` | `SVG_*` icon/flag constants (see Rule 13 below) |
| `_css.py` + `css/` | `render_base_css()`, concatenating themed fragments |
| `_player_js.py` + `player_js/` | `render_player_js()`, concatenating themed fragments |
| `_html.py` | `render_media_page()` — single HTML skeleton for audio + video |
| `_pwa.py` | Manifest, service worker, icons |
| `_audit.py` | Audit-log panel |
| `_board.py` | `/board` missing-episodes page (video only) |
| `_library.py` | Status/error pages, `check_library_accessible` |
| `_paths.py` | Path traversal validation |

### CSS/JS package split (agent-context optimization)

`_css.py` (1858 lines) and `_player_js.py` (8908 lines) were pure Python
string blobs with no internal tooling boundary, which made them expensive to
read/edit for agents. Both were split **mechanically** (AST- and
text-slice-based, verified byte-identical against the pre-split output) into
themed fragment modules that each expose one `render_<name>_css()` /
`render_<name>_js()` function; the top-level `render_base_css()` /
`render_player_js()` just concatenate them in a fixed order. **No runtime
behaviour changed.**

- `css/`: `_root.py`, `_tools_panel.py`, `_track_list.py`, `_table_view.py`,
  `_modals.py`, `_playlist_cards.py`, `_player_bar.py`, `_video_overlay.py`.
- `player_js/`: `_core.py` (bootstrap, header vars, waveform/video-overlay
  setup, skip-intro, cast, float-player), `_queue.py` (queue state + DnD),
  `_folder_browse.py` (`showFolderView` and friends), `_search_filter.py`
  (`globalSearch`, `applyFilter`), `_track_render.py` (`renderTracks`,
  player-bar actions), `_library_tools.py` (duplicates, file-mover,
  delete/reveal — still the largest fragment at ~2300 lines, a candidate for
  a further split), `_playlists.py`, `_smart_playlists.py`,
  `_drag_drop_init.py` (playlist DnD + the closing bootstrap IIFE call).
- A handful of fragments take parameters (`waveform_js`,
  `waveform_setup_js`, `sprite_preview_js`, `playlist_sync_interval_ms`)
  because the original code interpolated Python values at those exact
  points; `render_player_js()`/`render_base_css()` still have the same
  public signature as before.
- **Design rule:** the browser-side JS is one big IIFE closure — this split
  is purely at the Python-source level. Don't add real JS module boundaries
  (`import`/`export`) — there is no bundler and none is planned (see
  `IMPLEMENTATION_PLAN.md`).

### Bugfix: duplicate top-level `showToast`/`formatBytes` (2026-07-25)

**Symptom:** Creating a new playlist ("Neue Playlist…" card) sometimes
showed "Fehler beim Erstellen" even though the backend had created the
playlist successfully — a client-only false negative.

**Root cause:** The single-file `_player_js.py` (pre-dating the CSS/JS
split above) accumulated **two** independent top-level
`function showToast(msg, ...) {}` declarations (one in the section that
became `_core.py`, one in the section that became `_library_tools.py`) and
**two** `function formatBytes(...) {}` declarations (`_core.py` /
`_track_render.py`). Because the whole script is one IIFE, JS function
declarations are hoisted and the **textually later** declaration silently
wins — no `SyntaxError`, no console warning, just a quietly overridden
function. This is invisible to `esprima.parseScript()` (both versions are
valid JS) and to every existing test, which only asserted parseability and
feature-presence via substring checks — none of them asserted uniqueness
of top-level declarations. The concrete regression: any caller passing a
custom `durationMs` to `showToast(msg, durationMs)` (e.g. the "Weiter
bei …" resume toast, 3000/5000 ms) silently got the wrong 3500 ms default,
because the winning `showToast(msg)` definition ignored the second
argument entirely.

The playlist-creation error itself was not reproducible from this
duplication alone (backend + full jsdom simulation both succeeded), but
the fetch chains for playlist creation (`_folder_browse.py`'s
`newCard` handler and `_smart_playlists.py`'s `createAndAddToPlaylist()`)
also had no `response.ok` check — a non-2xx response with a non-JSON body
(e.g. a proxy error page, or the server restarting mid-request) would
throw inside `r.json()` and fall into `.catch()`, showing "Fehler beim
Erstellen" even in cases where surfacing the real HTTP status would have
been more useful. Both fetch chains now check `r.ok` and throw explicitly
so the `.catch()` always fires for a well-defined reason, and an explicit
`else { showToast('Fehler beim Erstellen'); }` branch covers the case
where the response is `200 OK` but doesn't contain a `playlist` key.

**Fix:**
- `showToast`/`formatBytes` now exist exactly once, in `_core.py` (the
  first-loaded fragment, the natural home for shared helpers). The
  duplicates in `_library_tools.py`/`_track_render.py` were removed and
  replaced with a one-line comment pointing back to `_core.py`.
- `_folder_browse.py` and `_smart_playlists.py`: playlist-creation
  `fetch(...).then(r => r.json())` now check `r.ok` first.
- New regression test `test_no_duplicate_top_level_function_declarations`
  in `tests/test_js_syntax.py` walks the esprima AST of the concatenated
  output and fails if any top-level `FunctionDeclaration` name appears
  twice. Nested functions (e.g. `initPlaylistDragDrop`'s local
  `startDrag()` vs. `initQueueDragDrop`'s own `startDrag()`, both
  legitimate per Rule 14) are intentionally excluded — only declarations
  directly inside the outer IIFE body are checked.

### Bugfix (follow-up, same day): `SVG_EDIT is not defined` broke both playlist types

The `showToast`/`formatBytes` fix above did **not** fully resolve the
"Fehler beim Erstellen" report — the actual runtime crash was a second,
unrelated bug in the same area, only visible as a real
`ReferenceError: SVG_EDIT is not defined` when interacting with a **smart**
playlist.

**Root cause:** `_folder_browse.py`'s playlist-folder-card renderer built
the smart-playlist "edit rules" button with
`'<button ...>' + SVG_EDIT + '</button>'`. `SVG_EDIT` is a **Python-only**
constant from `_svg.py` (imported by `_player_js.py` for other purposes);
no JS variable of that name was ever declared — the actual JS variable is
`IC_EDIT` (`var IC_EDIT = '<svg>...'` in `_player_js.py`'s header). The
typo is syntactically valid JS (a bare identifier reference), so
`esprima.parseScript()` — the project's only JS safety net (see above) —
could not catch it; it only surfaces as a browser `ReferenceError` the
moment `showFolderView()` tries to render a smart-playlist card.

This explains **both** reported symptoms with a single root cause:
- Creating/opening a **smart** playlist hit the broken card renderer
  directly → `ReferenceError: SVG_EDIT is not defined`.
- Creating a **plain** playlist calls `showFolderView()` afterwards to
  refresh the root view. If the user already had *any* smart playlist,
  re-rendering its card threw the same `ReferenceError` — inside the
  success `.then()` of the plain-playlist fetch chain, so it landed in the
  generic `.catch()` and showed "Fehler beim Erstellen", even though the
  plain playlist itself had already been created successfully server-side.

**Fix:** `SVG_EDIT` → `IC_EDIT` in `_folder_browse.py`. New regression test
`test_no_leaked_python_svg_constant_names` in `tests/test_js_syntax.py`
regex-scans the concatenated JS output for any bare `SVG_[A-Z_]+`
identifier — `SVG_*` names must only ever appear as Python-side constants
interpolated into an `IC_*` JS variable or an inline SVG string, never as
a literal identifier reference in the generated JS text.

## Streaming UI feature areas

Short reference for what lives where; see `player_js/` module table above
for file locations.

- **Generic kebab / three-dot menu** (`_library_tools.py`: `_openCtxMenu(btn,
  items)` + CSS `.ht-ctx-menu`/`.ht-ctx-item`): a single shared dropdown
  component used by *every* three-dot menu in the UI — track rows
  (`_openTrackCtxMenu`), the player bar (`#player-bar-kebab`), and playlist
  cards (`_openPlaylistCtxMenu` in `_folder_browse.py`). `items` is
  `[{ icon, label, onClick, danger }]`; the menu is anchored right-aligned
  to the triggering button (flips above if there's no room below).
  **Rule: any new three-dot menu must reuse `_openCtxMenu()` and sit at the
  same right-aligned position as its trigger button** — never invent a new
  bespoke dropdown or place a kebab button anywhere but the right edge of
  its card/row. Destructive items use `danger: true` (`.ht-ctx-item--danger`,
  red text/hover).
  Track rows keep `track-reveal-btn` immediately left of `track-kebab-btn`
  in both list and table mode; the duplicate-trash icon remains inside
  `.dupe-badge` near the title and is not part of the trailing action cluster.

- **Playlists** (`streaming/core/playlists.py`): CRUD, pseudo-folder cards
  on the root screen, drag-and-drop reorder (`initPlaylistDragDrop`),
  cross-device sync via `revision` + changelog, 50 playlists / 500 items
  per playlist limit, atomic JSON writes under `<cache_dir>/playlists/`.
  Card UI: the cover doubles as the play button (`.playlist-cover-play-btn`,
  a centered circular overlay inside `.playlist-thumb-wrap`, revealed on
  hover — same pattern as `.track-play-btn`). All modification actions
  (Umbenennen, Regeln bearbeiten, Aktualisieren, Löschen) live behind a
  single top-right `.playlist-folder-kebab` button (`_openPlaylistCtxMenu()`
  in `_folder_browse.py`), never as separate always-visible buttons.
- **Smart Playlists** (`streaming/core/smart_playlists.py`): store a rule
  group instead of an item list; evaluated **client-side** only
  (`_evaluateSmartPlaylist()` mirrors `evaluate_smart()`). Operators: `eq`,
  `contains`, `starts_with`, `matches`, `gte`, `lte`, `between`, `in`,
  `within_days`, `before`, `after`, `any_of`/`all_of`/`none_of` (for
  `in_playlist`). `in_playlist` never resolves against other smart
  playlists (cycle-safe by construction; DAG resolution is a Phase-2 idea,
  see IMPLEMENTATION_PLAN.md).
- **Queue**: bottom-drawer panel, `#queue-peek-handle` (drag-up or click to
  open/close, visible only when non-empty), DnD reorder
  (`initQueueDragDrop`/`destroyQueueDragDrop`).
- **Tools panel**: user-togglable UI features stored in `localStorage`
  (`ht-tools`): inline ratings, download buttons, playlist buttons,
  duplicate detection, file mover. CSS-only visibility via `body.tool-*`
  classes — no per-element JS toggling.
- **Duplicate detection**: pure client-side, `_normalizeStem()` +
  `_dupeKey()` (artist + normalized title) build a `Map<key, [indices]>`
  lazily from `allItems`; no backend endpoint. Soft-delete via
  `POST /api/<media>/delete-file` moves files to `HOMETOOLS_DELETE_DIR`.
- **File mover**: `POST /api/audio/move-file` + `GET /api/audio/folders`;
  MRU target folders in `localStorage`.
- **Windowed track rendering**: render guard (`_rgKey` fingerprint skips
  full re-render when nothing changed), batched DOM insertion
  (`_appendTrackBatch`, 100 items/batch via `IntersectionObserver`),
  single delegated click/change listener per render
  (`_wireTrackListDelegation`), 150 ms search debounce. Needed once
  libraries exceed ~6000 items.
- **Catalog cache (stale-while-revalidate)**: `localStorage` snapshot per
  `API_PATH`, max age 5 minutes (`_CATALOG_MAX_AGE_MS`). Fresh snapshot →
  render immediately, silent background fetch reconciles. Explicit refresh
  clears the cache. Client-side mutation tracking (`_locallyDeletedPaths`)
  filters just-deleted items out of background fetches until the server
  catches up. **Do not** reintroduce `fetch(..., {cache:'no-store'})` as the
  *first* load path — that was the original bug (see CHANGELOG 2026-07).
- **Video overlay / mobile player**: tap-and-drag-to-seek
  (`initTrackSeek`), `_currentItemDuration` fallback when
  `player.duration` is not finite yet, spurious-`ended` guard
  (`reachedEnd` check before advancing), iOS auto-PiP via
  `autopictureinpicture` (never calls `player.pause()` while
  transitioning into PiP on iOS), Cast button using only standard
  `Remote Playback API` / `webkitShowPlaybackTargetPicker` (no SDK).
- **Skip-intro**: button visible only within `[intro_start, intro_end]`.
  Precedence: manual UI marker → YAML override → ffprobe chapters.
  `GET/POST/DELETE /api/video/intro`.

## Native client layer (`clients/`)

Native apps (Android TV active; iOS/Android phone reserved) are **thin REST
clients** — no business logic duplicated. They implement only the
read/playback subset (`items`, `continue`, `metadata`, `progress`, `intro`,
`/video/stream`, `/thumb`); admin writes (rating/tag/move/delete/playlists)
stay web-only. Contract = OpenAPI, exported via
`hometools export-openapi --server {video,audio}` to
`clients/shared/openapi/*.json`; both servers also expose a live, filtered
`/openapi.json` + `/docs` (Swagger UI) via
`streaming/core/openapi_schema.py`. `GET /api/video/continue` joins
`get_continue_watching()` (unfinished, >30 s watched, <95 % of duration)
with the catalog.

**Android TV** (`clients/androidtv/`): Kotlin + Jetpack Compose for TV +
Media3/ExoPlayer (handles MP4/MKV/AVI + HTTP Range without server
transcoding). Three screens: server setup → browse → player. Data layer
mirrors `MediaItem.to_dict()`, tolerates unknown fields. Build/test via
`clients/androidtv/scripts/build.ps1` and `make android-*` targets; JVM unit
tests (`ApiClientTest`, `ModelsTest`) run without an emulator.

## Issue pipeline & CLI dashboard

Both streaming servers feed warnings/errors into
`streaming/core/issue_registry.py` in addition to logging:
`issues/open_issues.json` (open), `issues/issue_events.jsonl` (append-only
log), `issues/todo_candidates.json` (bundled task families), cooldown state
in `issues/todo_state.json` (also stores manual `acknowledged`/`snoozed`).
`GET /api/<media>/status` exposes a `todos` summary (monitoring/CLI only,
never shown in the browser UI); `POST /api/<media>/todos/state` accepts
`acknowledge`/`snooze`/`clear`. `_NOISE_RULES` suppress low-signal repeats;
`_ROOT_CAUSE_PATTERNS` merge related issues (e.g. `library-unreachable`)
into one TODO. `hometools stream-dashboard` renders issues + TODOs + the
last scheduler run as a table (`--json`, `--fail-on-match` for CI-style
gating). Design rule: the scheduler only ever produces *candidates* — no
destructive/automatic actions yet.

## Missing-episodes board (video only)

`streaming/core/episode_gaps.py:find_missing_episodes()` is a pure function
over the already-built catalog (no I/O): groups `MediaItem`s by
`(parent folder, season)`, requires ≥2 present episodes per season before
reporting gaps, and never flags an entirely-missing season (no reliable
inner range). `GET /api/video/board` returns `missing_episodes` (from the
in-memory catalog, instant) plus best-effort `issues` from
`scan_video_library()`. UI: `/board` (`server_utils/_board.py`, same
dark-theme family as `/audit`), entry point is the `#board-btn` in the
tools-panel header (video only). CLI: `hometools missing-episodes`.

## Library scan

`streaming/core/library_scan.py` — read-only, filesystem-only analysis (no
ffprobe, no network) for `hometools scan-library`. Video checks:
`episode_naming` (warning), `oversized_folder`, `untagged_language`
(info). Audio: `oversized_folder`. `ScanReport.to_dict()` is
JSON-serializable; `--fail-on-warning` sets exit code 1. Always
exception-safe (returns an empty report on any failure).

## Index caching

`/api/<media>/items` checks the cache first and only calls
`check_library_accessible()` (up to ~3 s on NAS paths) when no cached items
exist yet — never blocks delivery of already-available data. A persisted
snapshot's age (`saved_at`) is honored as-is on load: a snapshot younger
than `HOMETOOLS_STREAM_INDEX_CACHE_TTL` (default 900 s) is *not* rebuilt at
startup; only older snapshots trigger a background rescan. Explicit
`POST /api/<media>/refresh` always forces a full rebuild
(`IndexCache.invalidate()`).

## Shadow cache (`.hometools-cache/`)

Mirrors the library layout for all generated artefacts (default:
`.hometools-cache/` in the repo root, override via `HOMETOOLS_CACHE_DIR`).
**Never modifies original media files.** Subdirectories: `audio/`, `video/`
(thumbnails, small 120px + large 480px; waveform `*.waveform.json` files;
faststart/remux MP4 caches), `indexes/` (persisted snapshots),
`progress/`, `issues/`, `logs/`, plus `thumbnail_failures.json` and
`video_metadata_cache.json`. `make clean` removes all of the above; the
audit log lives separately under `HOMETOOLS_AUDIT_DIR` and is untouched.

Thumbnails and faststart/remux caches use **mtime-based invalidation**
(`source.st_mtime > cache.st_mtime` triggers regeneration) and run only in
background daemon threads — never on the request path or at startup.
Failure registries (`thumbnail_failures.json`) skip known-bad sources
unless the source mtime advanced.

### Waveform cache (audio)

`streaming/core/waveform.py` extracts stereo peak data via ffmpeg
(`-ac 2 -f f32le -ar 1000`, 256 segments/channel), stored as
`<cache_dir>/audio/<relative_path>.waveform.json`
(`{"peaks_l": [...], "peaks_r": [...], "segments": 256}`, with a
mono-only legacy format still supported for old caches).
`GET /api/audio/waveform?path=` serves from cache or generates on demand;
`start_background_waveform_generation()` warms the whole library at
startup. Classic player-bar canvas renders stereo (L above/R below
centerline) or falls back to mono/plain-progress if no data is available.

## On-the-fly remux, faststart & the iOS streaming cache

`streaming/core/remux.py` solves two separate problems for `GET
/video/stream`:

1. **Non-native containers** (MKV/AVI/FLV, `needs_remux()`): copy-remuxed
   to fragmented MP4 if codecs are browser-compatible
   (`can_copy_codecs()`), else transcoded (H.264/AAC).
2. **Non-faststart MP4s** (`moov` atom at the end): iOS Safari requires
   HTTP Range (`206 Partial Content`), which a live ffmpeg pipe cannot
   provide. Both cases get a **cached, range-capable MP4 copy**
   (`ensure_faststart_cache()` / `ensure_remux_cache()`,
   `{cache_dir}/video/{relative_path}.{faststart,remux}.mp4`) served via
   `FileResponse`; only as a last-resort fallback does the endpoint use a
   live `StreamingResponse`. Codec-copy caches build in seconds; codec
   transcodes are triggered in the background and served once ready
   (`HOMETOOLS_PRETRANSCODE` opts into eager whole-library
   pre-transcoding, default off — the cache would otherwise grow to
   double-digit GB). Temp files use an atomic tmp→rename pattern with
   `try/finally` cleanup; a startup sweep thread removes any stale
   `*.tmp.mp4` left over from crashes.

Design rules: originals are never modified; faststart conversion is
`-c copy` (no re-encode); ffmpeg/ffprobe failures fall back gracefully
(never crash the request).

## Channel streaming (`streaming/channel/`)

A continuous HLS "TV channel" fed by a YAML programme schedule
(`channel_schedule.yaml`), fundamentally different from the on-demand
audio/video servers:

- **Pre-transcode, never live-transcode into the stream.** All videos for
  an upcoming block are transcoded to a uniform H.264/AAC 1280×720@25fps
  MP4 in `.hometools-cache/channel/tmp/` *before* being fed to ffmpeg;
  temp files are deleted after playback.
- **Concat demuxer, single ffmpeg process.** One `-f concat -i list.txt -f
  hls` process per block (slot or filler period) — never one process per
  video. Per-video processes caused unavoidable segment-transition gaps
  and 404s for hls.js; that architecture (and its workarounds — segment
  counter sync, manifest cleanup) has been removed.
- **Block lifecycle:** pre-transcode → write `concat.txt` → start ffmpeg →
  wait for completion or interruption (stop/slot change) → delete temp
  files.

## Docker deployment

Multi-stage image (Python 3.12-slim + ffmpeg + tini, non-root user with
configurable UID/GID). `docker-compose.yml` runs one container per service
from the same image: `audio` (8010, behind the `audio` Compose profile,
optional), `video` (8011), `channel` (8012, optional). Shared named volumes
`hometools-cache` / `hometools-audit` map to `/data/cache` / `/data/audit`
and survive rebuilds. Library mounts default to `:ro`; write features
(ratings, tag edit, move, soft-delete) need an explicit `rw` mount.
`HOMETOOLS_STREAM_HOST=0.0.0.0`, `HOMETOOLS_CACHE_DIR=/data/cache`,
`HOMETOOLS_AUDIT_DIR=/data/audit` are fixed in the image. Healthchecks use
`/health` per container port. Tests are excluded from the build via
`.dockerignore`. See `docs/docker.md` for the full `.env` reference.

## PWA & offline downloads

`_pwa.py` renders the manifest, service worker and icons. The service
worker caches static assets (HTML/CSS/JS) and serves IndexedDB blobs for
offline playback; **API responses are never cached** by the service
worker — always fetched fresh. Offline downloads use IndexedDB for blob
storage; PWA shortcuts support deep-linking (pin a folder to the home
screen).

## SVG icons (Design Rule 13)

No Unicode/emoji for UI controls — iOS renders them as coloured emojis.
Every icon is an inline SVG constant. `SVG_*` (Python, `_svg.py`) and
`IC_*` (JS, injected by `_player_js.py`/fragments) constants currently
cover: play/pause/prev/next/pip/back/menu/download/check/folder-play/
pin/star (+empty)/shuffle/repeat/history/board/edit/lyrics/playlist/
smart-playlist/queue/refresh/duplicate/move/trash/dots/cast, plus flags
for de/en/fr/es/it/ja/ko/zh/pt/ru. New constants always go in `_svg.py`
(Python side), never inline in a fragment module.

## Known follow-ups

See `docs/IMPLEMENTATION_PLAN.md` for the maintained backlog (including a
further split of `player_js/_library_tools.py`, ~2300 lines) and open
design discussions (Smart Playlist cascades, `added_at` field, etc.).

## JS syntax safety net (no TypeScript/bundler)

`tests/test_js_syntax.py` parses the fully concatenated
`render_player_js()` output (several audio/video × classic/waveform
configs) with the pure-Python `esprima` parser and fails the build on
invalid JS — the most likely breakage from editing one of the split
`player_js/_*.py` fragments. This is a deliberate alternative to a
TypeScript/bundler migration: server config values are interpolated
directly into the JS text at render time, which is fundamentally
incompatible with a build-time bundler without a bigger architecture
change first (splitting config out into a separate JSON payload). See
"TypeScript/bundler switch" in `docs/IMPLEMENTATION_PLAN.md` — Design
Discussions for the full trade-off analysis and revisit conditions.


