"""Minimal local web server for the video streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` — same dark-theme layout
as the audio server, but with a ``<video>`` element instead of ``<audio>``.
"""

from __future__ import annotations

import html
import json as _json
import mimetypes
from pathlib import Path
from typing import Any

from hometools.config import get_video_library_dir, get_player_bar_style
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
from hometools.streaming.video.catalog import build_video_index


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


def render_video_index_html(items, library_dir: Path) -> str:
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
    app = FastAPI(title="hometools video streaming prototype")

    @app.on_event("startup")
    async def _check_library() -> None:
        import asyncio
        ok, msg = await asyncio.to_thread(check_library_accessible, resolved_library_dir)
        if not ok:
            import logging
            logging.getLogger(__name__).warning("Video-Bibliothek: %s", msg)

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
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            return HTMLResponse(render_error_page("hometools video", "🎬", msg, resolved_library_dir))
        items = build_video_index(resolved_library_dir)
        return HTMLResponse(render_video_index_html(items, resolved_library_dir))

    @app.get("/api/video/items")
    def video_items(q: str | None = None, artist: str | None = None, sort: str = "title") -> dict[str, object]:
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            return {
                "library_dir": str(resolved_library_dir),
                "count": 0,
                "items": [],
                "artists": [],
                "error": msg,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        items = build_video_index(resolved_library_dir)
        filtered = query_items(items, q=q, artist=artist, sort_by=sort)
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered),
            "items": [i.to_dict() for i in filtered],
            "artists": list_artists(items),
            "query": {"q": q or "", "artist": artist or "all", "sort": sort},
        }

    @app.get("/video/stream")
    def video_stream(path: str) -> FileResponse:
        try:
            file_path = resolve_video_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    # --- PWA endpoints ---
    _VIDEO_THEME = "#bb86fc"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=_json.loads(render_pwa_manifest("hometools video", "Video", theme_color=_VIDEO_THEME)),
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

