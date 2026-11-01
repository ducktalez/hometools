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
    get_audit_dir,
    get_cache_dir,
    get_player_bar_style,
    get_stream_index_cache_ttl,
    get_stream_safe_mode,
    get_video_library_dir,
    get_video_pwa_display_mode,
)
from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists, query_items
from hometools.streaming.core.index_cache import IndexCache
from hometools.streaming.core.openapi_schema import install_filtered_openapi
from hometools.streaming.core.server_factory import (
    register_audit_entries_route,
    register_delete_file_route,
    register_folder_order_routes,
    register_health_route,
    register_index_routes,
    register_playlist_routes,
    register_progress_routes,
    register_pwa_routes,
    register_reveal_route,
    register_shortcuts_routes,
    register_thumb_route,
    register_todo_state_route,
)
from hometools.streaming.core.server_utils import (
    check_library_accessible,
    mount_static_assets,
    render_error_page,
    render_media_page,
    resolve_media_path,
)
from hometools.streaming.core.thumbnailer import start_background_thumbnail_generation
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
"""


def resolve_video_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested video file inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, VIDEO_SUFFIX)


def render_video_index_html(items, *, safe_mode: bool = False, language_groups_json: str = "{}") -> str:
    """Render the video player UI — dark theme, folder grid, inline video element."""
    from hometools.config import get_debug_filter, get_default_language, get_min_rating, get_playlist_sync_interval

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
        enable_repeat=True,
        enable_playlists=True,
        playlist_sync_interval_ms=get_playlist_sync_interval() * 1000,
        min_rating=get_min_rating(),
        debug_filter=get_debug_filter(),
        language_groups_json=language_groups_json,
        default_language=get_default_language(),
    )


def create_app(
    library_dir: Path | None = None,
    *,
    safe_mode: bool | None = None,
    cache_dir: Path | None = None,
    audit_dir: Path | None = None,
) -> Any:
    """Create the FastAPI application for local video streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_video_library_dir()).expanduser()
    resolved_cache_dir = cache_dir or get_cache_dir()
    resolved_audit_dir = audit_dir or get_audit_dir()
    resolved_safe_mode = get_stream_safe_mode() if safe_mode is None else safe_mode

    # Language group mapping for multi-language linking.
    # Loaded in a background thread because load_language_groups scans the
    # filesystem with rglob() which is slow on NAS/UNC paths and must never
    # block server startup.
    _lang_state: dict[str, str] = {"json": "{}"}

    def _load_language_groups_bg() -> None:
        try:
            ok, msg = check_library_accessible(resolved_library_dir)
            if not ok:
                logger.info("Skipping language group scan — library not accessible: %s", msg)
                return
            from hometools.streaming.core.media_overrides import load_language_groups

            groups = load_language_groups(resolved_library_dir)
            _lang_state["json"] = _json.dumps(groups, ensure_ascii=False)
            logger.info("Language groups loaded: %d entries", len(groups))
        except Exception:
            logger.debug("Failed to load language groups", exc_info=True)

    threading.Thread(target=_load_language_groups_bg, daemon=True, name="video-lang-groups").start()

    # One-time migration: copy legacy audit log from cache dir to dedicated audit dir
    from hometools.streaming.core.audit_log import _migrate_from_cache

    _migrate_from_cache(resolved_audit_dir, resolved_cache_dir)

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

            def _prepare_intro_markers() -> None:
                from hometools.config import get_intro_autodetect_enabled

                if not get_intro_autodetect_enabled():
                    return
                try:
                    from hometools.streaming.core.intro_markers import start_background_intro_detection
                    from hometools.streaming.video.catalog import collect_intro_detection_work

                    work = collect_intro_detection_work(resolved_library_dir)
                    started = start_background_intro_detection(work, resolved_cache_dir, "video")
                    logger.info(
                        "Video startup intro auto-detection prepared: %d files (started=%s)",
                        len(work),
                        started,
                    )
                except Exception:
                    logger.debug("Failed to start background intro detection", exc_info=True)

            threading.Thread(target=_prepare_intro_markers, daemon=True, name="video-intro-bootstrap").start()

            def _sweep_stale_remux_tmp() -> None:
                try:
                    from hometools.streaming.core.remux import cleanup_stale_remux_tmp

                    cleanup_stale_remux_tmp(resolved_cache_dir)
                except Exception:
                    logger.debug("Failed to sweep stale remux temp files", exc_info=True)

            threading.Thread(target=_sweep_stale_remux_tmp, daemon=True, name="video-remux-tmp-sweep").start()

            def _prepare_remux() -> None:
                from hometools.config import get_pretranscode_enabled

                if not get_pretranscode_enabled():
                    return
                try:
                    from hometools.streaming.core.remux import start_background_remux_generation
                    from hometools.streaming.video.catalog import collect_remux_work

                    work = collect_remux_work(resolved_library_dir, resolved_cache_dir)
                    started = start_background_remux_generation(work)
                    logger.info(
                        "Video startup pre-transcode prepared: %d non-native files (started=%s)",
                        len(work),
                        started,
                    )
                except Exception:
                    logger.debug("Failed to start background pre-transcode", exc_info=True)

            threading.Thread(target=_prepare_remux, daemon=True, name="video-remux-bootstrap").start()
        else:
            logger.warning("Video server running in SAFE MODE — caches, PWA and thumbnail warmups are disabled")

        logger.info("Video server startup complete in %.2fs", time.monotonic() - startup_t0)
        yield

    app = FastAPI(title="hometools video streaming prototype", lifespan=lifespan)
    # Serve a JSON-API-only OpenAPI schema so /openapi.json + /docs work in the
    # browser (HTML/binary routes would otherwise break FastAPI's schema builder).
    install_filtered_openapi(app)
    # Vite/TS migration Phase 4 (docs/IMPLEMENTATION_PLAN.md): serve the built
    # webui bundle at /static if present. No-op (logs a warning) when the
    # bundle hasn't been built yet — never blocks/crashes startup.
    mount_static_assets(app)

    # Cache quick-scan results so repeated polls during index build don't
    # re-walk the filesystem every 2 seconds.
    _quick_cache: dict[str, object] = {"items": [], "at": 0.0}

    @app.get("/", response_class=HTMLResponse)
    def video_home() -> HTMLResponse:
        t0 = time.monotonic()
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            logger.warning("GET / — library not accessible: %s", msg)
            return HTMLResponse(render_error_page("hometools video", "🎬", msg, resolved_library_dir))
        html = render_video_index_html([], safe_mode=resolved_safe_mode, language_groups_json=_lang_state["json"])
        elapsed = time.monotonic() - t0
        logger.info("GET / — shell rendered in %.2fs (HTML: %d bytes)", elapsed, len(html))
        return HTMLResponse(html)

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

    @app.get("/api/video/continue")
    def video_continue_watching(limit: int = 20) -> dict[str, object]:
        """Return unfinished, recently-played videos for a "Continue Watching" row.

        Joins the playback-progress store with the current catalog so each
        entry carries full item metadata (title, artist, thumbnail, stream URL,
        intro markers) plus the resume position. Built for the native TV client
        (10-foot UI), but generic enough for any consumer. Never 500s — returns
        ``{"items": []}`` when the catalog isn't ready or on any error.
        """
        from hometools.streaming.core.progress import get_continue_watching

        try:
            entries = get_continue_watching(resolved_cache_dir, limit=max(1, min(int(limit), 100)))
        except Exception:
            logger.debug("GET /api/video/continue — failed to read progress", exc_info=True)
            return {"items": []}

        if not entries:
            return {"items": []}

        if resolved_safe_mode:
            items = build_video_index(resolved_library_dir, cache_dir=None)
        else:
            items = _video_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
        by_path = {it.relative_path: it for it in (items or [])}

        result: list[dict[str, object]] = []
        for entry in entries:
            rp = str(entry.get("relative_path") or "")
            item = by_path.get(rp)
            if item is None:
                continue  # progress for a file no longer in the catalog
            merged = item.to_dict()
            merged["position_seconds"] = entry.get("position_seconds", 0.0)
            merged["resume_duration"] = entry.get("duration", 0.0)
            merged["last_played"] = entry.get("timestamp", 0.0)
            result.append(merged)

        logger.info("GET /api/video/continue — %d resumable item(s)", len(result))
        return {"items": result}

    @app.get("/video/stream")
    def video_stream(path: str):
        from fastapi.responses import StreamingResponse

        from hometools.streaming.core.remux import (
            can_copy_codecs,
            ensure_faststart_cache,
            ensure_remux_cache,
            get_faststart_cache_path,
            get_remux_cache_path,
            has_faststart,
            needs_remux,
            remux_stream,
            start_background_remux,
        )

        try:
            file_path = resolve_video_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            logger.warning("GET /video/stream — not found: %s", path)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            logger.warning("GET /video/stream — invalid path: %s (%s)", path, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # --- MP4 without faststart → serve cached faststart copy (iOS-safe) ---
        # iOS Safari requires proper HTTP Range request support to even start
        # playback. FastAPI's FileResponse handles this natively; StreamingResponse
        # does not.  For MP4 files whose moov atom sits at the end we create a
        # faststart copy in the shadow cache (ffmpeg -c copy, no re-encoding)
        # and serve that via FileResponse.  Extra cost is paid once; subsequent
        # requests are cache hits served instantly.
        if not needs_remux(file_path) and not has_faststart(file_path):
            logger.info(
                "GET /video/stream — %s lacks fast-start, using shadow-cache faststart copy",
                file_path.name,
            )
            relative_path = str(file_path.relative_to(resolved_library_dir)).replace("\\", "/")
            # Check if cache already exists (fast path, no ffmpeg spawn)
            cached = get_faststart_cache_path(resolved_cache_dir, relative_path)
            if not cached.exists() or cached.stat().st_mtime < file_path.stat().st_mtime:
                # Build synchronously — ffmpeg -c copy is fast (seconds, not minutes)
                cached = ensure_faststart_cache(file_path, resolved_cache_dir, relative_path)
            if cached is not None and cached.exists():
                logger.debug("GET /video/stream — serving faststart cache: %s", cached.name)
                return FileResponse(cached, media_type="video/mp4", filename=file_path.name)
            # Faststart cache failed → fall through to legacy remux (no Range support, but better than 500)
            logger.warning(
                "GET /video/stream — faststart cache failed for %s, falling back to StreamingResponse",
                file_path.name,
            )
            return StreamingResponse(
                remux_stream(file_path),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="{file_path.stem}.mp4"',
                    "Cache-Control": "no-store",
                },
            )

        # --- Non-native container (MKV, AVI, …) or codec incompatibility ---
        if needs_remux(file_path):
            relative_path = str(file_path.relative_to(resolved_library_dir)).replace("\\", "/")

            # Preferred path: serve a cached, fast-start MP4 copy via FileResponse.
            # FileResponse supports HTTP Range/206 requests — REQUIRED by iOS
            # Safari and most mobile browsers.  The legacy StreamingResponse
            # remux pipe below cannot serve Range, which is why .avi episodes
            # failed to load on phones while native MP4s worked.
            cached = get_remux_cache_path(resolved_cache_dir, relative_path)
            try:
                cache_fresh = cached.exists() and cached.stat().st_mtime >= file_path.stat().st_mtime
            except OSError:
                cache_fresh = False
            if cache_fresh:
                logger.debug("GET /video/stream — serving cached remux: %s", cached.name)
                return FileResponse(cached, media_type="video/mp4", filename=file_path.stem + ".mp4")

            # No cache yet.  If the codecs are already browser-compatible we can
            # build it synchronously with `-c copy` (a few seconds) and serve
            # the Range-capable file straight away.
            copyable = can_copy_codecs(file_path)
            if copyable:
                logger.info("GET /video/stream — building copy-remux cache for %s", file_path.name)
                out = ensure_remux_cache(file_path, resolved_cache_dir, relative_path, copy=True)
                if out is not None and out.exists():
                    return FileResponse(out, media_type="video/mp4", filename=file_path.stem + ".mp4")

            # Full transcode needed (e.g. XviD .avi): too slow to block the
            # request.  Kick off a background transcode so the next attempt is
            # served from the Range-capable cache, and fall back to the live
            # remux pipe for this request (works on desktop; mobile should
            # retry once the cache is ready).
            start_background_remux(file_path, resolved_cache_dir, relative_path, copy=False if not copyable else None)
            logger.info(
                "GET /video/stream — remuxing %s live (cache warming in background)",
                file_path.name,
            )
            return StreamingResponse(
                remux_stream(file_path),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="{file_path.stem}.mp4"',
                    "Cache-Control": "no-store",
                },
            )

        # --- Native MP4/WebM with faststart → serve directly (Range-aware) ---
        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        logger.debug("GET /video/stream — serving %s (%s)", file_path.name, media_type)
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

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

    # --- Skip-Intro markers API ---

    @app.get("/api/video/intro")
    def video_get_intro(path: str) -> dict[str, object]:
        """Return the stored skip-intro marker for a video (or empty)."""
        from hometools.streaming.core.intro_markers import get_marker

        marker = get_marker(resolved_cache_dir, "video", path)
        return {"marker": marker}

    @app.post("/api/video/intro")
    def video_set_intro(payload: dict[str, object]) -> dict[str, object]:
        """Persist a manual skip-intro marker.

        Body: ``{"path": "Series/S01E01.mp4", "start": 0, "end": 92}``.
        Patches the in-memory catalog so the marker takes effect immediately.
        """
        from hometools.streaming.core.intro_markers import set_marker

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        try:
            start = float(payload.get("start") or 0.0)
            end = float(payload.get("end") or 0.0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="start and end must be numbers") from exc

        marker = set_marker(resolved_cache_dir, "video", path, start=start, end=end, source="manual")
        if marker is None:
            raise HTTPException(status_code=400, detail="Could not store marker")

        # Reflect the change in the live catalog without a full rebuild.
        if not resolved_safe_mode:
            _video_index_cache.patch_items({path: {"intro_start": marker["start"], "intro_end": marker["end"]}})

        return {"ok": True, "marker": marker}

    @app.delete("/api/video/intro")
    def video_delete_intro(path: str) -> dict[str, object]:
        """Delete the stored skip-intro marker for a video."""
        from hometools.streaming.core.intro_markers import delete_marker

        ok = delete_marker(resolved_cache_dir, "video", path)
        if ok and not resolved_safe_mode:
            _video_index_cache.patch_items({path: {"intro_start": 0.0, "intro_end": 0.0}})
        return {"deleted": ok}

    # --- File delete (soft-delete for duplicates) ---

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

        effective_limit = get_recent_video_limit() if limit is None else max(1, min(int(limit), 200))
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

    # --- Tasks board (missing episodes + library hints) ---

    @app.get("/api/video/board")
    def video_board() -> dict[str, object]:
        """Return board data: missing individual episodes + library hints.

        ``missing_episodes`` is computed from the in-memory catalog (instant).
        ``issues`` come from a best-effort filesystem scan and are exception-safe.
        """
        from hometools.streaming.core.episode_gaps import find_missing_episodes

        if resolved_safe_mode:
            items = build_video_index(resolved_library_dir, cache_dir=None)
        else:
            _video_index_cache.ensure_background_refresh(resolved_library_dir, cache_dir=resolved_cache_dir)
            items = _video_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)

        gaps = find_missing_episodes(items)

        issues: list[dict[str, object]] = []
        try:
            from hometools.streaming.core.library_scan import scan_video_library

            report = scan_video_library(resolved_library_dir)
            issues = report.to_dict().get("issues", [])
        except Exception:
            logger.debug("GET /api/video/board — library scan failed", exc_info=True)

        return {
            "missing_episodes": [g.to_dict() for g in gaps],
            "missing_count": sum(len(g.missing_episodes) for g in gaps),
            "issues": issues,
        }

    @app.get("/board")
    def video_board_page() -> HTMLResponse:
        """Serve the dark-theme tasks board HTML page."""
        from fastapi.responses import HTMLResponse

        from hometools.streaming.core.server_utils import render_board_page_html

        return HTMLResponse(
            render_board_page_html(
                server="hometools video",
                media_type="video",
                title="Aufgaben-Board — hometools video",
            )
        )

    # --- Shared endpoints (core/server_factory.py) ---
    register_health_route(app, resolved_library_dir)
    register_index_routes(
        app,
        library_dir=resolved_library_dir,
        cache_dir=resolved_cache_dir,
        safe_mode=resolved_safe_mode,
        media_type="video",
        api_path="/api/video/items",
        items_name="items",
        default_sort="title",
        suffixes=VIDEO_SUFFIX,
        stream_url_prefix="/video/stream",
        index_cache=_video_index_cache,
        build_index=build_video_index,
        query_fn=query_items,
        list_artists_fn=list_artists,
    )
    register_thumb_route(app, resolved_cache_dir, "video", allow_sprite=True)
    register_todo_state_route(app, resolved_cache_dir, "video")
    register_audit_entries_route(app, resolved_audit_dir, "video")
    register_reveal_route(app, resolved_library_dir, "video", resolve_video_path)
    register_delete_file_route(app, resolved_library_dir, resolved_audit_dir, "video", resolve_video_path, _video_index_cache.invalidate)
    register_progress_routes(app, resolved_cache_dir, "video")
    register_playlist_routes(app, resolved_cache_dir, "video")
    register_folder_order_routes(app, resolved_cache_dir, "video")
    register_shortcuts_routes(app, resolved_cache_dir, "video")
    register_pwa_routes(
        app,
        cache_dir=resolved_cache_dir,
        media_type="video",
        app_name="hometools video",
        short_name="Video",
        emoji="??",
        theme_color="#bb86fc",
        display_mode=get_video_pwa_display_mode(),
    )

    return app
