"""Minimal local web server for the audio streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` for shared UI rendering
so that the video server can reuse the same dark-theme layout.
"""

from __future__ import annotations

import html
import json as _json
import mimetypes
from pathlib import Path
from typing import Any

from hometools.config import get_audio_library_dir
from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    list_artists,
    query_tracks,
)
from hometools.streaming.core.server_utils import render_media_page, resolve_media_path


AUDIO_CSS_EXTRA = """
.track-item.active .track-num::before { content: '♪'; color: var(--accent); }
#player { display: none; }
"""


def resolve_audio_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested audio track inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, AUDIO_SUFFIX)


def render_audio_index_html(tracks: list[AudioTrack], library_dir: Path) -> str:
    """Render the audio player UI — dark theme, fixed bottom player, scrollable track list."""
    artists = list_artists(tracks)
    artist_options = "\n".join(
        f'<option value="{html.escape(a, quote=True)}">{html.escape(a)}</option>'
        for a in artists
    )
    items_json = _json.dumps([t.to_dict() for t in tracks], ensure_ascii=False)

    return render_media_page(
        title="hometools audio",
        emoji="🎵",
        items_json=items_json,
        artist_options_html=artist_options,
        media_element_tag="audio",
        extra_css=AUDIO_CSS_EXTRA,
        api_path="/api/audio/tracks",
        item_noun="track",
        filter2_label="Artist",
    )


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    app = FastAPI(title="hometools audio streaming prototype")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "library_dir": str(resolved_library_dir)}

    @app.get("/", response_class=HTMLResponse)
    def audio_home() -> HTMLResponse:
        tracks = build_audio_index(resolved_library_dir)
        return HTMLResponse(render_audio_index_html(tracks, resolved_library_dir))

    @app.get("/api/audio/tracks")
    def audio_tracks(q: str | None = None, artist: str | None = None, sort: str = "artist") -> dict[str, object]:
        tracks = build_audio_index(resolved_library_dir)
        filtered = query_tracks(tracks, q=q, artist=artist, sort_by=sort)
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered),
            "items": [t.to_dict() for t in filtered],
            "artists": list_artists(tracks),
            "query": {"q": q or "", "artist": artist or "all", "sort": sort},
        }

    @app.get("/audio/stream")
    def audio_stream(path: str) -> FileResponse:
        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    return app

