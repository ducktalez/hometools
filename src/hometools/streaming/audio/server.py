"""Minimal local web server for the audio streaming prototype.

Uses :mod:`hometools.streaming.core.server_utils` for shared UI rendering
so that the video server can reuse the same dark-theme layout.
"""

from __future__ import annotations

import json as _json
import logging
import mimetypes
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hometools.audio.sanitize import split_stem
from hometools.config import (
    get_audio_library_dir,
    get_audit_dir,
    get_cache_dir,
    get_player_bar_style,
    get_stream_index_cache_ttl,
    get_stream_safe_mode,
)
from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    collect_thumbnail_work,
    list_artists,
    query_tracks,
)
from hometools.streaming.core.catalog import quick_folder_scan
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

_audio_index_cache = IndexCache(build_audio_index, ttl=float(get_stream_index_cache_ttl()), label="audio-index")

AUDIO_CSS_EXTRA = """
.track-item.active .track-num::before { content: '♪'; color: var(--accent); }
#player { display: none; }
"""

logger = logging.getLogger(__name__)


def resolve_audio_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested audio track inside the library root."""
    return resolve_media_path(library_dir, encoded_relative_path, AUDIO_SUFFIX)


def render_audio_index_html(tracks: list[AudioTrack], *, safe_mode: bool = False) -> str:
    """Render the audio player UI — dark theme, folder grid, player."""
    from hometools.config import get_crossfade_duration, get_debug_filter, get_min_rating, get_playlist_sync_interval

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
        player_bar_style="classic" if safe_mode else get_player_bar_style(),
        safe_mode=safe_mode,
        enable_shuffle=True,
        enable_rating_write=True,
        enable_metadata_edit=True,
        enable_recent=False,  # Audio: no "recently played" section; audiobooks resume via progress API
        enable_auto_resume=False,  # Audio: don't auto-seek to last position (songs, not audiobooks)
        enable_lyrics=True,
        enable_playlists=True,
        playlist_sync_interval_ms=get_playlist_sync_interval() * 1000,
        min_rating=get_min_rating(),
        crossfade_duration=get_crossfade_duration(),
        debug_filter=get_debug_filter(),
    )


# ---------------------------------------------------------------------------
# Rating refresh log — persistent record of per-folder refresh timestamps
# ---------------------------------------------------------------------------

_REFRESH_LOG_FILENAME = "rating_refresh_log.json"


def _read_refresh_log(cache_dir: Path) -> dict[str, object]:
    """Load the refresh log from disk.  Returns ``{}`` on any failure."""
    try:
        log_path = cache_dir / _REFRESH_LOG_FILENAME
        if log_path.exists():
            return _json.loads(log_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Could not read refresh log", exc_info=True)
    return {}


def _update_refresh_log(
    cache_dir: Path,
    folder: str,
    total: int,
    changed: int,
) -> str:
    """Record a rating-refresh event for *folder* and return the ISO timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        log = _read_refresh_log(cache_dir)
        log[folder] = {
            "last_refresh": now,
            "total": total,
            "changed": changed,
        }
        log_path = cache_dir / _REFRESH_LOG_FILENAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Could not write refresh log", exc_info=True)
    return now


def create_app(
    library_dir: Path | None = None,
    *,
    safe_mode: bool | None = None,
    cache_dir: Path | None = None,
) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    resolved_cache_dir = cache_dir or get_cache_dir()
    resolved_audit_dir = get_audit_dir()
    resolved_safe_mode = get_stream_safe_mode() if safe_mode is None else safe_mode

    # One-time migration: copy legacy audit log from cache dir to dedicated audit dir
    from hometools.streaming.core.audit_log import _migrate_from_cache

    _migrate_from_cache(resolved_audit_dir, resolved_cache_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        import asyncio

        startup_t0 = time.monotonic()
        logger.info("Audio server startup: library=%s cache=%s", resolved_library_dir, resolved_cache_dir)
        check_t0 = time.monotonic()
        ok, msg = await asyncio.to_thread(check_library_accessible, resolved_library_dir)
        logger.info("Audio startup library check finished in %.2fs: %s", time.monotonic() - check_t0, msg)
        if not ok:
            import logging

            logging.getLogger(__name__).warning("Audio-Bibliothek: %s", msg)
        elif not resolved_safe_mode:
            cached = _audio_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
            started_index_refresh = _audio_index_cache.ensure_background_refresh(
                resolved_library_dir,
                cache_dir=resolved_cache_dir,
            )
            logger.info(
                "Audio startup index state: cached_items=%d refresh_started=%s building=%s",
                len(cached),
                started_index_refresh,
                _audio_index_cache.is_building(),
            )

            def _prepare_thumbnails() -> None:
                try:
                    collect_t0 = time.monotonic()
                    work = collect_thumbnail_work(resolved_library_dir, resolved_cache_dir)
                    collect_elapsed = time.monotonic() - collect_t0
                    started = start_background_thumbnail_generation(work)
                    logger.info(
                        "Audio startup thumbnail work prepared: %d items in %.2fs (started=%s)",
                        len(work),
                        collect_elapsed,
                        started,
                    )
                except Exception:
                    logger.debug("Failed to start background audio thumbnail generation", exc_info=True)

            threading.Thread(target=_prepare_thumbnails, daemon=True, name="audio-thumb-bootstrap").start()
        else:
            logger.warning("Audio server running in SAFE MODE — caches, PWA and thumbnail warmups are disabled")

        logger.info("Audio server startup complete in %.2fs", time.monotonic() - startup_t0)
        yield

    app = FastAPI(title="hometools audio streaming prototype", lifespan=lifespan)

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
    def audio_home() -> HTMLResponse:
        t0 = time.monotonic()
        ok, msg = check_library_accessible(resolved_library_dir)
        if not ok:
            logger.warning("GET / — library not accessible: %s", msg)
            return HTMLResponse(render_error_page("hometools audio", "🎵", msg, resolved_library_dir))
        html = render_audio_index_html([], safe_mode=resolved_safe_mode)
        elapsed = time.monotonic() - t0
        logger.info("GET / — shell rendered in %.2fs", elapsed)
        return HTMLResponse(html)

    @app.get("/api/audio/tracks")
    def audio_tracks(q: str | None = None, artist: str | None = None, sort: str = "artist") -> dict[str, object]:
        t0 = time.monotonic()
        logger.info("GET /api/audio/tracks — start (q=%r, artist=%r, sort=%r)", q, artist, sort)
        if resolved_safe_mode:
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
            tracks = build_audio_index(resolved_library_dir, cache_dir=None)
            filtered = query_tracks(tracks, q=q, artist=artist, sort_by=sort)
            logger.info(
                "GET /api/audio/tracks — SAFE MODE returned %d/%d items in %.1fs",
                len(filtered),
                len(tracks),
                time.monotonic() - t0,
            )
            return {
                "library_dir": str(resolved_library_dir),
                "count": len(filtered),
                "items": [t.to_dict() for t in filtered],
                "artists": list_artists(tracks),
                "safe_mode": True,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        cache_t0 = time.monotonic()
        refresh_started = _audio_index_cache.ensure_background_refresh(
            resolved_library_dir,
            cache_dir=resolved_cache_dir,
        )
        tracks = _audio_index_cache.get_cached(resolved_library_dir, cache_dir=resolved_cache_dir)
        building = _audio_index_cache.is_building()
        cache_elapsed = time.monotonic() - cache_t0
        if building and not tracks:
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
            cache_status = _audio_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
            status_payload = build_index_status_payload(
                library_dir=resolved_library_dir,
                item_label="audio",
                library_ok=True,
                library_message="ok",
                cache_status=cache_status,
            )
            # Reuse cached quick scan if available (avoid re-walking the
            # filesystem on every 2-second poll while the index builds).
            now = time.monotonic()
            if _quick_cache["items"] and (now - _quick_cache["at"]) < 30.0:
                quick_items = _quick_cache["items"]
                logger.debug("GET /api/audio/tracks — reusing cached quick scan (%d items)", len(quick_items))
            else:
                quick_items = quick_folder_scan(
                    resolved_library_dir,
                    suffixes=AUDIO_SUFFIX,
                    media_type="audio",
                    stream_url_prefix="/audio/stream",
                )
                _quick_cache["items"] = quick_items
                _quick_cache["at"] = now
            filtered = query_tracks(quick_items, q=q, artist=artist, sort_by=sort)
            logger.info(
                "GET /api/audio/tracks — quick scan %d items in %.2fs (refresh_started=%s, status=%s)",
                len(quick_items),
                time.monotonic() - cache_t0,
                refresh_started,
                status_payload["detail"],
            )
            return {
                "count": len(filtered),
                "items": [t.to_dict() for t in filtered],
                "artists": list_artists(quick_items),
                "refreshing": True,
                **status_payload,
                "query": {"q": q or "", "artist": artist or "all", "sort": sort},
            }
        query_t0 = time.monotonic()
        filtered = query_tracks(tracks, q=q, artist=artist, sort_by=sort)
        query_elapsed = time.monotonic() - query_t0
        cache_status = _audio_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
        logger.info(
            "GET /api/audio/tracks — %d/%d items in %.1fs (cache=%.2fs, query=%.2fs, refresh_started=%s, building=%s, q=%r, artist=%r, sort=%r)",
            len(filtered),
            len(tracks),
            time.monotonic() - t0,
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
            "items": [t.to_dict() for t in filtered],
            "artists": list_artists(tracks),
            "refreshing": building,
            "cache": cache_status,
            "query": {"q": q or "", "artist": artist or "all", "sort": sort},
        }

    @app.post("/api/audio/refresh")
    def audio_refresh() -> dict[str, object]:
        """Invalidate the index cache and trigger a fresh rebuild from the filesystem."""
        _audio_index_cache.invalidate()
        _quick_cache["items"] = []
        _quick_cache["at"] = 0.0
        _audio_index_cache.ensure_background_refresh(
            resolved_library_dir,
            cache_dir=resolved_cache_dir,
        )
        return {"ok": True, "detail": "Refresh started"}

    @app.post("/api/audio/refresh-ratings")
    def audio_refresh_ratings(payload: dict[str, object]) -> dict[str, object]:
        """Re-read POPM ratings from the filesystem for specific tracks.

        Designed for lazy on-demand refresh: instead of rebuilding the entire
        5 000-item index, the client sends only the paths it is currently
        displaying (typically 10–50 items for a single folder).

        Body: ``{"paths": ["Funsongs/song1.mp3", ...]}``
        Returns: ``{"ok": true, "ratings": {"Funsongs/song1.mp3": 5.0, ...}, "changed": 3}``
        """
        from hometools.audio.metadata import get_popm_rating, popm_raw_to_stars

        paths = payload.get("paths", [])
        if not isinstance(paths, list) or not paths:
            raise HTTPException(status_code=400, detail="paths must be a non-empty list")

        ratings: dict[str, float] = {}
        for path_str in paths[:500]:  # cap to prevent abuse
            path_str = str(path_str).strip()
            if not path_str:
                continue
            try:
                file_path = resolve_audio_path(resolved_library_dir, path_str)
                raw = get_popm_rating(file_path)
                stars = popm_raw_to_stars(raw)
                ratings[path_str] = stars
            except Exception:
                continue  # skip unresolvable / unreadable paths

        # Patch in-memory cache so subsequent /api/audio/tracks responses
        # already contain the corrected ratings.
        cache_updates = {p: {"rating": r} for p, r in ratings.items()}
        changed = _audio_index_cache.patch_items(cache_updates)

        # Derive folder name from common prefix of requested paths
        folder = ""
        if paths:
            parts = [str(p).replace("\\", "/") for p in paths[:500] if str(p).strip()]
            if parts:
                first_dir = parts[0].rsplit("/", 1)[0] if "/" in parts[0] else ""
                if first_dir and all(str(p).replace("\\", "/").startswith(first_dir + "/") for p in parts):
                    folder = first_dir
                else:
                    folder = "(root)"

        last_refresh = _update_refresh_log(
            resolved_cache_dir,
            folder,
            total=len(ratings),
            changed=changed,
        )

        return {
            "ok": True,
            "ratings": ratings,
            "changed": changed,
            "last_refresh": last_refresh,
            "folder": folder,
        }

    @app.get("/api/audio/refresh-log")
    def audio_refresh_log() -> dict[str, object]:
        """Return the persistent rating-refresh log (folder → last timestamp)."""
        return _read_refresh_log(resolved_cache_dir)

    @app.get("/api/audio/status")
    def audio_status() -> dict[str, object]:
        from hometools.streaming.core.issue_registry import summarize_issue_and_todos

        ok, msg = check_library_accessible(resolved_library_dir)
        cache_status = (
            {
                "label": "audio-index",
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
            else _audio_index_cache.status(resolved_library_dir, cache_dir=resolved_cache_dir)
        )
        issue_todo_summary = summarize_issue_and_todos(resolved_cache_dir)
        payload = build_index_status_payload(
            library_dir=resolved_library_dir,
            item_label="audio",
            library_ok=ok,
            library_message="Safe mode active — no cache snapshot or thumbnail warmup" if resolved_safe_mode else msg,
            cache_status=cache_status,
            issues_summary=issue_todo_summary["issues"],
            todo_summary=issue_todo_summary["todos"],
        )
        return payload

    @app.post("/api/audio/todos/state")
    def audio_todo_state(payload: dict[str, object]) -> dict[str, object]:
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

    @app.get("/api/audio/lyrics")
    def audio_lyrics(path: str) -> dict[str, object]:
        """Return embedded lyrics for an audio file, or null if none found."""
        from hometools.audio.metadata import get_lyrics

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        text = get_lyrics(file_path)
        return {"path": path, "lyrics": text, "has_lyrics": text is not None}

    @app.get("/api/audio/metadata")
    def audio_metadata(path: str) -> dict[str, object]:
        """Re-read embedded metadata for a single audio track."""
        from hometools.audio.metadata import audiofile_assume_artist_title, get_popm_rating, popm_raw_to_stars

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        parts = split_stem(file_path.stem)
        artist = parts[0] if parts else "Unknown"
        title = parts[1] if len(parts) > 1 else "MISSING"
        stars = 0.0

        try:
            artist, title = audiofile_assume_artist_title(file_path)
            raw_rating = get_popm_rating(file_path)
            stars = popm_raw_to_stars(raw_rating)
        except Exception:
            logger.warning("GET /api/audio/metadata — fallback for %s due to metadata read error", path, exc_info=True)

        return {"title": title, "artist": artist, "rating": stars}

    @app.post("/api/audio/rating")
    def audio_set_rating(payload: dict[str, object]) -> dict[str, object]:
        """Write a star rating (0–5) as POPM tag to an MP3 file.

        Returns the ``entry_id`` of the audit log entry so the client can
        offer a one-click undo.
        """
        from hometools.audio.metadata import get_popm_rating, popm_raw_to_stars, set_popm_rating, stars_to_popm_raw
        from hometools.streaming.core.audit_log import log_rating_write

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        try:
            stars = float(payload.get("rating") or 0)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="rating must be a number 0–5") from exc
        if not 0 <= stars <= 5:
            raise HTTPException(status_code=400, detail="rating must be between 0 and 5")

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        # Read current rating before overwriting (needed for undo)
        old_raw = get_popm_rating(file_path)
        old_stars = popm_raw_to_stars(old_raw)
        new_raw = stars_to_popm_raw(stars)

        ok = set_popm_rating(file_path, new_raw)
        entry_id = ""
        if ok:
            _audio_index_cache.invalidate()
            entry = log_rating_write(
                resolved_audit_dir,
                server="audio",
                path=path,
                old_stars=old_stars,
                new_stars=stars,
                old_raw=old_raw,
                new_raw=new_raw,
            )
            entry_id = entry.entry_id
        return {"ok": ok, "rating": stars, "raw": new_raw, "entry_id": entry_id}

    @app.post("/api/audio/metadata/edit")
    def audio_metadata_edit(payload: dict[str, object]) -> dict[str, object]:
        """Write text tags (title / artist / album) to an audio file.

        Body: ``{"path": "...", "title": "...", "artist": "...", "album": "..."}``
        Missing / null fields are left unchanged.
        Returns ``{"ok": bool, "entry_ids": [...]}`` with one audit entry per changed field.
        """
        from hometools.audio.metadata import audiofile_assume_artist_title, write_track_tags
        from hometools.streaming.core.audit_log import log_tag_write

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        new_title = str(payload["title"]).strip() if payload.get("title") is not None else None
        new_artist = str(payload["artist"]).strip() if payload.get("artist") is not None else None
        new_album = str(payload["album"]).strip() if payload.get("album") is not None else None

        # Read current values for audit log
        try:
            cur_artist, cur_title = audiofile_assume_artist_title(file_path)
        except Exception:
            cur_artist, cur_title = "", ""
        cur_album = ""

        ok = write_track_tags(file_path, title=new_title, artist=new_artist, album=new_album)

        entry_ids: list[str] = []
        if ok:
            _audio_index_cache.invalidate()
            for field, old_val, new_val in [
                ("title", cur_title, new_title),
                ("artist", cur_artist, new_artist),
                ("album", cur_album, new_album),
            ]:
                if new_val is not None and new_val != old_val:
                    entry = log_tag_write(
                        resolved_audit_dir,
                        server="audio",
                        path=path,
                        field=field,
                        old_value=old_val,
                        new_value=new_val,
                    )
                    entry_ids.append(entry.entry_id)

        return {"ok": ok, "entry_ids": entry_ids}

    @app.get("/api/audio/recent")
    def audio_recent(limit: int = 10) -> dict[str, object]:
        """No recently-played section for audio.

        Audiobook resume is handled automatically via ``loadAndSeekProgress``
        in the player JS (fires on every playItem call) — no dedicated
        "recently played" UI is needed or shown.
        """
        return {"items": []}

    # --- Audit log endpoints ---

    @app.get("/api/audio/audit")
    def audio_audit_entries(
        limit: int = 200,
        path_filter: str = "",
        action_filter: str = "",
        include_undone: bool = True,
    ) -> dict[str, object]:
        """Return audit log entries for the audio server."""
        from hometools.streaming.core.audit_log import load_entries

        entries = load_entries(
            resolved_audit_dir,
            limit=limit,
            path_filter=path_filter,
            action_filter=action_filter,
            include_undone=include_undone,
        )
        return {"items": entries, "total": len(entries)}

    @app.post("/api/audio/audit/undo")
    def audio_audit_undo(payload: dict[str, object]) -> dict[str, object]:
        """Undo a single audit log entry by entry_id.

        Re-applies the stored ``undo_payload`` (currently: rating writes).
        """
        from hometools.audio.metadata import set_popm_rating
        from hometools.streaming.core.audit_log import get_entry, mark_undone

        entry_id = str(payload.get("entry_id") or "").strip()
        if not entry_id:
            raise HTTPException(status_code=400, detail="entry_id is required")

        entry = get_entry(resolved_audit_dir, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Audit entry not found")
        if entry.get("undone"):
            raise HTTPException(status_code=409, detail="Entry has already been undone")

        undo = entry.get("undo_payload", {})
        action = entry.get("action", "")

        if action == "rating_write":
            path = str(undo.get("path") or "").strip()
            raw = int(undo.get("raw") or 0)
            try:
                file_path = resolve_audio_path(resolved_library_dir, path)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            ok = set_popm_rating(file_path, raw)
            if ok:
                mark_undone(resolved_audit_dir, entry_id)
                _audio_index_cache.invalidate()
                return {"ok": True, "action": action, "restored_rating": undo.get("rating")}
            raise HTTPException(status_code=500, detail="Failed to restore rating")

        if action == "tag_write":
            from hometools.audio.metadata import write_track_tags

            path = str(undo.get("path") or "").strip()
            field = str(undo.get("field") or "").strip()
            value = str(undo.get("value") or "")
            try:
                file_path = resolve_audio_path(resolved_library_dir, path)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            kwargs = {field: value} if field in ("title", "artist", "album") else {}
            ok = write_track_tags(file_path, **kwargs)
            if ok:
                mark_undone(resolved_audit_dir, entry_id)
                _audio_index_cache.invalidate()
                return {"ok": True, "action": action, "restored_field": field, "restored_value": value}
            raise HTTPException(status_code=500, detail="Failed to restore tag")

        raise HTTPException(status_code=422, detail=f"Undo not supported for action '{action}'")

    @app.get("/audit")
    def audio_audit_panel() -> HTMLResponse:
        """Serve the dark-theme Audit / Control-Panel HTML page."""
        from fastapi.responses import HTMLResponse

        from hometools.streaming.core.server_utils import render_audit_panel_html

        return HTMLResponse(
            render_audit_panel_html(
                server="hometools audio",
                media_type="audio",
                title="Audit-Log — hometools audio",
            )
        )

    @app.post("/api/audio/progress")
    def audio_save_progress(payload: dict[str, object]) -> dict[str, object]:
        """Save playback progress for an audio track."""
        from hometools.streaming.core.progress import save_progress

        rp = str(payload.get("relative_path") or "").strip()
        if not rp:
            raise HTTPException(status_code=400, detail="relative_path is required")
        pos = float(payload.get("position_seconds") or 0)
        dur = float(payload.get("duration") or 0)
        ok = save_progress(resolved_cache_dir, rp, pos, dur)
        return {"ok": ok}

    @app.get("/api/audio/progress")
    def audio_load_progress(path: str) -> dict[str, object]:
        """Load playback progress for an audio track."""
        from hometools.streaming.core.progress import load_progress

        entry = load_progress(resolved_cache_dir, path)
        return {"items": [entry] if entry else []}

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
    def thumb(path: str, size: str = "sm") -> FileResponse:
        """Serve a cached thumbnail image for an audio track.

        Pass ``?size=lg`` for the large (480 px) variant.
        """
        from urllib.parse import unquote

        relative_path = unquote(path)
        if size == "lg":
            from hometools.streaming.core.thumbnailer import get_thumbnail_lg_path

            thumb_path = get_thumbnail_lg_path(resolved_cache_dir, "audio", relative_path)
        else:
            thumb_path = get_thumbnail_path(resolved_cache_dir, "audio", relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    # --- Playlists API ---

    @app.get("/api/audio/playlists/version")
    def audio_playlists_version() -> dict[str, object]:
        """Return the current playlist revision number (lightweight)."""
        from hometools.streaming.core.playlists import get_revision

        return {"revision": get_revision(resolved_cache_dir, "audio")}

    @app.get("/api/audio/playlists")
    def audio_playlists() -> dict[str, object]:
        """Return all user playlists for the audio server."""
        from hometools.streaming.core.playlists import load_playlists_with_revision

        playlists, revision = load_playlists_with_revision(resolved_cache_dir, "audio")
        return {"items": playlists, "revision": revision}

    @app.post("/api/audio/playlists")
    def audio_create_playlist(payload: dict[str, str]) -> dict[str, object]:
        """Create a new empty playlist."""
        from hometools.streaming.core.playlists import create_playlist

        name = payload.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        pl = create_playlist(resolved_cache_dir, "audio", name=name)
        return {"playlist": pl}

    @app.delete("/api/audio/playlists")
    def audio_delete_playlist(id: str) -> dict[str, object]:
        """Delete a playlist by id."""
        from hometools.streaming.core.playlists import delete_playlist

        remaining = delete_playlist(resolved_cache_dir, "audio", id)
        return {"items": remaining}

    @app.post("/api/audio/playlists/items")
    def audio_add_playlist_item(payload: dict[str, str]) -> dict[str, object]:
        """Add a track to a playlist."""
        from hometools.config import get_playlist_insert_position
        from hometools.streaming.core.playlists import add_item

        playlist_id = payload.get("playlist_id", "")
        relative_path = payload.get("relative_path", "")
        if not playlist_id or not relative_path:
            raise HTTPException(status_code=400, detail="playlist_id and relative_path are required")
        pl = add_item(
            resolved_cache_dir,
            "audio",
            playlist_id,
            relative_path=relative_path,
            insert_position=get_playlist_insert_position(),
        )
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    @app.delete("/api/audio/playlists/items")
    def audio_remove_playlist_item(playlist_id: str, path: str) -> dict[str, object]:
        """Remove a track from a playlist."""
        from hometools.streaming.core.playlists import remove_item

        pl = remove_item(resolved_cache_dir, "audio", playlist_id, relative_path=path)
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    @app.patch("/api/audio/playlists/items")
    def audio_move_playlist_item(payload: dict[str, str]) -> dict[str, object]:
        """Move a track up or down within a playlist."""
        from hometools.streaming.core.playlists import move_item

        playlist_id = payload.get("playlist_id", "")
        relative_path = payload.get("relative_path", "")
        direction = payload.get("direction", "")
        if not playlist_id or not relative_path or direction not in ("up", "down"):
            raise HTTPException(status_code=400, detail="playlist_id, relative_path, and direction (up/down) are required")
        pl = move_item(resolved_cache_dir, "audio", playlist_id, relative_path=relative_path, direction=direction)
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist or item not found")
        return {"playlist": pl}

    @app.put("/api/audio/playlists/items")
    def audio_reorder_playlist_item(payload: dict[str, object]) -> dict[str, object]:
        """Move a track to a specific index within a playlist."""
        from hometools.streaming.core.playlists import reorder_item

        playlist_id = str(payload.get("playlist_id", ""))
        relative_path = str(payload.get("relative_path", ""))
        to_index = payload.get("to_index")
        if not playlist_id or not relative_path or to_index is None:
            raise HTTPException(status_code=400, detail="playlist_id, relative_path, and to_index are required")
        pl = reorder_item(resolved_cache_dir, "audio", playlist_id, relative_path=relative_path, to_index=int(to_index))
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist or item not found")
        return {"playlist": pl}

    # --- Custom Order API (server-side folder/favorites reorder) ---

    @app.get("/api/audio/folder-order")
    def audio_get_folder_order(path: str = "") -> dict[str, object]:
        """Return the custom item order for a folder (or __favorites__)."""
        from hometools.streaming.core.custom_order import load_order

        return {"items": load_order(resolved_cache_dir, "audio", path)}

    @app.put("/api/audio/folder-order")
    def audio_save_folder_order(payload: dict[str, object]) -> dict[str, object]:
        """Persist the custom item order for a folder (or __favorites__)."""
        from hometools.streaming.core.custom_order import save_order

        folder_path = str(payload.get("folder_path", ""))
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")
        saved = save_order(resolved_cache_dir, "audio", folder_path, [str(i) for i in items])
        return {"items": saved}

    @app.delete("/api/audio/folder-order")
    def audio_delete_folder_order(path: str = "") -> dict[str, object]:
        """Delete the custom order for a folder."""
        from hometools.streaming.core.custom_order import delete_order

        ok = delete_order(resolved_cache_dir, "audio", path)
        return {"deleted": ok}

    # --- Shortcuts API ---

    @app.get("/api/audio/shortcuts")
    def audio_shortcuts() -> dict[str, object]:
        """Return saved PWA shortcuts for the audio server."""
        from hometools.streaming.core.shortcuts import load_shortcuts

        return {"items": load_shortcuts(resolved_cache_dir, "audio")}

    @app.post("/api/audio/shortcuts")
    def audio_add_shortcut(payload: dict[str, str]) -> dict[str, object]:
        """Add or update a PWA shortcut."""
        from hometools.streaming.core.shortcuts import save_shortcut

        item_id = payload.get("id", "")
        title = payload.get("title", "")
        if not item_id or not title:
            raise HTTPException(status_code=400, detail="id and title are required")
        url = f"/?id={item_id}"
        icon = payload.get("icon", f"/thumb?path={item_id}")
        shortcuts = save_shortcut(resolved_cache_dir, "audio", item_id=item_id, title=title, url=url, icon=icon)
        return {"items": shortcuts}

    @app.delete("/api/audio/shortcuts")
    def audio_remove_shortcut(id: str) -> dict[str, object]:
        """Remove a PWA shortcut by item id."""
        from hometools.streaming.core.shortcuts import remove_shortcut

        shortcuts = remove_shortcut(resolved_cache_dir, "audio", id)
        return {"items": shortcuts}

    # --- PWA endpoints ---
    _AUDIO_THEME = "#1db954"

    @app.get("/manifest.json")
    def manifest():
        from fastapi.responses import JSONResponse

        from hometools.streaming.core.shortcuts import load_shortcuts

        saved = load_shortcuts(resolved_cache_dir, "audio")
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
            content=_json.loads(render_pwa_manifest("hometools audio", "Audio", theme_color=_AUDIO_THEME, shortcuts=pwa_shortcuts or None)),
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
