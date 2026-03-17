---
applyTo: "src/hometools/streaming/**"
---
# Streaming

## Core design rules

- **`MediaItem` is frozen.** Never mutate; create new instances.
- **`artist` is overloaded.** Audio: actual artist. Video: folder name. Handle empty strings.
- **`render_media_page()`** is the single HTML skeleton — never duplicate per media type.
- **API responses use `items` key** (not `tracks` or `videos`).

## Audio ↔ Video parity

Audio and video servers share ~80% of their code via `streaming/core/`.
When adding or changing a feature:

1. **Check if it belongs in `core/`.** Catalog query/sort/filter, sync logic,
   UI rendering, PWA support, thumbnail handling — all shared.
2. **If it's media-type-specific**, put it in `streaming/audio/` or
   `streaming/video/` but keep the interface consistent (same endpoint
   patterns, same response shapes).
3. **Never duplicate endpoints.** `/health`, `/manifest.json`, `/sw.js`,
   `/icon-*.png`, `/thumb` — these are generic. If both servers need it,
   it belongs in `core/server_utils.py`.

## Adding a new media type

1. `streaming/<type>/catalog.py` → `list[MediaItem]`
2. `streaming/<type>/sync.py` → delegate to `core.sync`
3. `streaming/<type>/server.py` → call `render_media_page()`
4. CLI in `cli.py`, config in `config.py`, tests in `tests/`

## Client caching contract

- **Service Worker** caches static assets (HTML/CSS/JS) and serves
  IndexedDB blobs for offline media playback.
- **API responses** are NOT cached by the Service Worker — always fresh.
- **Thumbnails** are served from the shadow cache directory on disk.
  Cache-busting is handled by MTime comparison in the background worker.
- When changing API response shapes, the Service Worker and frontend JS
  must both be updated (they are generated strings in `server_utils.py`).
