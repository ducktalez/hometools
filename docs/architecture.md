# hometools – Architecture Reference

> Framework overview for developers and AI assistants.
> Behavioral rules: `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md`.
> Open tasks: `docs/IMPLEMENTATION_PLAN.md`.

---

## 1. What is hometools?

CLI tool collection + two local FastAPI **streaming servers** (audio &
video) sharing one core, plus a dark-theme PWA UI and native clients.

``
Input:  media library on disk (audio/video files, optional NAS mount)
Output: browsable/streamable catalog via REST API + generated web UI
``

---

## 2. Module overview

``
src/hometools/
├── cli.py                    # entry point (`hometools` console script)
├── config.py                 # HOMETOOLS_* env vars, single source of paths/ports
├── audio/, video/             # standalone file CLI tools (sanitize, metadata,
│                              #   compare, merger, silence, organizer)
├── streaming/
│   ├── core/                 # shared by audio+video servers (~80%)
│   │   ├── models.py         # MediaItem, build_*_index, sort_items
│   │   ├── catalog cache     # IndexCache — GET/refresh, TTL
│   │   ├── media_overrides.py, playlists.py, smart_playlists.py
│   │   ├── issue_registry.py, episode_gaps.py, library_scan.py
│   │   ├── thumbnailer.py, waveform.py, remux.py
│   │   ├── bpm_hints.py, openapi_schema.py
│   │   ├── server_factory.py # register_* shared routes: health, PWA, progress, shortcuts, playlists, folder-order, todos, audit list, reveal, delete-file, index list/refresh/status, thumb
│   │   └── server_utils/     # HTML skeleton, PWA, SVG icons, static serving (Python)
│   │   └── webui/            # Vite/TypeScript player UI source (built to core/static/)
│   ├── audio/                # catalog.py, server.py, sync.py (thin wrapper)
│   ├── video/                 # catalog.py, server.py, sync.py (thin wrapper)
│   └── channel/               # HLS "TV channel" server (own architecture)
└── clients/                   # native apps consuming the JSON API
    └── androidtv/              # Kotlin + Compose for TV + Media3 (active)
``

---

## 3. Core concepts

- **`MediaItem`** (`streaming/core/models.py`) — frozen dataclass, the single
  item shape shared by audio+video. Never mutated; every transform returns a
  new instance. Fields: `relative_path`, `title`, `artist` (video: folder
  name), `season`/`episode`, `language`/`subtitle_language`, `genre`,
  `rating`, `duration`, `bitrate`, `file_size`, `mtime`, `intro_start/end`,
  `bpm`. All API responses expose items under `"items"`.
- **Index cache** — catalog build is expensive (filesystem scan + ffprobe),
  so each server keeps an in-memory + on-disk (`indexes/`) snapshot with a
  TTL (`HOMETOOLS_STREAM_INDEX_CACHE_TTL`). Only `POST /refresh` forces a
  full rebuild.
- **Shadow cache (`.hometools-cache/`, `HOMETOOLS_CACHE_DIR`)** — mirrors the
  library layout for every *generated* artefact (thumbnails, waveforms,
  faststart/remux MP4s, index snapshots, issues, logs). Original media files
  are never touched; invalidation is mtime-based.
- **`#ht-config` bridge** — `_html.py` embeds one JSON blob (`CFG`) per page;
  the TS app reads config/API paths/icons from it (`config.ts`) instead of
  Python string-interpolating values; `app.ts` derives every `*_API_PATH`
  from `cfg.apiPath` (see §7).
- **Issue pipeline** — background scans/servers feed warnings into
  `issue_registry.py` (`issues/open_issues.json` + append-only event log);
  bundled into `todos`, exposed for monitoring/CLI only, never in the
  browser UI.

---

## 4. Request lifecycle (audio/video server)

``
startup            → mount static assets, load cached index if fresh, start
                      background thumbnail/waveform generation (daemon threads)
GET /               → render_media_page() (HTML skeleton + #ht-config + JS)
GET /api/.../items  → IndexCache (rebuild only if stale/missing/forced)
GET /thumb          → shadow cache lookup → background-generate if missing
                      (video: size=sprite → sprite sheet; GET /api/video/sprites → meta;
                       webui/src/hoverPreview.ts cycles frames on `[data-preview-path]` hover)
GET /video/stream   → direct file, or faststart/remux cache, or live fallback
POST /refresh       → IndexCache.invalidate() → full rebuild
``

Client side: `localStorage` catalog cache (stale-while-revalidate, 5 min) →
instant render → silent background fetch reconciles → Service Worker caches
static assets only (never API responses) → IndexedDB stores offline blobs.

---

## 5. Channel server (different architecture)

Continuous HLS "TV channel" driven by `channel_schedule.yaml`. Unlike the
on-demand servers: videos are **pre-transcoded** to a uniform H.264/AAC
1280×720@25fps MP4 before ffmpeg ever sees them, and a **single** ffmpeg
process per block reads them via the concat demuxer
(`-f concat -i list.txt -f hls`). No live transcoding into the stream, no
per-video ffmpeg process (both were tried and removed — see git log).

---

## 6. Native clients

Thin REST clients over the same API — no business logic duplicated.
Read/playback subset only (`items`, `continue`, `metadata`, `progress`,
`intro`, `/video/stream`, `/thumb`); admin writes (rating/tag/move/delete/
playlists) stay web-only. Contract = `clients/shared/openapi/*.json`
(`hometools export-openapi`) + live `/openapi.json`/`/docs`.

Android TV (`clients/androidtv/`): Kotlin + Jetpack Compose for TV +
Media3/ExoPlayer, three screens (setup → browse → player), data layer
mirrors `MediaItem.to_dict()`.

---

## 7. Web UI (Vite/TypeScript)

All player JS/CSS is real TypeScript/CSS in `streaming/core/webui/` (Vite),
built to `core/static/` and served at `/static` by `server_utils/_static.py`.
Python only renders the HTML skeleton (`_html.py`), PWA files and SVG icons.
Details + usage: `webui/README.md`.

- **Entry:** `src/main.ts` (CSS imports, click guard, hover preview) calls
  `startApp()` in `src/app.ts`, the composition root: reads `#ht-config`
  (`config.ts::readConfig`), builds the `create*Wiring` factories and hands
  them thunk-style deps (late-bound, so cross-wiring cycles resolve per call).
- **Wiring factories** (`*Wiring.ts`): `playlistWiring`, `folderWiring`,
  `searchFilterWiring`, `trackRenderWiring`, `libraryWiring`, `catalogWiring`,
  `playbackWiring`. `cfg` = eager constants; `deps` = callbacks resolved per
  call. Factories must not call into deps during construction (use `start()`).
- **State:** `playbackState.ts::createPlaybackState` (`_pb` in `app.ts`: items,
  index, path, shuffle/repeat, queue, playlists, favorites), exposed as
  `window.htState` (`stateBridge.ts`); `dom.ts` (DOM refs), `viewState.ts`
  (persisted filter/view state). `window.originalTitle` is the only other
  window global (`globals.d.ts`).
- **Feature modules:** one file per concern (`queue.ts`, `filterChain.ts`,
  `folderContents.ts`, `trackRows.ts`, `router.ts`, `offlineDb.ts`, ...);
  pure ones take explicit params. `offlineDb.ts` name/version = contract with
  the SW in `_pwa.py`.
- **Icons:** `_svg.py` (`SVG_*`) is the single source; `_html.py` puts them in
  `#ht-config.icons` (key = suffix, e.g. `PLAY`, `FLAG_DE`). Inline-only icons
  stay in `app.ts` (`IC_*`).
- **CSS:** `src/styles/*.css`, one stylesheet linked by `_static.py`.
- **Tests:** `webui/test/*.test.ts` (vitest, `npm test`; pytest wrapper
  `tests/test_webui_unit.py`). Typecheck: `npm run typecheck`.

---
## 8. Feature location index

Quick "where does X live" lookup — one line each, grouped by area.

**UI/rendering** (`server_utils/`): header `<header>` (`_html.py`, always
zurück|Home|Breadcrumb|spacer|Tools|Suche, `renderBreadcrumb()` in
`breadcrumb.ts` — inline in header, no separate nav row, no unicode icons) ·
header state: `_applyHeaderState()` (`app.ts`) is the
ONLY writer of header controls; the two view entry points
`_enterTrackListView()` / `_enterFolderGridView()` delegate to it, so every
view shows the same controls (incl. global search) and differs only in
content/enabled state · kebab menu `_openCtxMenu()`
(`ctxMenu.ts`) · playlists `playlists.py` +
`playlistWiring.ts` · smart playlists `smart_playlists.py` +
`smartPlaylist.ts` · queue `queue.ts` · tools panel `localStorage['ht-tools']`
+ `body.tool-*` · duplicate detection `dupeUtils.ts` · file mover
`POST /api/audio/move-file` · windowed rendering `trackRenderWindow.ts` ·
catalog cache `localStorage` (`webui/src/catalogCache.ts`, TTL `CATALOG_MAX_AGE_MS`) · skip-intro
`GET/POST/DELETE /api/video/intro` · video extra folders (outside library;
virtual top-level folder `<alias>/…`, stored `<cache>/extra_folders/video.json`)
`core/extra_folders.py` + `GET/POST/DELETE /api/video/folders` +
`video/catalog.py::_collect_video_entries` + `resolve_video_path_extra` +
tools-row buttons `rootCards.ts` / `extraFolders.ts` (no YAML overrides
for extra folders) · BPM `audio/metadata.py` +
`audio/bpm.py` + `bpm_hints.py` + `metricPill.ts` · video hover preview
(sprite frames on thumbnail hover) `webui/src/hoverPreview.ts` +
`thumbnailer.generate_sprite_sheet` + `GET /api/video/sprites`.

**Backend features**: missing-episodes board `episode_gaps.py` +
`GET /api/video/board` + `/board` · library scan `library_scan.py` +
`hometools scan-library` · issue dashboard `issue_registry.py` +
`hometools stream-dashboard` · waveform `waveform.py` +
`GET /api/audio/waveform` · remux/faststart `remux.py` +
`GET /video/stream`.

**Ops**: Docker `Dockerfile` (multi-stage incl. `webui-builder`) +
`docker-compose.yml` (services `audio`/`video`/`channel`) · PWA `_pwa.py`
(manifest/SW/icons) + IndexedDB offline downloads · local webui build
`streaming/webui_build.py` + `hometools build-webui` (mtime-based staleness
check; wired as PyCharm before-launch task) · webui JS unit tests
`webui/test/` (vitest, `npm test`; pytest wrapper `tests/test_webui_unit.py`)
· PyCharm run configs generated
by `streaming/setup.py::generate_pycharm_configs` + `hometools setup-pycharm`
(`.idea/` is git-ignored, so nothing is committed).

**Icons**: `_svg.py` (`SVG_*`) is the single source; delivered to the app via `#ht-config.icons` — no independent literals in TS (past bug, see git log).

---

## 9. Adding a new media type

1. `streaming/<type>/catalog.py` → `list[MediaItem]`
2. `streaming/<type>/sync.py` → delegate to `core.sync`
3. `streaming/<type>/server.py` → call `render_media_page()`
4. CLI in `cli.py`, config in `config.py`, tests in `tests/`


