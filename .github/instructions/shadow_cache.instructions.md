---
applyTo: "src/hometools/streaming/core/thumbnailer.py"
---
# Shadow Cache

## Key rules

- **Never modify original media files.** All generated artefacts (thumbnails, failure logs) go into `HOMETOOLS_CACHE_DIR`.
- **Thumbnails mirror the library structure** as `<cache_dir>/<media_type>/<relative_path>.thumb.jpg` (120px JPEG).
- **Video seek position = 20% of total duration** (via ffprobe). Fallback to 5s if ffprobe is unavailable. This skips intros/logos for series and films.
- **MTime-based invalidation:** Before skipping an existing thumbnail, compare `source.stat().st_mtime > thumb.stat().st_mtime`. Regenerate if the source is newer. `st_mtime` = modification time, not access time.
- **Failure registry** (`thumbnail_failures.json`): Tracks failed extractions with `source_mtime`. Skip known failures unless the source file's mtime is newer (= file was replaced). Always clear the failure entry on success.
- **Exception safety:** Every public function in `thumbnailer.py` must never raise. Log and return `None`/`False` on failure.
- **Background-only extraction:** Thumbnail generation runs in a daemon thread (`start_background_thumbnail_generation`). Never block server startup or catalog building on extraction.

## Future TODOs

- **Sprite-sheet** for scroll-preview performance (not needed yet — individual JPEGs + lazy loading suffice).
- **Black-frame detection** via Pillow histogram (avg brightness < 10/255) to detect and retry dark thumbnails.
