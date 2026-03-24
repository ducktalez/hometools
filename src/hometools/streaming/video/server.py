"""Minimal local web server for the video streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` — same dark-theme layout
as the audio server, but with a ``<video>`` element instead of ``<audio>``.
"""

from __future__ import annotations

import json as _json
import logging
import mimetypes
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from hometools.config import (
    get_cache_dir,
    get_player_bar_style,
    get_stream_index_cache_ttl,
    get_stream_safe_mode,
    get_video_library_dir,
    get_video_pwa_display_mode,
)
from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists, query_items, quick_folder_scan
from hometools.streaming.core.index_cache import IndexCache
from hometools.streaming.core.server_utils import (
    build_index_status_payload,
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

_video_index_cache = IndexCache(build_video_index, ttl=float(get_stream_index_cache_ttl()), label="video-index")

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
  display: none;
}
"""


def resolve_video_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested video file inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, VIDEO_SUFFIX)


def render_video_index_html(items, *, safe_mode: bool = False) -> str:
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
        player_bar_style="classic" if safe_mode else get_player_bar_style(),
        safe_mode=safe_mode,
    )


def create_app(library_dir: Path | None = None, *, safe_mode: bool | None = None) -> Any:
    """Create the FastAPI application for local video streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_video_library_dir()).expanduser()
    resolved_cache_dir = get_cache_dir()
    resolved_safe_mode = get_stream_safe_mode() if safe_mode is None else safe_mode

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        import asyncio

        startup_t0 = time.monotonic()
        logger.info("Video server startup: library=%s cache=%s", resolved_library_dir, resolved_cache_dir)
        check_t0 = time.monotonic()
        ok, msg = await asyncio.to_thread(check_library_accessible, resolved_library_dir)
        logger.info("Video startup library check finished in %.2fs: %s", time.monotonic() - check_t0, msg)
        if not ok:
            import logging

            logging.getLogger(__name__).warning("Video-Bibliothek: %s", msg)
        elif not resolved_safe_mode:
            cached = _video_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
            started_index_refresh = _video_index_cache.ensure_background_refresh(
                resolved_library_dir,
                cache_dir=resolved_cache_dir,
            )
            logger.info(
                "Video startup index state: cached_items=%d refresh_started=%s building=%s",
                len(cached),
                started_index_refresh,
                _video_index_cache.is_building(),
            )

            def _prepare_thumbnails() -> None:
                try:
                    collect_t0 = time.monotonic()
                    work = collect_thumbnail_work(resolved_library_dir, resolved_cache_dir)
                    collect_elapsed = time.monotonic() - collect_t0
                    started = start_background_thumbnail_generation(work)
                    logger.info(
                        "Video startup thumbnail work prepared: %d items in %.2fs (started=%s)",
                        len(work),
                        collect_elapsed,
                        started,
                    )
                except Exception:
                    logger.debug("Failed to start background video thumbnail generation", exc_info=True)

            threading.Thread(target=_prepare_thumbnails, daemon=True, name="video-thumb-bootstrap").start()
        else:
            logger.warning("Video server running in SAFE MODE — caches, PWA and thumbnail warmups are disabled")

        logger.info("Video server startup complete in %.2fs", time.monotonic() - startup_t0)
        yield

    app = FastAPI(title="hometools video streaming prototype", lifespan=lifespan)

    # Cache quick-scan results so repeated polls during index build don't
    # re-walk the filesystem every 2 seconds.
    _quick_cache: dict[str, object] = {"items": [], "at": 0.0}

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
        html = render_video_index_html([], safe_mode=resolved_safe_mode)
        elapsed = time.monotonic() - t0
        logger.info("GET / — shell rendered in %.2fs (HTML: %d bytes)", elapsed, len(html))
        return HTMLResponse(html)

    @app.get("/api/video/items")
    def video_items(q: str | None = None, artist: str | None = None, sort: str = "title") -> dict[str, object]:
        t0 = time.monotonic()
        logger.info("GET /api/video/items — start (q=%r, artist=%r, sort=%r)", q, artist, sort)
        if resolved_safe_mode:
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
            items = build_video_index(resolved_library_dir, cache_dir=None)
            filtered = query_items(items, q=q, artist=artist, sort_by=sort)
            logger.info(
                "GET /api/video/items — SAFE MODE returned %d/%d items in %.1fs",
                len(filtered),
                len(items),
                time.monotonic() - t0,
            )
            return {
                "library_dir": str(resolved_library_dir),
                "count": len(filtered),
                "items": [i.to_dict() for i in filtered],
                "artists": list_artists(items),
                "safe_mode": True,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        cache_t0 = time.monotonic()
        refresh_started = _video_index_cache.ensure_background_refresh(
            resolved_library_dir,
            cache_dir=resolved_cache_dir,
        )
        items = _video_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
        building = _video_index_cache.is_building()
        cache_elapsed = time.monotonic() - cache_t0
        if building and not items:
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
            cache_status = _video_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
            status_payload = build_index_status_payload(
                library_dir=resolved_library_dir,
                item_label="video",
                library_ok=True,
                library_message="ok",
                cache_status=cache_status,
            )
            # Reuse cached quick scan if available (avoid re-walking the
            # filesystem on every 2-second poll while the index builds).
            now = time.monotonic()
            if _quick_cache["items"] and (now - _quick_cache["at"]) < 30.0:
                quick_items = _quick_cache["items"]
                logger.debug("GET /api/video/items — reusing cached quick scan (%d items)", len(quick_items))
            else:
                quick_items = quick_folder_scan(
                    resolved_library_dir,
                    suffixes=VIDEO_SUFFIX,
                    media_type="video",
                    stream_url_prefix="/video/stream",
                )
                _quick_cache["items"] = quick_items
                _quick_cache["at"] = now
            filtered = query_items(quick_items, q=q, artist=artist, sort_by=sort)
            logger.info(
                "GET /api/video/items — quick scan %d items in %.2fs (refresh_started=%s, status=%s)",
                len(quick_items),
                time.monotonic() - cache_t0,
                refresh_started,
                status_payload["detail"],
            )
            return {
                "count": len(filtered),
                "items": [i.to_dict() for i in filtered],
                "artists": list_artists(quick_items),
                "refreshing": True,
                **status_payload,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        query_t0 = time.monotonic()
        filtered = query_items(items, q=q, artist=artist, sort_by=sort)
        query_elapsed = time.monotonic() - query_t0
        cache_status = _video_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
        elapsed = time.monotonic() - t0
        logger.info(
            "GET /api/video/items — %d/%d items in %.1fs (cache=%.2fs, query=%.2fs, refresh_started=%s, building=%s, q=%r, artist=%r, sort=%r)",
            len(filtered),
            len(items),
            elapsed,
            cache_elapsed,
            query_elapsed,
            refresh_started,
            building,
            q,
            artist,
            sort,
        )
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered),
            "items": [i.to_dict() for i in filtered],
            "artists": list_artists(items),
            "refreshing": building,
            "cache": cache_status,
            "query": {"q": q or "", "artist": artist or "all", "sort": sort},
        }

    @app.get("/api/video/status")
    def video_status() -> dict[str, object]:
        from hometools.streaming.core.issue_registry import summarize_issue_and_todos

        ok, msg = check_library_accessible(resolved_library_dir)
        cache_status = (
            {
                "label": "video-index",
                "building": False,
                "cached_count": 0,
                "fresh": False,
                "ttl_seconds": 0,
                "cache_age_seconds": None,
                "library_dir": str(resolved_library_dir),
                "snapshot_path": "",
                "snapshot_exists": False,
                "build_running_for_seconds": None,
                "last_build_started_at": None,
                "last_build_finished_at": None,
                "last_build_duration_seconds": None,
                "last_build_reason": "safe-mode",
                "last_error": "",
            }
            if resolved_safe_mode
            else _video_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
        )
        issue_todo_summary = summarize_issue_and_todos(resolved_cache_dir)
        payload = build_index_status_payload(
            library_dir=resolved_library_dir,
            item_label="video",
            library_ok=ok,
            library_message="Safe mode active — no cache snapshot or thumbnail warmup" if resolved_safe_mode else msg,
            cache_status=cache_status,
            issues_summary=issue_todo_summary["issues"],
            todo_summary=issue_todo_summary["todos"],
        )
        return payload

    @app.post("/api/video/todos/state")
    def video_todo_state(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.issue_registry import summarize_todos, update_todo_state_action

        todo_key = str(payload.get("todo_key") or "").strip()
        action = str(payload.get("action") or "").strip().lower()
        if not todo_key:
            raise HTTPException(status_code=400, detail="todo_key is required")
        if action not in {"acknowledge", "snooze", "clear"}:
            raise HTTPException(status_code=400, detail="action must be acknowledge, snooze or clear")

        result = update_todo_state_action(
            resolved_cache_dir,
            todo_key=todo_key,
            action=action,
            reason=str(payload.get("reason") or "").strip(),
            seconds=int(payload.get("seconds") or 3600),
        )
        if not bool(result.get("ok", False)):
            detail = str(result.get("message") or "Task state update failed")
            raise HTTPException(status_code=404 if result.get("state") == "missing" else 400, detail=detail)

        return {
            "ok": True,
            "result": result,
            "todos": summarize_todos(resolved_cache_dir),
        }

    @app.get("/api/video/metadata")
    def video_metadata(path: str) -> dict[str, object]:
        """Re-read embedded metadata for a single video file, with YAML overrides."""
        from hometools.audio.metadata import read_embedded_metadata
        from hometools.streaming.core.media_overrides import load_overrides
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
            meta_title = str(meta.get("title") or "")
            meta_artist = str(meta.get("artist") or "")
            if meta_title.strip():
                title = meta_title.strip()
            if meta_artist.strip():
                artist = meta_artist.strip()

        # Apply per-folder YAML overrides (same as build_video_index)
        folder = file_path.parent
        folder_ov = load_overrides(folder)
        if folder_ov is not None:
            if folder_ov.series_title:
                artist = folder_ov.series_title
            ep_ov = folder_ov.episodes.get(file_path.name)
            if ep_ov is not None and ep_ov.title is not None:
                title = ep_ov.title

        logger.debug("GET /api/video/metadata — %s → title=%r artist=%r", path, title, artist)
        return {"title": title, "artist": artist, "rating": 0.0}

    @app.post("/api/video/progress")
    def video_save_progress(payload: dict[str, object]) -> dict[str, object]:
        """Save playback progress for a video file."""
        from hometools.streaming.core.progress import save_progress

        rp = str(payload.get("relative_path") or "").strip()
        if not rp:
            raise HTTPException(status_code=400, detail="relative_path is required")
        pos = float(payload.get("position_seconds") or 0)
        dur = float(payload.get("duration") or 0)
        ok = save_progress(resolved_cache_dir, rp, pos, dur)
        return {"ok": ok}

    @app.get("/api/video/progress")
    def video_load_progress(path: str) -> dict[str, object]:
        """Load playback progress for a video file."""
        from hometools.streaming.core.progress import load_progress

        entry = load_progress(resolved_cache_dir, path)
        return {"items": [entry] if entry else []}

    @app.get("/video/stream")
    def video_stream(path: str):
        from fastapi.responses import StreamingResponse

        from hometools.streaming.core.remux import has_faststart, needs_remux, remux_stream

        try:
            file_path = resolve_video_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            logger.warning("GET /video/stream — not found: %s", path)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            logger.warning("GET /video/stream — invalid path: %s (%s)", path, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        do_remux = needs_remux(file_path)

        if not do_remux and not has_faststart(file_path):
            # MP4 with moov atom at end — browser can't start playback
            # until the entire file is downloaded.  Remux to fragmented
            # MP4 so playback begins immediately.
            do_remux = True
            logger.info(
                "GET /video/stream — %s lacks fast-start (moov at end), remuxing to fragmented MP4",
                file_path.name,
            )

        if do_remux:
            # On-the-fly remux/transcode to fragmented MP4 (like Jellyfin)
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
        logger.debug("GET /video/stream — serving %s (%s)", file_path.name, media_type)
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    @app.get("/thumb")
    def thumb(path: str, size: str = "sm") -> FileResponse:
        """Serve a cached thumbnail image for a video file.

        Pass ``?size=lg`` for the large (480 px) variant,
        or ``?size=sprite`` for the sprite sheet image.
        """
        from urllib.parse import unquote

        relative_path = unquote(path)
        if size == "lg":
            from hometools.streaming.core.thumbnailer import get_thumbnail_lg_path

            thumb_path = get_thumbnail_lg_path(resolved_cache_dir, "video", relative_path)
        elif size == "sprite":
            from hometools.streaming.core.thumbnailer import get_sprite_path

            thumb_path = get_sprite_path(resolved_cache_dir, relative_path)
        else:
            thumb_path = get_thumbnail_path(resolved_cache_dir, "video", relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    @app.get("/api/video/sprites")
    def video_sprites(path: str) -> dict[str, object]:
        """Return sprite sheet metadata for a video file (or 404)."""
        from urllib.parse import unquote

        from hometools.streaming.core.thumbnailer import get_sprite_meta_path

        relative_path = unquote(path)
        meta_path = get_sprite_meta_path(resolved_cache_dir, relative_path)
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="Sprite sheet not generated yet")
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
            return {"ok": True, **meta}
        except Exception:
            raise HTTPException(status_code=500, detail="Sprite metadata corrupted") from None

    # --- Shortcuts API ---

    @app.get("/api/video/shortcuts")
    def video_shortcuts() -> dict[str, object]:
        """Return saved PWA shortcuts for the video server."""
        from hometools.streaming.core.shortcuts import load_shortcuts

        return {"items": load_shortcuts(resolved_cache_dir, "video")}

    @app.post("/api/video/shortcuts")
    def video_add_shortcut(payload: dict[str, str]) -> dict[str, object]:
        """Add or update a PWA shortcut."""
        from hometools.streaming.core.shortcuts import save_shortcut

        item_id = payload.get("id", "")
        title = payload.get("title", "")
        if not item_id or not title:
            raise HTTPException(status_code=400, detail="id and title are required")
        url = f"/?id={item_id}"
        icon = payload.get("icon", f"/thumb?path={item_id}")
        shortcuts = save_shortcut(resolved_cache_dir, "video", item_id=item_id, title=title, url=url, icon=icon)
        return {"items": shortcuts}

    @app.delete("/api/video/shortcuts")
    def video_remove_shortcut(id: str) -> dict[str, object]:
        """Remove a PWA shortcut by item id."""
        from hometools.streaming.core.shortcuts import remove_shortcut

        shortcuts = remove_shortcut(resolved_cache_dir, "video", id)
        return {"items": shortcuts}

    # --- Audit log endpoints (read-only for video — no write ops yet) ---

    @app.get("/api/video/recent")
    def video_recent(limit: int | None = None) -> dict[str, object]:
        """Return recently watched video episodes for the start-screen suggestions.

        Filters applied (all configurable via env vars):
        - ``HOMETOOLS_RECENT_VIDEO_LIMIT``  — max items to show (default 3)
        - ``HOMETOOLS_RECENT_MAX_AGE_DAYS`` — max age in days (default 14)
        - ``HOMETOOLS_RECENT_MAX_PER_SERIES`` — max episodes per series (default 1,
          only the most-recently-seen episode per series is kept)
        """
        import dataclasses
        import time

        from hometools.config import get_recent_max_age_days, get_recent_max_per_series, get_recent_video_limit
        from hometools.streaming.core.progress import get_recent_progress

        effective_limit = get_recent_video_limit() if limit is None else max(1, min(int(limit), 50))
        max_age_days = get_recent_max_age_days()
        max_per_series = get_recent_max_per_series()
        cutoff_ts = time.time() - max_age_days * 86400

        # Fetch a generous pool from storage; we'll filter down
        recent = get_recent_progress(resolved_cache_dir, limit=effective_limit * 10)

        cached = _video_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
        catalog_by_path: dict[str, object] = {item.relative_path: item for item in cached}

        result = []
        series_count: dict[str, int] = {}  # artist (series folder) → how many episodes kept

        for entry in recent:
            path = entry.get("relative_path", "")
            item = catalog_by_path.get(path)
            if item is None:
                continue

            # Age filter
            ts = float(entry.get("timestamp", 0))
            if ts < cutoff_ts:
                continue

            # Per-series cap (artist = top-level folder = series name for video)
            series_key = item.artist or ""
            if series_count.get(series_key, 0) >= max_per_series:
                continue

            pos = float(entry.get("position_seconds", 0))
            dur = float(entry.get("duration", 0))
            pct = round(pos / dur * 100) if dur > 0 else 0
            d = dataclasses.asdict(item)
            d.update(
                position_seconds=pos,
                duration=dur,
                progress_pct=pct,
                timestamp=ts,
            )
            result.append(d)
            series_count[series_key] = series_count.get(series_key, 0) + 1

            if len(result) >= effective_limit:
                break

        return {"items": result}

    @app.get("/api/video/audit")
    def video_audit_entries(
        limit: int = 200,
        path_filter: str = "",
        action_filter: str = "",
        include_undone: bool = True,
    ) -> dict[str, object]:
        """Return audit log entries visible to the video server (shared cache)."""
        from hometools.streaming.core.audit_log import load_entries

        entries = load_entries(
            resolved_cache_dir,
            limit=limit,
            path_filter=path_filter,
            action_filter=action_filter,
            include_undone=include_undone,
        )
        return {"items": entries, "total": len(entries)}

    @app.post("/api/video/audit/undo")
    def video_audit_undo(payload: dict[str, object]) -> dict[str, object]:
        """Undo not supported on the video server (no write operations yet)."""
        raise HTTPException(status_code=422, detail="No undoable actions on the video server yet")

    @app.get("/audit")
    def video_audit_panel() -> HTMLResponse:
        """Serve the dark-theme Audit / Control-Panel HTML page."""
        from fastapi.responses import HTMLResponse

        from hometools.streaming.core.server_utils import render_audit_panel_html

        return HTMLResponse(
            render_audit_panel_html(
                server="hometools video",
                media_type="video",
                title="Audit-Log — hometools video",
            )
        )

    # --- PWA endpoints ---
    _VIDEO_THEME = "#bb86fc"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse

        from hometools.streaming.core.shortcuts import load_shortcuts

        saved = load_shortcuts(resolved_cache_dir, "video")
        pwa_shortcuts = [
            {
                "name": s["title"],
                "short_name": s["title"][:25],
                "url": s.get("url", f"/?id={s['id']}"),
                "icons": [{"src": s.get("icon", "/icon.svg"), "sizes": "any"}],
            }
            for s in saved
        ]
        return JSONResponse(
            content=_json.loads(
                render_pwa_manifest(
                    "hometools video",
                    "Video",
                    theme_color=_VIDEO_THEME,
                    display_mode=get_video_pwa_display_mode(),
                    shortcuts=pwa_shortcuts or None,
                )
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
