# hometools – Architecture Reference

> Framework overview for developers and AI assistants.
> Behavioral rules: `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md`.
> Open tasks: `docs/IMPLEMENTATION_PLAN.md`.

---

## 1. What is hometools?

CLI tool collection + two local FastAPI **streaming servers** (audio &
video) sharing one core, plus a dark-theme PWA UI and native clients.

```
Input:  media library on disk (audio/video files, optional NAS mount)
Output: browsable/streamable catalog via REST API + generated web UI
```

---

## 2. Module overview

```
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
│   │   └── server_utils/     # generates HTML/CSS/JS as Python strings (legacy)
│   │       ├── css/, player_js/   # split fragments, concatenated at render time
│   │       └── webui/             # Vite/TypeScript migration target (in progress)
│   ├── audio/                # catalog.py, server.py, sync.py (thin wrapper)
│   ├── video/                 # catalog.py, server.py, sync.py (thin wrapper)
│   └── channel/               # HLS "TV channel" server (own architecture)
└── clients/                   # native apps consuming the JSON API
    └── androidtv/              # Kotlin + Compose for TV + Media3 (active)
```

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
  the generated JS reads config/API paths from `CFG` instead of Python
  string-interpolating each value individually (`_apiBase()` derives every
  `*_API_PATH` from `CFG.apiPath`). This is the seam the Vite/TS migration
  is peeling outward from (see §7).
- **Issue pipeline** — background scans/servers feed warnings into
  `issue_registry.py` (`issues/open_issues.json` + append-only event log);
  bundled into `todos`, exposed for monitoring/CLI only, never in the
  browser UI.

---

## 4. Request lifecycle (audio/video server)

```
startup            → mount static assets, load cached index if fresh, start
                      background thumbnail/waveform generation (daemon threads)
GET /               → render_media_page() (HTML skeleton + #ht-config + JS)
GET /api/.../items  → IndexCache (rebuild only if stale/missing/forced)
GET /thumb          → shadow cache lookup → background-generate if missing
GET /video/stream   → direct file, or faststart/remux cache, or live fallback
POST /refresh       → IndexCache.invalidate() → full rebuild
```

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

## 7. Vite/TypeScript migration (in progress)

Goal: replace the Python-string JS/CSS generators
(`server_utils/_player_js.py` + `player_js/*.py` + `_css.py` + `css/*.py`,
~8900 lines) module-by-module with real `.ts`/`.css`, built by Vite, served
as static assets. Backend is unaffected.

- `streaming/core/webui/` — Vite project (`src/main.ts` defines `PlayerConfig`
  and hosts already-ported leaf modules: `pathUtils.ts`, `dupeUtils.ts`,
  `metricPill.ts`, `breadcrumb.ts`, `smartPlaylist.ts`, `recentMoveTargets.ts`,
  `catalogCache.ts`, `offlineDownloads.ts`, `langDetect.ts`, `episodeGaps.ts`,
  `catalogQuery.ts`; `legacy-globals.d.ts` types the shared cross-fragment
  globals still owned by the legacy script).
- `server_utils/_static.py` mounts the Vite build output at `/static` and
  injects its script tag right before the legacy inline `<script>` — same
  execution order as before, zero behavior change.
- Only dependency-free leaf functions have been ported so far; the
  stateful fragments (`_core.py`, `_library_tools.py`, ...) are blocked by
  cross-fragment coupling (see `docs/IMPLEMENTATION_PLAN.md` → Design
  Discussions → "Player-JS-Modulkopplung").
- Safety net until the migration is complete: `tests/test_js_syntax.py`
  parses the concatenated legacy JS with `esprima`.

---

## 8. Feature location index

Quick "where does X live" lookup — one line each, grouped by area.

**UI/rendering** (`server_utils/`): header `<header>` (`_html.py`, always
zurück|Home|Breadcrumb|spacer|Tools|Suche, `renderBreadcrumb()` in
`_queue.py` — inline in header, no separate nav row, no unicode icons) ·
kebab menu `_openCtxMenu()`
(`player_js/_library_tools.py`) · playlists `playlists.py` +
`_folder_browse.py` · smart playlists `smart_playlists.py` +
`_smart_playlists.py` · queue `_queue.py` · tools panel `localStorage['ht-tools']`
+ `body.tool-*` · duplicate detection `dupeUtils.ts` · file mover
`POST /api/audio/move-file` · windowed rendering `_track_render.py` ·
catalog cache `localStorage` (`webui/src/catalogCache.ts`, bridged onto
`window` by `main.ts`, TTL `CATALOG_MAX_AGE_MS`) · skip-intro
`GET/POST/DELETE /api/video/intro` · BPM `audio/metadata.py` +
`audio/bpm.py` + `bpm_hints.py` + `metricPill.ts`.

**Backend features**: missing-episodes board `episode_gaps.py` +
`GET /api/video/board` + `/board` · library scan `library_scan.py` +
`hometools scan-library` · issue dashboard `issue_registry.py` +
`hometools stream-dashboard` · waveform `waveform.py` +
`GET /api/audio/waveform` · remux/faststart `remux.py` +
`GET /video/stream`.

**Ops**: Docker `Dockerfile` (multi-stage incl. `webui-builder`) +
`docker-compose.yml` (services `audio`/`video`/`channel`) · PWA `_pwa.py`
(manifest/SW/icons) + IndexedDB offline downloads.

**Icons**: `_svg.py` (`SVG_*`, Python) ↔ `IC_*` (JS, `player_js/_core.py`
header) — always keep 1:1, no independent literals (past bug, see git log).

---

## 9. Adding a new media type

1. `streaming/<type>/catalog.py` → `list[MediaItem]`
2. `streaming/<type>/sync.py` → delegate to `core.sync`
3. `streaming/<type>/server.py` → call `render_media_page()`
4. CLI in `cli.py`, config in `config.py`, tests in `tests/`


