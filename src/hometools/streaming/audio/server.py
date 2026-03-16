"""Minimal local web server for the audio streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` for shared UI rendering
so that the video server can reuse the same dark-theme layout.
"""

from __future__ import annotations

import json as _json
import mimetypes
from pathlib import Path
from typing import Any

from hometools.config import get_audio_library_dir, get_cache_dir, get_player_bar_style
from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    collect_thumbnail_work,
    list_artists,
    query_tracks,
)
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


AUDIO_CSS_EXTRA = """
.track-item.active .track-num::before { content: '♪'; color: var(--accent); }
#player { display: none; }
"""


def resolve_audio_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested audio track inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, AUDIO_SUFFIX)


def render_audio_index_html(tracks: list[AudioTrack], library_dir: Path) -> str:
    """Render the audio player UI — dark theme, folder grid, player."""
    items_json = _json.dumps([t.to_dict() for t in tracks], ensure_ascii=False)

    return render_media_page(
        title="hometools audio",
        emoji="🎵",
        items_json=items_json,
        media_element_tag="audio",
        extra_css=AUDIO_CSS_EXTRA,
        api_path="/api/audio/tracks",
        item_noun="track",
        theme_color="#1db954",
        player_bar_style=get_player_bar_style(),
    )


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    resolved_cache_dir = get_cache_dir()
    app = FastAPI(title="hometools audio streaming prototype")

    @app.on_event("startup")
    async def _check_library() -> None:
        import asyncio
        ok, msg = await asyncio.to_thread(check_library_accessible, resolved_library_dir)
        if not ok:
            import logging
            logging.getLogger(__name__).warning("Audio-Bibliothek: %s", msg)
        else:
            # Trigger thumbnail generation in a background daemon thread so
            # the server is immediately responsive.
            try:
                work = await asyncio.to_thread(
                    collect_thumbnail_work, resolved_library_dir, resolved_cache_dir,
                )
                start_background_thumbnail_generation(work)
            except Exception:
                import logging
                logging.getLogger(__name__).debug(
                    "Failed to start background audio thumbnail generation", exc_info=True,
                )

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
    def audio_home() -> HTMLResponse:
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            return HTMLResponse(render_error_page("hometools audio", "🎵", msg, resolved_library_dir))
        tracks = build_audio_index(resolved_library_dir, cache_dir=resolved_cache_dir)
        return HTMLResponse(render_audio_index_html(tracks, resolved_library_dir))

    @app.get("/api/audio/tracks")
    def audio_tracks(q: str | None = None, artist: str | None = None, sort: str = "artist") -> dict[str, object]:
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
        tracks = build_audio_index(resolved_library_dir, cache_dir=resolved_cache_dir)
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

    @app.get("/thumb")
    def thumb(path: str) -> FileResponse:
        """Serve a cached thumbnail image for an audio track."""
        from urllib.parse import unquote
        relative_path = unquote(path)
        thumb_path = get_thumbnail_path(resolved_cache_dir, "audio", relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    # --- PWA endpoints ---
    _AUDIO_THEME = "#1db954"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=_json.loads(render_pwa_manifest("hometools audio", "Audio", theme_color=_AUDIO_THEME)),
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        from fastapi.responses import Response
        return Response(content=render_pwa_service_worker(), media_type="application/javascript")

    @app.get("/icon.svg")
    def icon_svg():
        from fastapi.responses import Response
        return Response(content=render_pwa_icon_svg("🎵", _AUDIO_THEME), media_type="image/svg+xml")

    @app.get("/icon-192.png")
    def icon_192():
        from fastapi.responses import Response
        return Response(content=render_pwa_icon_png("🎵", 192, _AUDIO_THEME), media_type="image/png")

    @app.get("/icon-512.png")
    def icon_512():
        from fastapi.responses import Response
        return Response(content=render_pwa_icon_png("🎵", 512, _AUDIO_THEME), media_type="image/png")

    return app

