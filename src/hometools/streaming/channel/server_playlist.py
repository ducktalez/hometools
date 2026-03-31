"""Playlist-based channel (TV) server — sequential playback from schedule.

Instead of the complex HLS concat-demuxer approach (``server_hls.py``), this
server resolves the daily schedule into a flat playlist of video files and
serves them using the **same** player UI as the video server.  The existing
auto-next logic (``player.addEventListener('ended', …)``) in
``server_utils.py`` automatically advances to the next item when playback
finishes — exactly like a real TV channel, just simpler and rock-solid.

Architecture
~~~~~~~~~~~~

1. On startup (and periodically), the schedule is resolved into an ordered
   list of :class:`~hometools.streaming.core.models.MediaItem` instances.
2. Fill-series episodes fill gaps between scheduled slots; scheduled-slot
   episodes appear at their designated position.
3. The ``/`` endpoint renders a standard ``render_media_page()`` shell.
4. ``/api/channel/items`` returns the playlist as JSON (same ``"items"`` key
   convention as audio/video servers).
5. ``/video/stream?path=…`` serves the actual video bytes (with on-the-fly
   remux for FLV / non-faststart MP4).
6. ``/api/channel/epg`` returns today's programme for display.
7. The player JS auto-advances to the next track when a video ends.

No ffmpeg background processes, no HLS segments, no race conditions.
"""

from __future__ import annotations

import contextlib
import json as _json
import logging
import mimetypes
import random
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from hometools.config import (
    get_cache_dir,
    get_channel_schedule_file,
    get_channel_state_dir,
    get_video_library_dir,
)
from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.channel.schedule import (
    get_display_schedule,
    get_fill_series,
    get_slots_for_date,
    list_episodes,
    parse_schedule_file,
    resolve_next_episode,
)
from hometools.streaming.core.models import MediaItem, normalize_relative_path
from hometools.streaming.core.server_utils import (
    check_library_accessible,
    render_error_page,
    render_media_page,
    resolve_media_path,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Playlist builder
# ---------------------------------------------------------------------------

_CHANNEL_STREAM_PREFIX = "/video/stream"
_CHANNEL_THUMB_PREFIX = "/thumb"


def _media_item_from_path(
    video_path: Path,
    library_dir: Path,
    *,
    series_folder: str = "",
    episode_label: str = "",
) -> MediaItem | None:
    """Create a :class:`MediaItem` from an absolute video file path."""
    try:
        rel = video_path.relative_to(library_dir)
    except ValueError:
        logger.warning("Video path %s is not inside library %s", video_path, library_dir)
        return None

    rel_posix = normalize_relative_path(rel)
    encoded = quote(rel_posix, safe="")
    title = episode_label or video_path.stem
    artist = series_folder or (rel.parts[0] if len(rel.parts) > 1 else "")

    return MediaItem(
        relative_path=rel_posix,
        title=title,
        artist=artist,
        stream_url=f"{_CHANNEL_STREAM_PREFIX}?path={encoded}",
        media_type="video",
        thumbnail_url=f"{_CHANNEL_THUMB_PREFIX}?path={encoded}",
        thumbnail_lg_url=f"{_CHANNEL_THUMB_PREFIX}?path={encoded}&size=lg",
    )


def build_channel_playlist(
    schedule_data: dict[str, Any],
    library_dir: Path,
    state_dir: Path,
    *,
    max_fill: int = 50,
) -> list[MediaItem]:
    """Build today's channel playlist from the schedule + fill series.

    The playlist is ordered:
    1. Fill episodes (random from ``fill_series``) fill the time before the
       first scheduled slot and between slots.
    2. Scheduled slot episodes appear at their designated positions.
    3. More fill episodes after the last scheduled slot.

    Returns a flat list of :class:`MediaItem` ready for the player UI.
    """
    now = datetime.now()
    items: list[MediaItem] = []

    # ── Scheduled slots for today ──
    slots = get_slots_for_date(schedule_data, now)
    scheduled_items: list[MediaItem] = []
    for slot in slots:
        episode = resolve_next_episode(
            library_dir,
            slot.series_folder,
            state_dir,
            slot.strategy,
        )
        if episode is None:
            continue
        mi = _media_item_from_path(
            episode,
            library_dir,
            series_folder=slot.series_folder,
            episode_label=episode.stem,
        )
        if mi is not None:
            scheduled_items.append(mi)

    # ── Fill series episodes ──
    fill_series = get_fill_series(schedule_data)
    fill_items: list[MediaItem] = []

    if fill_series:
        # Gather a pool of fill episodes
        fill_pool: list[Path] = []
        for series_name in fill_series:
            eps = list_episodes(library_dir, series_name)
            fill_pool.extend(eps)

        if fill_pool:
            random.shuffle(fill_pool)
            count = min(max_fill, len(fill_pool))
            for fp in fill_pool[:count]:
                series_name = ""
                with contextlib.suppress(ValueError, IndexError):
                    series_name = fp.relative_to(library_dir).parts[0]
                mi = _media_item_from_path(
                    fp,
                    library_dir,
                    series_folder=series_name,
                    episode_label=fp.stem,
                )
                if mi is not None:
                    fill_items.append(mi)

    # ── Interleave: fill → scheduled → fill → scheduled → fill ──
    # Split fill items roughly between the gaps
    if scheduled_items:
        n_gaps = len(scheduled_items) + 1
        chunk_size = max(1, len(fill_items) // n_gaps) if fill_items else 0
        fill_iter = iter(fill_items)

        for gap_idx in range(n_gaps):
            # Add a chunk of fill items
            for _ in range(chunk_size):
                try:
                    items.append(next(fill_iter))
                except StopIteration:
                    break
            # Add the scheduled item (except after the last gap)
            if gap_idx < len(scheduled_items):
                items.append(scheduled_items[gap_idx])

        # Append remaining fill items
        for remaining in fill_iter:
            items.append(remaining)
    else:
        # No scheduled slots — just play fill content
        items.extend(fill_items)

    if not items:
        logger.warning("Channel playlist is empty — no schedule slots or fill content found")

    logger.info(
        "Channel playlist built: %d items (%d scheduled, %d fill)",
        len(items),
        len(scheduled_items),
        len(fill_items),
    )
    return items


# ---------------------------------------------------------------------------
# CSS extra — channel purple/red theme
# ---------------------------------------------------------------------------

CHANNEL_CSS_EXTRA = """
:root { --accent: #f44336; }
.track-item.active .track-num::before { content: ''; color: var(--accent); }
.ctrl-btn.play-pause:hover { background: #ff6659; }
.folder-play-btn:hover { background: #ff6659; }
.back-btn:hover { color: #ff6659; }
.play-all-btn:hover { background: #ff6659; }
.view-toggle:hover { color: var(--accent); border-color: var(--accent); }
.breadcrumb a:hover { color: #ff6659; }
input[type=range]:hover::-webkit-slider-thumb { background: var(--accent); }
#player {
  width: 100%; max-height: 50vh; background: #000;
  border-top: 1px solid #333; flex-shrink: 0;
  display: none;
}
/* EPG section below the player */
.epg-section {
  max-width: 960px; margin: 0 auto; padding: 0.75rem 1rem;
}
.epg-title {
  font-size: 0.78rem; text-transform: uppercase; letter-spacing: .08em;
  color: #888; margin-bottom: 0.6rem;
}
.epg-list { list-style: none; padding: 0; margin: 0; }
.epg-item {
  display: flex; gap: 0.75rem; padding: 0.5rem 0;
  border-bottom: 1px solid #2a2a2a; font-size: 0.88rem;
}
.epg-time { color: #f44336; font-weight: 600; flex-shrink: 0; width: 50px; }
.epg-series { color: #e0e0e0; }
"""


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------


def create_app(
    library_dir: Path | None = None,
    *,
    schedule_file: Path | None = None,
) -> Any:
    """Create the FastAPI application for the playlist-based channel server."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_video_library_dir()).expanduser()
    resolved_schedule = (schedule_file or get_channel_schedule_file()).expanduser()
    resolved_state_dir = get_channel_state_dir()
    resolved_cache_dir = get_cache_dir()

    # Parse channel name
    channel_name = "Haus-TV"
    schedule_data: dict[str, Any] = {}
    try:
        schedule_data = parse_schedule_file(resolved_schedule)
        channel_name = str(schedule_data.get("channel_name", channel_name))
    except Exception:
        logger.error("Failed to parse channel schedule", exc_info=True)

    # Playlist state — rebuilt periodically in background
    _playlist_lock = threading.Lock()
    _playlist: list[MediaItem] = []
    _playlist_built_at: float = 0.0
    _PLAYLIST_TTL = 3600.0  # rebuild every hour

    def _rebuild_playlist() -> list[MediaItem]:
        """Rebuild the channel playlist from the schedule."""
        nonlocal _playlist, _playlist_built_at
        try:
            data = parse_schedule_file(resolved_schedule)
            new_list = build_channel_playlist(
                data,
                resolved_library_dir,
                resolved_state_dir,
            )
            with _playlist_lock:
                _playlist = new_list
                _playlist_built_at = time.monotonic()
            return new_list
        except Exception:
            logger.error("Failed to rebuild channel playlist", exc_info=True)
            return []

    def _get_playlist() -> list[MediaItem]:
        """Return current playlist, rebuilding if stale."""
        with _playlist_lock:
            age = time.monotonic() - _playlist_built_at
            if _playlist and age < _PLAYLIST_TTL:
                return list(_playlist)

        return _rebuild_playlist()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        startup_t0 = time.monotonic()
        logger.info(
            "Channel server (playlist) startup: library=%s schedule=%s",
            resolved_library_dir,
            resolved_schedule,
        )

        # Build initial playlist in background thread
        threading.Thread(
            target=_rebuild_playlist,
            daemon=True,
            name="channel-playlist-build",
        ).start()

        logger.info("Channel server startup complete in %.2fs", time.monotonic() - startup_t0)
        yield
        logger.info("Channel server shutdown complete")

    app = FastAPI(title=f"hometools channel — {channel_name}", lifespan=lifespan)

    # ── Health ──
    @app.get("/health")
    def health() -> dict[str, str]:
        ok, _msg = check_library_accessible(resolved_library_dir)
        return {
            "status": "ok" if ok else "degraded",
            "library_dir": str(resolved_library_dir),
            "schedule_file": str(resolved_schedule),
            "playlist_size": str(len(_playlist)),
        }

    # ── Main page ──
    @app.get("/", response_class=HTMLResponse)
    def channel_home() -> HTMLResponse:
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            return HTMLResponse(render_error_page(f"hometools — {channel_name}", "\U0001f4fa", msg, resolved_library_dir))

        items_json = _json.dumps([], ensure_ascii=False)
        page_html = render_media_page(
            title=f"hometools — {channel_name}",
            emoji="\U0001f4fa",
            items_json=items_json,
            media_element_tag="video",
            extra_css=CHANNEL_CSS_EXTRA,
            api_path="/api/channel/items",
            item_noun="video",
            theme_color="#f44336",
            player_bar_style="classic",
            safe_mode=False,
            enable_shuffle=False,
            enable_recent=False,
        )
        return HTMLResponse(page_html)

    # ── Playlist items API ──
    @app.get("/api/channel/items")
    def channel_items() -> dict[str, object]:
        playlist = _get_playlist()
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(playlist),
            "items": [item.to_dict() for item in playlist],
            "artists": sorted({item.artist for item in playlist if item.artist}),
        }

    # ── EPG (Electronic Program Guide) ──
    @app.get("/api/channel/epg")
    def channel_epg() -> dict[str, Any]:
        data = parse_schedule_file(resolved_schedule)
        return {"items": get_display_schedule(data)}

    # ── Now playing (based on playlist position — informational) ──
    @app.get("/api/channel/now")
    def channel_now() -> dict[str, Any]:
        playlist = _get_playlist()
        if not playlist:
            return {"series": "Sendepause", "episode": "", "is_filler": True}
        # Return the first item as a hint — the actual playback position
        # is tracked on the client side.
        first = playlist[0]
        return {
            "series": first.artist,
            "episode": first.title,
            "is_filler": False,
        }

    # ── Video streaming ──
    @app.get("/video/stream")
    def video_stream(path: str):
        from fastapi.responses import StreamingResponse

        from hometools.streaming.core.remux import has_faststart, needs_remux, remux_stream

        try:
            file_path = resolve_media_path(resolved_library_dir, path, VIDEO_SUFFIX)
        except FileNotFoundError as exc:
            logger.warning("GET /video/stream — not found: %s", path)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            logger.warning("GET /video/stream — invalid path: %s (%s)", path, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        do_remux = needs_remux(file_path)
        if not do_remux and not has_faststart(file_path):
            do_remux = True
            logger.info(
                "GET /video/stream — %s lacks fast-start, remuxing to fragmented MP4",
                file_path.name,
            )

        if do_remux:
            logger.info("GET /video/stream — remuxing %s for browser playback", file_path.name)
            return StreamingResponse(
                remux_stream(file_path),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="{file_path.stem}.mp4"',
                    "Cache-Control": "no-store",
                },
            )

        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    # ── Thumbnails ──
    @app.get("/thumb")
    def thumb(path: str, size: str = "sm") -> FileResponse:
        from urllib.parse import unquote

        from hometools.streaming.core.thumbnailer import get_thumbnail_lg_path, get_thumbnail_path

        relative_path = unquote(path)
        if size == "lg":
            thumb_path = get_thumbnail_lg_path(resolved_cache_dir, "video", relative_path)
        else:
            thumb_path = get_thumbnail_path(resolved_cache_dir, "video", relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    # ── Schedule raw data ──
    @app.get("/api/channel/schedule")
    def channel_schedule_raw() -> dict[str, Any]:
        data = parse_schedule_file(resolved_schedule)
        return {"schedule": data}

    # ── Metadata (single file re-read for player title/artist refresh) ──
    @app.get("/api/channel/metadata")
    def channel_metadata(path: str) -> dict[str, object]:
        try:
            file_path = resolve_media_path(resolved_library_dir, path, VIDEO_SUFFIX)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        title = file_path.stem
        artist = ""
        try:
            rel = file_path.relative_to(resolved_library_dir)
            if len(rel.parts) > 1:
                artist = rel.parts[0]
        except ValueError:
            pass
        return {"title": title, "artist": artist, "rating": 0.0}

    # ── Status endpoint (required by player JS polling) ──
    @app.get("/api/channel/status")
    def channel_status() -> dict[str, object]:
        return {
            "library_dir": str(resolved_library_dir),
            "detail": "ok",
            "count": len(_playlist),
        }

    # ── Rebuild playlist (manual trigger) ──
    @app.post("/api/channel/rebuild")
    def channel_rebuild() -> dict[str, object]:
        playlist = _rebuild_playlist()
        return {"ok": True, "count": len(playlist)}

    # ── Progress endpoints (reuse video progress store) ──
    @app.post("/api/channel/progress")
    def channel_save_progress(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.progress import save_progress

        rp = str(payload.get("relative_path") or "").strip()
        if not rp:
            raise HTTPException(status_code=400, detail="relative_path is required")
        pos = float(payload.get("position_seconds") or 0)
        dur = float(payload.get("duration") or 0)
        ok = save_progress(resolved_cache_dir, rp, pos, dur)
        return {"ok": ok}

    @app.get("/api/channel/progress")
    def channel_load_progress(path: str) -> dict[str, object]:
        from hometools.streaming.core.progress import load_progress

        entry = load_progress(resolved_cache_dir, path)
        return {"items": [entry] if entry else []}

    # ── PWA endpoints ──
    _CHANNEL_THEME = "#f44336"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse

        from hometools.streaming.core.server_utils import render_pwa_manifest

        return JSONResponse(
            content=_json.loads(
                render_pwa_manifest(
                    f"hometools — {channel_name}",
                    channel_name,
                    theme_color=_CHANNEL_THEME,
                    display_mode="minimal-ui",
                )
            ),
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        from fastapi.responses import Response

        from hometools.streaming.core.server_utils import render_pwa_service_worker

        return Response(content=render_pwa_service_worker(), media_type="application/javascript")

    @app.get("/icon.svg")
    def icon_svg():
        from fastapi.responses import Response

        from hometools.streaming.core.server_utils import render_pwa_icon_svg

        return Response(
            content=render_pwa_icon_svg("\U0001f4fa", _CHANNEL_THEME),
            media_type="image/svg+xml",
        )

    @app.get("/icon-192.png")
    def icon_192():
        from fastapi.responses import Response

        from hometools.streaming.core.server_utils import render_pwa_icon_png

        return Response(
            content=render_pwa_icon_png("\U0001f4fa", 192, _CHANNEL_THEME),
            media_type="image/png",
        )

    @app.get("/icon-512.png")
    def icon_512():
        from fastapi.responses import Response

        from hometools.streaming.core.server_utils import render_pwa_icon_png

        return Response(
            content=render_pwa_icon_png("\U0001f4fa", 512, _CHANNEL_THEME),
            media_type="image/png",
        )

    return app
