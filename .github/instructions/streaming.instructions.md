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

## Channel streaming (Fernsehsender)

The channel server produces a **continuous HLS livestream** via ffmpeg.
It is fundamentally different from the on-demand audio/video servers.

### Pre-transcode — no live transcoding into the stream

**Streams must be prepared before being fed into the HLS pipeline.**
All videos are pre-transcoded to a uniform MP4 format (H.264/AAC,
1280×720, 25fps) in `.hometools-cache/channel/tmp/` *before* the
concat-based ffmpeg process reads them.  Temporary files are deleted
after playback.

**Live transcoding from disk/NAS directly into the stream is
prohibited.**  It leads to inconsistent timing, buffer underruns,
and race conditions where hls.js requests segments that don't exist.

### Concat demuxer — single ffmpeg process

The mixer uses ffmpeg's **concat demuxer** (`-f concat`) to read
a list of pre-transcoded files sequentially in a **single** process.
This eliminates the gap problem that occurred with per-video processes.

**Never start a separate ffmpeg process per video/filler** — process
transitions create unavoidable gaps that cause 404 errors.  The old
multi-process architecture and its workarounds (segment counter sync,
manifest cleanup, `_sync_segment_counter_from_disk`,
`_cleanup_stale_manifest`) have been removed.

### Block-based architecture

Each playback unit (a slot or filler period) is a *block*:

1. Pre-transcode all videos for the block → uniform MP4 in `tmp/`.
2. Write a concat list file (`concat.txt`).
3. Start **one** ffmpeg process: `-f concat → -f hls`.
4. Wait for process to finish (or interrupt on stop/slot change).
5. Delete temporary files.

