# Streaming

> Part of [INSTRUCTIONS.md](../INSTRUCTIONS.md). Covers `streaming/`.

## Modules

| Sub-package | Modules |
|-------------|---------|
| `core/` | `catalog.py`, `models.py`, `server_utils.py`, `sync.py`, `thumbnailer.py` |
| `audio/` | `catalog.py`, `server.py`, `sync.py` |
| `video/` | `catalog.py`, `server.py`, `sync.py` |

## Core design rules

- **`MediaItem` is frozen.** Never mutate; create new instances.
- **`artist` is overloaded.** Audio: actual artist. Video: folder name. Handle empty strings.
- **`render_media_page()`** is the single HTML skeleton — never duplicate.
- **API responses use `items` key** (not `tracks`).

## API pattern (same for audio & video)

```
GET /api/<type>/tracks?q=&artist=&sort= → { "items": [...] }
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
| `test_streaming_core.py` |
| `test_streaming_audio_catalog.py` |
| `test_streaming_audio_server.py` |
| `test_streaming_audio_sync.py` |
| `test_streaming_video.py` |
