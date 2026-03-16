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

from hometools.config import get_video_library_dir
from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists, query_items
from hometools.streaming.core.server_utils import render_media_page, resolve_media_path
from hometools.streaming.video.catalog import build_video_index


VIDEO_CSS_EXTRA = """
.track-item.active .track-num::before { content: '▶'; color: var(--accent); }
#player {
  width: 100%; max-height: 35vh; background: #000;
  border-top: 1px solid #333; flex-shrink: 0;
}
"""


def resolve_video_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested video file inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, VIDEO_SUFFIX)


def render_video_index_html(items, library_dir: Path) -> str:
    """Render the video player UI — dark theme, inline video element, scrollable list."""
    artists = list_artists(items)
    artist_options = "\n".join(
        f'<option value="{html.escape(a, quote=True)}">{html.escape(a)}</option>'
        for a in artists
    )
    items_json = _json.dumps([i.to_dict() for i in items], ensure_ascii=False)

    return render_media_page(
        title="hometools video",
        emoji="🎬",
        items_json=items_json,
        artist_options_html=artist_options,
        media_element_tag="video",
        extra_css=VIDEO_CSS_EXTRA,
        api_path="/api/video/items",
        item_noun="video",
        filter2_label="Folder",
    )


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local video streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_video_library_dir()).expanduser()
    app = FastAPI(title="hometools video streaming prototype")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "library_dir": str(resolved_library_dir)}

    @app.get("/", response_class=HTMLResponse)
    def video_home() -> HTMLResponse:
        items = build_video_index(resolved_library_dir)
        return HTMLResponse(render_video_index_html(items, resolved_library_dir))

    @app.get("/api/video/items")
    def video_items(q: str | None = None, artist: str | None = None, sort: str = "title") -> dict[str, object]:
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

    return app

