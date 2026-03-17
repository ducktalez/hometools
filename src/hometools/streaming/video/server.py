"""Minimal local web server for the video streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` — same dark-theme layout
as the audio server, but with a ``<video>`` element instead of ``<audio>``.
"""

from __future__ import annotations

import json as _json
import logging
import mimetypes
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from hometools.config import get_cache_dir, get_player_bar_style, get_video_library_dir, get_video_pwa_display_mode
from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists, query_items
from hometools.streaming.core.server_utils import (
    check_library_accessible,
    render_error_page,
    render_media_page,
    render_pwa_icon_png,
    render_pwa_icon_svg,
    render_pwa_manifest,
    render_pwa_service_worker,
    resolve_media_path,
)
from hometools.streaming.core.thumbnailer import get_thumbnail_path, start_background_thumbnail_generation
from hometools.streaming.video.catalog import build_video_index, collect_thumbnail_work

logger = logging.getLogger(__name__)

VIDEO_CSS_EXTRA = """
:root { --accent: #bb86fc; }
.track-item.active .track-num::before { content: '▶'; color: var(--accent); }
.ctrl-btn.play-pause:hover { background: #d1a3ff; }
.folder-play-btn:hover { background: #d1a3ff; }
.back-btn:hover { color: #d1a3ff; }
.play-all-btn:hover { background: #d1a3ff; }
.view-toggle:hover { color: var(--accent); border-color: var(--accent); }
.breadcrumb a:hover { color: #d1a3ff; }
input[type=range]:hover::-webkit-slider-thumb { background: var(--accent); }
#player {
  width: 100%; max-height: 35vh; background: #000;
  border-top: 1px solid #333; flex-shrink: 0;
}
"""


def resolve_video_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested video file inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, VIDEO_SUFFIX)


def render_video_index_html(items) -> str:
    """Render the video player UI — dark theme, folder grid, inline video element."""
    items_json = _json.dumps([i.to_dict() for i in items], ensure_ascii=False)

    return render_media_page(
        title="hometools video",
        emoji="🎬",
        items_json=items_json,
        media_element_tag="video",
        extra_css=VIDEO_CSS_EXTRA,
        api_path="/api/video/items",
        item_noun="video",
        theme_color="#bb86fc",
        player_bar_style=get_player_bar_style(),
    )


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local video streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_video_library_dir()).expanduser()
    resolved_cache_dir = get_cache_dir()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        import asyncio

        ok, msg = await asyncio.to_thread(check_library_accessible, resolved_library_dir)
        if not ok:
            import logging

            logging.getLogger(__name__).warning("Video-Bibliothek: %s", msg)
        else:
            # Trigger thumbnail generation in a background daemon thread so
            # the server is immediately responsive.
            try:
                work = await asyncio.to_thread(
                    collect_thumbnail_work,
                    resolved_library_dir,
                    resolved_cache_dir,
                )
                start_background_thumbnail_generation(work)
            except Exception:
                import logging

                logging.getLogger(__name__).debug(
                    "Failed to start background video thumbnail generation",
                    exc_info=True,
                )

        yield

    app = FastAPI(title="hometools video streaming prototype", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        ok, msg = check_library_accessible(resolved_library_dir)
        return {
            "status": "ok" if ok else "degraded",
            "library_dir": str(resolved_library_dir),
            "library_accessible": str(ok),
            "detail": msg,
        }

    @app.get("/", response_class=HTMLResponse)
    def video_home() -> HTMLResponse:
        t0 = time.monotonic()
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            logger.warning("GET / — library not accessible: %s", msg)
            return HTMLResponse(render_error_page("hometools video", "🎬", msg, resolved_library_dir))
        html = render_video_index_html([])
        elapsed = time.monotonic() - t0
        logger.info("GET / — shell rendered in %.2fs (HTML: %d bytes)", elapsed, len(html))
        return HTMLResponse(html)

    @app.get("/api/video/items")
    def video_items(q: str | None = None, artist: str | None = None, sort: str = "title") -> dict[str, object]:
        t0 = time.monotonic()
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            logger.warning("GET /api/video/items — library not accessible: %s", msg)
            return {
                "library_dir": str(resolved_library_dir),
                "count": 0,
                "items": [],
                "artists": [],
                "error": msg,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        items = build_video_index(resolved_library_dir, cache_dir=resolved_cache_dir)
        filtered = query_items(items, q=q, artist=artist, sort_by=sort)
        elapsed = time.monotonic() - t0
        logger.info("GET /api/video/items — %d/%d items in %.1fs (q=%r, artist=%r)", len(filtered), len(items), elapsed, q, artist)
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered),
            "items": [i.to_dict() for i in filtered],
            "artists": list_artists(items),
            "query": {"q": q or "", "artist": artist or "all", "sort": sort},
        }

    @app.get("/api/video/metadata")
    def video_metadata(path: str) -> dict[str, object]:
        """Re-read embedded metadata for a single video file."""
        from hometools.audio.metadata import read_embedded_metadata
        from hometools.streaming.video.catalog import _folder_as_artist, _title_from_filename

        try:
            file_path = resolve_video_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("GET /api/video/metadata — resolve failed: %s", exc)
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        title = _title_from_filename(file_path.stem)
        artist = _folder_as_artist(file_path, resolved_library_dir)

        try:
            meta = read_embedded_metadata(file_path)
        except Exception:
            logger.warning("GET /api/video/metadata — fallback for %s due to metadata read error", path, exc_info=True)
            meta = None

        if meta:
            if meta.get("title", "").strip():
                title = meta["title"].strip()
            if meta.get("artist", "").strip():
                artist = meta["artist"].strip()

        logger.debug("GET /api/video/metadata — %s → title=%r artist=%r", path, title, artist)
        return {"title": title, "artist": artist, "rating": 0.0}

    @app.get("/video/stream")
    def video_stream(path: str) -> FileResponse:
        try:
            file_path = resolve_video_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            logger.warning("GET /video/stream — not found: %s", path)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            logger.warning("GET /video/stream — invalid path: %s (%s)", path, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        logger.debug("GET /video/stream — serving %s (%s)", file_path.name, media_type)
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    @app.get("/thumb")
    def thumb(path: str) -> FileResponse:
        """Serve a cached thumbnail image for a video file."""
        from urllib.parse import unquote

        relative_path = unquote(path)
        thumb_path = get_thumbnail_path(resolved_cache_dir, "video", relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    # --- PWA endpoints ---
    _VIDEO_THEME = "#bb86fc"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=_json.loads(
                render_pwa_manifest("hometools video", "Video", theme_color=_VIDEO_THEME, display_mode=get_video_pwa_display_mode())
            ),
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        from fastapi.responses import Response

        return Response(content=render_pwa_service_worker(), media_type="application/javascript")

    @app.get("/icon.svg")
    def icon_svg():
        from fastapi.responses import Response

        return Response(content=render_pwa_icon_svg("🎬", _VIDEO_THEME), media_type="image/svg+xml")

    @app.get("/icon-192.png")
    def icon_192():
        from fastapi.responses import Response

        return Response(content=render_pwa_icon_png("🎬", 192, _VIDEO_THEME), media_type="image/png")

    @app.get("/icon-512.png")
    def icon_512():
        from fastapi.responses import Response

        return Response(content=render_pwa_icon_png("🎬", 512, _VIDEO_THEME), media_type="image/png")

    return app
