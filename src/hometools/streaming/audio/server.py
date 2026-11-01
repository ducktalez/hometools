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
    safe_resolve,
)
from hometools.streaming.core.thumbnailer import start_background_thumbnail_generation
from hometools.streaming.core.waveform import (
    check_waveform_cached,
    ensure_waveform,
    load_waveform,
    start_background_waveform_generation,
)

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
    from hometools.config import (
        get_bpm_max,
        get_bpm_min,
        get_crossfade_duration,
        get_debug_filter,
        get_min_rating,
        get_playlist_sync_interval,
    )

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
        enable_repeat=True,
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
        bpm_min=get_bpm_min(),
        bpm_max=get_bpm_max(),
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


def _deferred_delete(path: Path, retries: int = 12, delay: float = 5.0) -> None:
    """Delete *path* in a background thread with retries.

    Used on Windows when a file is still held open by an active stream while we
    already copied it to the new location.  We keep retrying until the file
    handle is released (typically when the HTTP connection closes).
    """
    import time as _time

    for attempt in range(retries):
        _time.sleep(delay)
        try:
            if not path.exists():
                return  # already gone
            path.unlink()
            logger.info("Deferred delete succeeded: %s (attempt %d)", path, attempt + 1)
            return
        except PermissionError:
            logger.debug("Deferred delete attempt %d/%d — file still in use: %s", attempt + 1, retries, path)
        except Exception:
            logger.warning("Deferred delete failed for %s", path, exc_info=True)
            return
    logger.warning("Deferred delete gave up after %d attempts: %s", retries, path)


def create_app(
    library_dir: Path | None = None,
    *,
    safe_mode: bool | None = None,
    cache_dir: Path | None = None,
    audit_dir: Path | None = None,
) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    resolved_cache_dir = cache_dir or get_cache_dir()
    resolved_audit_dir = audit_dir or get_audit_dir()
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

            def _prepare_waveforms() -> None:
                try:
                    work = collect_thumbnail_work(resolved_library_dir, resolved_cache_dir)
                    started = start_background_waveform_generation(work)
                    logger.info(
                        "Audio startup waveform work prepared: %d items (started=%s)",
                        len(work),
                        started,
                    )
                except Exception:
                    logger.debug("Failed to start background audio waveform generation", exc_info=True)

            threading.Thread(target=_prepare_waveforms, daemon=True, name="audio-waveform-bootstrap").start()
        else:
            logger.warning("Audio server running in SAFE MODE — caches, PWA and thumbnail warmups are disabled")

        logger.info("Audio server startup complete in %.2fs", time.monotonic() - startup_t0)
        yield

    app = FastAPI(title="hometools audio streaming prototype", lifespan=lifespan)
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

    @app.post("/api/audio/refresh-ratings")
    def audio_refresh_ratings(payload: dict[str, object]) -> dict[str, object]:
        """Re-read POPM ratings from the filesystem for specific tracks.

        Designed for lazy on-demand refresh: instead of rebuilding the entire
        5 000-item index, the client sends only the paths it is currently
        displaying (typically 10–50 items for a single folder).

        Body: ``{"paths": ["Funsongs/song1.mp3", ...]}``
        Returns: ``{"ok": true, "ratings": {"Funsongs/song1.mp3": 5.0, ...}, "changed": 3}``
        """
        from hometools.audio.metadata import get_rating_stars

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
                stars = get_rating_stars(file_path)
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
        from hometools.audio.metadata import audiofile_assume_artist_title, get_rating_stars

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
            stars = get_rating_stars(file_path)
        except Exception:
            logger.warning("GET /api/audio/metadata — fallback for %s due to metadata read error", path, exc_info=True)

        return {"title": title, "artist": artist, "rating": stars}

    @app.post("/api/audio/rating")
    def audio_set_rating(payload: dict[str, object]) -> dict[str, object]:
        """Write a star rating (0–5) to an audio file.

        Supports MP3 (POPM), M4A (iTunes freeform atom), FLAC/OGG (Vorbis).
        Returns the ``entry_id`` of the audit log entry so the client can
        offer a one-click undo.
        """
        from hometools.audio.metadata import get_rating_stars, set_rating_stars, stars_to_popm_raw
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
        old_stars = get_rating_stars(file_path)
        new_raw = stars_to_popm_raw(stars)  # for audit log / response compatibility

        ok = set_rating_stars(file_path, stars)
        entry_id = ""
        if ok:
            # Immediately update the in-memory cache so subsequent API
            # requests return the correct rating even before the background
            # rebuild reads it back from disk.
            _audio_index_cache.patch_items({path: {"rating": stars}})
            _audio_index_cache.invalidate()
            entry = log_rating_write(
                resolved_audit_dir,
                server="audio",
                path=path,
                old_stars=old_stars,
                new_stars=stars,
                old_raw=stars_to_popm_raw(old_stars),
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

    @app.post("/api/audio/bpm/calculate")
    async def audio_bpm_calculate(payload: dict[str, object]) -> dict[str, object]:
        """Estimate a track's BPM (librosa) and write it to the file's tags.

        Body: ``{"path": "..."}``. This is an **edit tool** — the client
        only exposes it (via the BPM-adjust popup) when the Tools-panel
        "BPM berechnen" toggle is active; the endpoint itself has no
        separate feature flag since BPM calculation is inherently harmless
        to expose (it estimates + writes one numeric tag, same trust level
        as rating writes). Requires the optional ``audio-analysis`` extra
        (librosa); returns ``{"ok": false, "error": "..."}`` (never a 5xx)
        when that dependency is missing or analysis fails, so the UI can
        show a toast instead of a broken request.

        The raw librosa estimate is biased by any stored octave-correction
        hint (``streaming/core/bpm_hints.py``) before being rounded/saved —
        set previously via a "Langsamer"/"Schneller" BPM-adjust action, so
        a known half/double-tempo mis-detection isn't reproduced here.
        """
        import asyncio

        from hometools.audio.bpm import calculate_bpm
        from hometools.audio.metadata import get_bpm, set_bpm
        from hometools.streaming.core.audit_log import log_bpm_write
        from hometools.streaming.core.bpm_hints import get_octave_multiplier

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        old_bpm = get_bpm(file_path)
        raw_bpm = await asyncio.to_thread(calculate_bpm, file_path)
        if raw_bpm is None:
            return {
                "ok": False,
                "error": "BPM-Berechnung nicht verf\u00fcgbar (librosa fehlt oder Analyse fehlgeschlagen).",
            }
        multiplier = get_octave_multiplier(resolved_cache_dir, "audio", path)
        bpm = raw_bpm * multiplier

        ok = set_bpm(file_path, bpm)
        if not ok:
            return {"ok": False, "error": "BPM konnte nicht gespeichert werden."}

        rounded = float(round(bpm))
        _audio_index_cache.patch_items({path: {"bpm": rounded}})
        _audio_index_cache.invalidate()
        entry = log_bpm_write(
            resolved_audit_dir,
            server="audio",
            path=path,
            old_bpm=old_bpm,
            new_bpm=rounded,
        )
        return {"ok": True, "bpm": rounded, "entry_id": entry.entry_id}

    @app.post("/api/audio/bpm/adjust")
    async def audio_bpm_adjust(payload: dict[str, object]) -> dict[str, object]:
        """Halve/double a track's stored BPM and remember the correction.

        Body: ``{"path": "...", "factor": 0.5 | 2}``. Beat-tracking
        sometimes locks onto half/double the true tempo (an "octave
        error") — this fixes a mis-detected value in one click AND biases
        every future "neu berechnen" (``/api/audio/bpm/calculate``) call
        the same way via ``streaming/core/bpm_hints.py``, so the same
        mistake isn't repeated. Requires an existing positive BPM value
        (nothing to scale otherwise); rejects results outside a sane
        1-400 BPM range. Never a 5xx for a "nothing to adjust" case —
        returns ``{"ok": false, "error": "..."}`` instead.
        """
        from hometools.audio.metadata import get_bpm, set_bpm
        from hometools.streaming.core.audit_log import log_bpm_write
        from hometools.streaming.core.bpm_hints import adjust_octave_multiplier

        path = str(payload.get("path") or "").strip()
        try:
            factor = float(payload.get("factor") or 0)
        except (TypeError, ValueError):
            factor = 0.0
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        if factor not in (0.5, 2.0):
            raise HTTPException(status_code=400, detail="factor must be 0.5 or 2")

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        old_bpm = get_bpm(file_path)
        if old_bpm <= 0:
            return {"ok": False, "error": "Kein BPM-Wert vorhanden, der angepasst werden k\u00f6nnte."}
        new_bpm = old_bpm * factor
        if not (1.0 <= new_bpm <= 400.0):
            return {"ok": False, "error": "Angepasster BPM-Wert liegt au\u00dferhalb des g\u00fcltigen Bereichs."}

        ok = set_bpm(file_path, new_bpm)
        if not ok:
            return {"ok": False, "error": "BPM konnte nicht gespeichert werden."}

        adjust_octave_multiplier(resolved_cache_dir, "audio", path, factor)
        rounded = float(round(new_bpm))
        _audio_index_cache.patch_items({path: {"bpm": rounded}})
        _audio_index_cache.invalidate()
        entry = log_bpm_write(
            resolved_audit_dir,
            server="audio",
            path=path,
            old_bpm=old_bpm,
            new_bpm=rounded,
        )
        return {"ok": True, "bpm": rounded, "entry_id": entry.entry_id}

    @app.post("/api/audio/bpm/set")
    async def audio_bpm_set(payload: dict[str, object]) -> dict[str, object]:
        """Manually set a track's BPM to an explicit value ("Analoge Werteingabe").

        Body: ``{"path": "...", "bpm": <number>}``. Unlike ``bpm/adjust``
        this does **not** touch the stored octave-correction hint
        (``streaming/core/bpm_hints.py``) — a one-off manual value doesn't
        tell us anything about *why* the last automatic estimate was
        wrong, only what the correct value is right now.
        """
        from hometools.audio.metadata import get_bpm, set_bpm
        from hometools.streaming.core.audit_log import log_bpm_write

        path = str(payload.get("path") or "").strip()
        try:
            bpm = float(payload.get("bpm") or 0)
        except (TypeError, ValueError):
            bpm = 0.0
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        if not (1.0 <= bpm <= 400.0):
            return {"ok": False, "error": "BPM muss zwischen 1 und 400 liegen."}

        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        old_bpm = get_bpm(file_path)
        ok = set_bpm(file_path, bpm)
        if not ok:
            return {"ok": False, "error": "BPM konnte nicht gespeichert werden."}

        rounded = float(round(bpm))
        _audio_index_cache.patch_items({path: {"bpm": rounded}})
        _audio_index_cache.invalidate()
        entry = log_bpm_write(
            resolved_audit_dir,
            server="audio",
            path=path,
            old_bpm=old_bpm,
            new_bpm=rounded,
        )
        return {"ok": True, "bpm": rounded, "entry_id": entry.entry_id}

    @app.get("/api/audio/folders")
    def audio_list_folders() -> dict[str, object]:
        """Return all top-level folder names in the audio library."""
        try:
            items = _audio_index_cache.get(library_dir=resolved_library_dir, cache_dir=resolved_cache_dir)
            folders: set[str] = set()
            for item in items:
                parts = item.relative_path.split("/")
                if len(parts) > 1:
                    folders.add(parts[0])
            return {"folders": sorted(folders, key=str.casefold)}
        except Exception:
            logger.exception("Failed to list folders")
            return {"folders": []}

    @app.post("/api/audio/move-file")
    def audio_move_file(payload: dict[str, object]) -> dict[str, object]:
        """Move an audio file to a different folder within the library.

        Body: ``{"path": "OLD/song.mp3", "target_folder": "NEW"}``
        Returns ``{"ok": true, "new_path": "NEW/song.mp3", "entry_id": "..."}``
        """
        import shutil

        from hometools.streaming.core.audit_log import log_file_move

        path = str(payload.get("path") or "").strip()
        target_folder = str(payload.get("target_folder") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        if not target_folder:
            raise HTTPException(status_code=400, detail="target_folder is required")

        # Validate the source file exists
        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        # Compute target path
        filename = file_path.name
        target_dir = resolved_library_dir / target_folder
        target_file = target_dir / filename

        # Safety checks
        try:
            safe_target = safe_resolve(target_file)
            safe_target.relative_to(safe_resolve(resolved_library_dir))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Target path escapes the library.") from exc

        if target_file.exists():
            raise HTTPException(status_code=409, detail=f"File already exists: {target_folder}/{filename}")

        # Create target directory if needed and move the file
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(target_file))
        except PermissionError as exc:
            # Windows WinError 32: file is held open by an active stream.
            # shutil.move() already copied the file to the destination before
            # failing to delete the source.  If the copy is in place we treat
            # the move as successful and schedule a background retry to remove
            # the original once the file handle is released.
            if target_file.exists():
                logger.info(
                    "File in use during move %s → %s — copy succeeded, scheduling deferred source delete",
                    file_path,
                    target_file,
                )
                threading.Thread(
                    target=_deferred_delete,
                    args=(file_path,),
                    daemon=True,
                    name="deferred-delete",
                ).start()
                # Fall through to the success path below
            else:
                # Copy did not succeed either — genuine failure
                raise HTTPException(
                    status_code=409,
                    detail="Die Datei kann nicht verschoben werden (Zugriff verweigert).",
                ) from exc
        except Exception as exc:
            logger.exception("Failed to move file %s → %s", file_path, target_file)
            raise HTTPException(status_code=500, detail=f"Move failed: {exc}") from exc

        # Compute the new relative path
        new_relative = safe_resolve(target_file).relative_to(safe_resolve(resolved_library_dir)).as_posix()

        # Audit log entry
        entry = log_file_move(
            resolved_audit_dir,
            server="audio",
            old_path=path,
            new_path=new_relative,
        )

        # Invalidate the index so the next request picks up the change
        _audio_index_cache.invalidate()

        return {"ok": True, "new_path": new_relative, "entry_id": entry.entry_id}

    @app.get("/api/audio/recent")
    def audio_recent(limit: int = 10) -> dict[str, object]:
        """No recently-played section for audio.

        Audiobook resume is handled automatically via ``loadAndSeekProgress``
        in the player JS (fires on every playItem call) — no dedicated
        "recently played" UI is needed or shown.
        """
        return {"items": []}

    # --- Audit log endpoints ---

    @app.post("/api/audio/audit/undo")
    def audio_audit_undo(payload: dict[str, object]) -> dict[str, object]:
        """Undo a single audit log entry by entry_id.

        Re-applies the stored ``undo_payload`` (currently: rating writes).
        """
        from hometools.audio.metadata import set_rating_stars
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
            restore_stars = float(undo.get("rating") or 0)
            try:
                file_path = resolve_audio_path(resolved_library_dir, path)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            ok = set_rating_stars(file_path, restore_stars)
            if ok:
                mark_undone(resolved_audit_dir, entry_id)
                _audio_index_cache.patch_items({path: {"rating": restore_stars}})
                _audio_index_cache.invalidate()
                return {"ok": True, "action": action, "restored_rating": restore_stars}
            raise HTTPException(status_code=500, detail="Failed to restore rating")

        if action == "bpm_write":
            from hometools.audio.metadata import set_bpm

            path = str(undo.get("path") or "").strip()
            restore_bpm = float(undo.get("bpm") or 0)
            try:
                file_path = resolve_audio_path(resolved_library_dir, path)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            if restore_bpm <= 0:
                # set_bpm() only writes positive values (no "delete tag" support in
                # any of the supported formats' write path) — the tag was unset
                # before this write, so there is nothing safe to restore it to.
                raise HTTPException(
                    status_code=422,
                    detail="Kann nicht r\u00fcckg\u00e4ngig gemacht werden: BPM war zuvor nicht gesetzt.",
                )
            ok = set_bpm(file_path, restore_bpm)
            if ok:
                mark_undone(resolved_audit_dir, entry_id)
                _audio_index_cache.patch_items({path: {"bpm": restore_bpm}})
                _audio_index_cache.invalidate()
                return {"ok": True, "action": action, "restored_bpm": restore_bpm}
            raise HTTPException(status_code=500, detail="Failed to restore bpm")

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

        if action == "file_move":
            import shutil

            old_path = str(undo.get("old_path") or "").strip()
            new_path = str(undo.get("new_path") or "").strip()
            if not old_path or not new_path:
                raise HTTPException(status_code=400, detail="old_path and new_path required in undo payload")
            # The file is currently at new_path, move back to old_path
            try:
                current_file = resolve_audio_path(resolved_library_dir, new_path)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            restore_target = safe_resolve(resolved_library_dir / Path(old_path))
            try:
                restore_target.relative_to(safe_resolve(resolved_library_dir))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Restore path escapes the library.") from exc
            restore_target.parent.mkdir(parents=True, exist_ok=True)
            if restore_target.exists():
                raise HTTPException(status_code=409, detail=f"File already exists at original location: {old_path}")
            try:
                shutil.move(str(current_file), str(restore_target))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Move-back failed: {exc}") from exc
            mark_undone(resolved_audit_dir, entry_id)
            _audio_index_cache.invalidate()
            return {"ok": True, "action": action, "restored_path": old_path}

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

    @app.get("/api/audio/waveform")
    def audio_waveform(path: str) -> dict[str, object]:
        """Return cached waveform peaks (128 segments, 0.0–1.0) for an audio file.

        Tries the shadow cache first.  Falls back to on-demand generation so the
        first request per track always succeeds (takes < 5 s for typical songs).
        Returns ``{"peaks": [...], "segments": 128}`` or 404 if unavailable.
        """
        from urllib.parse import unquote

        relative_path = unquote(path)
        if not relative_path:
            raise HTTPException(status_code=400, detail="path is required")

        # Fast path: already cached
        cached = check_waveform_cached(resolved_cache_dir, "audio", relative_path)
        if cached:
            data = load_waveform(cached)
            if data:
                return data

        # On-demand: resolve the source file and generate
        try:
            file_path = resolve_audio_path(resolved_library_dir, relative_path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        wf_path = ensure_waveform(file_path, resolved_cache_dir, "audio", relative_path)
        if wf_path:
            data = load_waveform(wf_path)
            if data:
                return data

        raise HTTPException(status_code=404, detail="Waveform not available")

    # --- Shared endpoints (core/server_factory.py) ---
    register_health_route(app, resolved_library_dir)
    register_index_routes(
        app,
        library_dir=resolved_library_dir,
        cache_dir=resolved_cache_dir,
        safe_mode=resolved_safe_mode,
        media_type="audio",
        api_path="/api/audio/tracks",
        items_name="tracks",
        default_sort="artist",
        suffixes=AUDIO_SUFFIX,
        stream_url_prefix="/audio/stream",
        index_cache=_audio_index_cache,
        build_index=build_audio_index,
        query_fn=query_tracks,
        list_artists_fn=list_artists,
    )
    register_thumb_route(app, resolved_cache_dir, "audio", allow_sprite=False)
    register_todo_state_route(app, resolved_cache_dir, "audio")
    register_audit_entries_route(app, resolved_audit_dir, "audio")
    register_reveal_route(app, resolved_library_dir, "audio", resolve_audio_path)
    register_delete_file_route(app, resolved_library_dir, resolved_audit_dir, "audio", resolve_audio_path, _audio_index_cache.invalidate)
    register_progress_routes(app, resolved_cache_dir, "audio")
    register_playlist_routes(app, resolved_cache_dir, "audio")
    register_folder_order_routes(app, resolved_cache_dir, "audio")
    register_shortcuts_routes(app, resolved_cache_dir, "audio")
    register_pwa_routes(
        app,
        cache_dir=resolved_cache_dir,
        media_type="audio",
        app_name="hometools audio",
        short_name="Audio",
        emoji="??",
        theme_color="#1db954",
    )

    return app
