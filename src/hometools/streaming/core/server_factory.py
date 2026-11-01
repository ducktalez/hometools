"""Shared route registrars for the audio + video streaming servers.

Each ``register_*`` function adds one group of media-type-agnostic endpoints
to a FastAPI app. Handler names (``<media>_<name>``) and paths match the
former per-server definitions so the OpenAPI contract stays unchanged.
"""

from __future__ import annotations

import json as _json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hometools.streaming.core.server_utils import (
    check_library_accessible,
    render_pwa_icon_png,
    render_pwa_icon_svg,
    render_pwa_manifest,
    render_pwa_service_worker,
)


def _named(fn: Callable[..., Any], media_type: str, name: str) -> Callable[..., Any]:
    """Rename handler to ``<media>_<name>`` (keeps stable OpenAPI operation IDs)."""
    fn.__name__ = f"{media_type}_{name}"
    fn.__qualname__ = fn.__name__
    return fn


def register_health_route(app: Any, library_dir: Path) -> None:
    """``GET /health``."""

    @app.get("/health")
    def health() -> dict[str, str]:
        ok, msg = check_library_accessible(library_dir)
        return {
            "status": "ok" if ok else "degraded",
            "library_dir": str(library_dir),
            "library_accessible": str(ok),
            "detail": msg,
        }


def register_pwa_routes(
    app: Any,
    *,
    cache_dir: Path,
    media_type: str,
    app_name: str,
    short_name: str,
    emoji: str,
    theme_color: str,
    display_mode: str | None = None,
) -> None:
    """``/manifest.json``, ``/sw.js``, ``/icon.svg``, ``/icon-192.png``, ``/icon-512.png``."""
    from fastapi.responses import JSONResponse, Response

    from hometools.streaming.core.shortcuts import load_shortcuts

    @app.get("/manifest.json")
    def manifest():
        saved = load_shortcuts(cache_dir, media_type)
        pwa_shortcuts = [
            {
                "name": s["title"],
                "short_name": s["title"][:25],
                "url": s.get("url", f"/?id={s['id']}"),
                "icons": [{"src": s.get("icon", "/icon.svg"), "sizes": "any"}],
            }
            for s in saved
        ]
        kwargs: dict[str, Any] = {"theme_color": theme_color, "shortcuts": pwa_shortcuts or None}
        if display_mode is not None:
            kwargs["display_mode"] = display_mode
        return JSONResponse(
            content=_json.loads(render_pwa_manifest(app_name, short_name, **kwargs)),
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        return Response(content=render_pwa_service_worker(), media_type="application/javascript")

    @app.get("/icon.svg")
    def icon_svg():
        return Response(content=render_pwa_icon_svg(emoji, theme_color), media_type="image/svg+xml")

    @app.get("/icon-192.png")
    def icon_192():
        return Response(content=render_pwa_icon_png(emoji, 192, theme_color), media_type="image/png")

    @app.get("/icon-512.png")
    def icon_512():
        return Response(content=render_pwa_icon_png(emoji, 512, theme_color), media_type="image/png")


def register_progress_routes(app: Any, cache_dir: Path, media_type: str) -> None:
    """``POST/GET /api/<media>/progress``."""
    from fastapi import HTTPException

    def save_progress_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.progress import save_progress

        rp = str(payload.get("relative_path") or "").strip()
        if not rp:
            raise HTTPException(status_code=400, detail="relative_path is required")
        pos = float(payload.get("position_seconds") or 0)
        dur = float(payload.get("duration") or 0)
        return {"ok": save_progress(cache_dir, rp, pos, dur)}

    def load_progress_ep(path: str) -> dict[str, object]:
        from hometools.streaming.core.progress import load_progress

        entry = load_progress(cache_dir, path)
        return {"items": [entry] if entry else []}

    base = f"/api/{media_type}/progress"
    app.post(base)(_named(save_progress_ep, media_type, "save_progress"))
    app.get(base)(_named(load_progress_ep, media_type, "load_progress"))


def register_shortcuts_routes(app: Any, cache_dir: Path, media_type: str) -> None:
    """``GET/POST/DELETE /api/<media>/shortcuts``."""
    from fastapi import HTTPException

    def list_ep() -> dict[str, object]:
        from hometools.streaming.core.shortcuts import load_shortcuts

        return {"items": load_shortcuts(cache_dir, media_type)}

    def add_ep(payload: dict[str, str]) -> dict[str, object]:
        from hometools.streaming.core.shortcuts import save_shortcut

        item_id = payload.get("id", "")
        title = payload.get("title", "")
        if not item_id or not title:
            raise HTTPException(status_code=400, detail="id and title are required")
        url = f"/?id={item_id}"
        icon = payload.get("icon", f"/thumb?path={item_id}")
        return {"items": save_shortcut(cache_dir, media_type, item_id=item_id, title=title, url=url, icon=icon)}

    def remove_ep(id: str) -> dict[str, object]:
        from hometools.streaming.core.shortcuts import remove_shortcut

        return {"items": remove_shortcut(cache_dir, media_type, id)}

    base = f"/api/{media_type}/shortcuts"
    app.get(base)(_named(list_ep, media_type, "shortcuts"))
    app.post(base)(_named(add_ep, media_type, "add_shortcut"))
    app.delete(base)(_named(remove_ep, media_type, "remove_shortcut"))


def register_folder_order_routes(app: Any, cache_dir: Path, media_type: str) -> None:
    """``GET/PUT/DELETE /api/<media>/folder-order``."""
    from fastapi import HTTPException

    def get_ep(path: str = "") -> dict[str, object]:
        from hometools.streaming.core.custom_order import load_order

        return {"items": load_order(cache_dir, media_type, path)}

    def save_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.custom_order import save_order

        folder_path = str(payload.get("folder_path", ""))
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")
        return {"items": save_order(cache_dir, media_type, folder_path, [str(i) for i in items])}

    def delete_ep(path: str = "") -> dict[str, object]:
        from hometools.streaming.core.custom_order import delete_order

        return {"deleted": delete_order(cache_dir, media_type, path)}

    base = f"/api/{media_type}/folder-order"
    app.get(base)(_named(get_ep, media_type, "get_folder_order"))
    app.put(base)(_named(save_ep, media_type, "save_folder_order"))
    app.delete(base)(_named(delete_ep, media_type, "delete_folder_order"))


def register_playlist_routes(app: Any, cache_dir: Path, media_type: str) -> None:
    """Playlist + smart-playlist endpoints under ``/api/<media>/playlists``."""
    from fastapi import HTTPException

    def version_ep() -> dict[str, object]:
        from hometools.streaming.core.playlists import get_revision

        return {"revision": get_revision(cache_dir, media_type)}

    def list_ep() -> dict[str, object]:
        from hometools.streaming.core.playlists import load_playlists_with_revision

        playlists, revision = load_playlists_with_revision(cache_dir, media_type)
        return {"items": playlists, "revision": revision}

    def create_ep(payload: dict[str, str]) -> dict[str, object]:
        from hometools.streaming.core.playlists import create_playlist

        name = payload.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        return {"playlist": create_playlist(cache_dir, media_type, name=name)}

    def delete_ep(id: str) -> dict[str, object]:
        from hometools.streaming.core.playlists import delete_playlist

        return {"items": delete_playlist(cache_dir, media_type, id)}

    def rename_ep(payload: dict[str, str]) -> dict[str, object]:
        from hometools.streaming.core.playlists import rename_playlist

        playlist_id = payload.get("playlist_id", "")
        name = payload.get("name", "").strip()
        if not playlist_id or not name:
            raise HTTPException(status_code=400, detail="playlist_id and name are required")
        pl = rename_playlist(cache_dir, media_type, playlist_id, name=name)
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    def add_item_ep(payload: dict[str, str]) -> dict[str, object]:
        from hometools.config import get_playlist_insert_position
        from hometools.streaming.core.playlists import add_item

        playlist_id = payload.get("playlist_id", "")
        relative_path = payload.get("relative_path", "")
        if not playlist_id or not relative_path:
            raise HTTPException(status_code=400, detail="playlist_id and relative_path are required")
        pl = add_item(
            cache_dir,
            media_type,
            playlist_id,
            relative_path=relative_path,
            insert_position=get_playlist_insert_position(),
        )
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    def remove_item_ep(playlist_id: str, path: str) -> dict[str, object]:
        from hometools.streaming.core.playlists import remove_item

        pl = remove_item(cache_dir, media_type, playlist_id, relative_path=path)
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    def move_item_ep(payload: dict[str, str]) -> dict[str, object]:
        from hometools.streaming.core.playlists import move_item

        playlist_id = payload.get("playlist_id", "")
        relative_path = payload.get("relative_path", "")
        direction = payload.get("direction", "")
        if not playlist_id or not relative_path or direction not in ("up", "down"):
            raise HTTPException(status_code=400, detail="playlist_id, relative_path, and direction (up/down) are required")
        pl = move_item(cache_dir, media_type, playlist_id, relative_path=relative_path, direction=direction)
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist or item not found")
        return {"playlist": pl}

    def reorder_item_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.playlists import reorder_item

        playlist_id = str(payload.get("playlist_id", ""))
        relative_path = str(payload.get("relative_path", ""))
        to_index = payload.get("to_index")
        if not playlist_id or not relative_path or to_index is None:
            raise HTTPException(status_code=400, detail="playlist_id, relative_path, and to_index are required")
        pl = reorder_item(cache_dir, media_type, playlist_id, relative_path=relative_path, to_index=int(to_index))
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist or item not found")
        return {"playlist": pl}

    def create_smart_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.playlists import create_playlist
        from hometools.streaming.core.smart_playlists import validate_smart_rules

        name = str(payload.get("name", "")).strip()
        smart = payload.get("smart")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        ok, reason = validate_smart_rules(smart)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        return {"playlist": create_playlist(cache_dir, media_type, name=name, smart=smart)}  # type: ignore[arg-type]

    def update_smart_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.playlists import update_smart_rules
        from hometools.streaming.core.smart_playlists import validate_smart_rules

        playlist_id = str(payload.get("playlist_id", ""))
        smart = payload.get("smart")
        if not playlist_id:
            raise HTTPException(status_code=400, detail="playlist_id is required")
        ok, reason = validate_smart_rules(smart, own_id=playlist_id)
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        pl = update_smart_rules(cache_dir, media_type, playlist_id, smart=smart)  # type: ignore[arg-type]
        if pl is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": pl}

    base = f"/api/{media_type}/playlists"
    app.get(f"{base}/version")(_named(version_ep, media_type, "playlists_version"))
    app.get(base)(_named(list_ep, media_type, "playlists"))
    app.post(base)(_named(create_ep, media_type, "create_playlist"))
    app.delete(base)(_named(delete_ep, media_type, "delete_playlist"))
    app.patch(base)(_named(rename_ep, media_type, "rename_playlist"))
    app.post(f"{base}/items")(_named(add_item_ep, media_type, "add_playlist_item"))
    app.delete(f"{base}/items")(_named(remove_item_ep, media_type, "remove_playlist_item"))
    app.patch(f"{base}/items")(_named(move_item_ep, media_type, "move_playlist_item"))
    app.put(f"{base}/items")(_named(reorder_item_ep, media_type, "reorder_playlist_item"))
    app.post(f"{base}/smart")(_named(create_smart_ep, media_type, "create_smart_playlist"))
    app.put(f"{base}/smart")(_named(update_smart_ep, media_type, "update_smart_rules"))


def register_todo_state_route(app: Any, cache_dir: Path, media_type: str) -> None:
    """``POST /api/<media>/todos/state``."""
    from fastapi import HTTPException

    def todo_state_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.streaming.core.issue_registry import summarize_todos, update_todo_state_action

        todo_key = str(payload.get("todo_key") or "").strip()
        action = str(payload.get("action") or "").strip().lower()
        if not todo_key:
            raise HTTPException(status_code=400, detail="todo_key is required")
        if action not in {"acknowledge", "snooze", "clear"}:
            raise HTTPException(status_code=400, detail="action must be acknowledge, snooze or clear")
        result = update_todo_state_action(
            cache_dir,
            todo_key=todo_key,
            action=action,
            reason=str(payload.get("reason") or "").strip(),
            seconds=int(payload.get("seconds") or 3600),
        )
        if not bool(result.get("ok", False)):
            detail = str(result.get("message") or "Task state update failed")
            raise HTTPException(status_code=404 if result.get("state") == "missing" else 400, detail=detail)
        return {"ok": True, "result": result, "todos": summarize_todos(cache_dir)}

    app.post(f"/api/{media_type}/todos/state")(_named(todo_state_ep, media_type, "todo_state"))


def register_audit_entries_route(app: Any, audit_dir: Path, media_type: str) -> None:
    """``GET /api/<media>/audit`` (read-only list)."""

    def audit_entries_ep(
        limit: int = 200,
        path_filter: str = "",
        action_filter: str = "",
        include_undone: bool = True,
    ) -> dict[str, object]:
        from hometools.streaming.core.audit_log import load_entries

        entries = load_entries(
            audit_dir,
            limit=limit,
            path_filter=path_filter,
            action_filter=action_filter,
            include_undone=include_undone,
        )
        return {"items": entries, "total": len(entries)}

    app.get(f"/api/{media_type}/audit")(_named(audit_entries_ep, media_type, "audit_entries"))


def register_reveal_route(
    app: Any,
    library_dir: Path,
    media_type: str,
    resolver: Callable[[Path, str], Path],
) -> None:
    """``POST /api/<media>/reveal``."""
    from fastapi import HTTPException

    def reveal_ep(payload: dict[str, object]) -> dict[str, object]:
        from hometools.utils import reveal_in_explorer

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        try:
            file_path = resolver(library_dir, path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"ok": True, "path": str(file_path.resolve()), "revealed": reveal_in_explorer(file_path)}

    app.post(f"/api/{media_type}/reveal")(_named(reveal_ep, media_type, "reveal"))


def register_delete_file_route(
    app: Any,
    library_dir: Path,
    audit_dir: Path,
    media_type: str,
    resolver: Callable[[Path, str], Path],
    on_changed: Callable[[], None],
) -> None:
    """``POST /api/<media>/delete-file`` (send to trash + audit entry)."""
    from fastapi import HTTPException

    def delete_file_ep(payload: dict[str, object]) -> dict[str, object]:
        import logging

        from hometools.streaming.core.audit_log import log_file_delete
        from hometools.utils import send_to_trash

        path = str(payload.get("path") or "").strip()
        if not path:
            raise HTTPException(status_code=400, detail="path is required")
        try:
            file_path = resolver(library_dir, path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            trash_dest = send_to_trash(file_path)
        except Exception as exc:
            logging.getLogger(__name__).exception("Failed to delete file %s", file_path)
            raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc
        entry = log_file_delete(audit_dir, server=media_type, path=path, trash_path=trash_dest)
        on_changed()
        return {"ok": True, "entry_id": entry.entry_id}

    app.post(f"/api/{media_type}/delete-file")(_named(delete_file_ep, media_type, "delete_file"))


def register_index_routes(
    app: Any,
    *,
    library_dir: Path,
    cache_dir: Path,
    safe_mode: bool,
    media_type: str,
    api_path: str,
    items_name: str,
    default_sort: str,
    suffixes: Any,
    stream_url_prefix: str,
    index_cache: Any,
    build_index: Callable[..., list[Any]],
    query_fn: Callable[..., list[Any]],
    list_artists_fn: Callable[[list[Any]], Any],
) -> None:
    """Catalog list (``api_path``), ``POST /api/<media>/refresh``, ``GET /api/<media>/status``."""
    import logging
    import time

    from hometools.streaming.core.catalog import quick_folder_scan
    from hometools.streaming.core.server_utils import build_index_status_payload

    log = logging.getLogger(__name__)
    # Cache quick-scan results so polls during index build don't re-walk the filesystem.
    quick_cache: dict[str, Any] = {"items": [], "at": 0.0}

    def _query_echo(q: str | None, artist: str | None, sort: str) -> dict[str, str]:
        return {"q": q or "", "artist": artist or "all", "sort": sort}

    def items_ep(q: str | None = None, artist: str | None = None, sort: str = default_sort) -> dict[str, object]:
        t0 = time.monotonic()
        log.info("GET %s — start (q=%r, artist=%r, sort=%r)", api_path, q, artist, sort)

        def _unavailable(msg: str) -> dict[str, object]:
            log.warning("GET %s — library not accessible: %s", api_path, msg)
            return {
                "library_dir": str(library_dir),
                "count": 0,
                "items": [],
                "artists": [],
                "error": msg,
                "query": _query_echo(q, artist, sort),
            }

        if safe_mode:
            ok, msg = check_library_accessible(library_dir)
            if not ok:
                return _unavailable(msg)
            items = build_index(library_dir, cache_dir=None)
            filtered = query_fn(items, q=q, artist=artist, sort_by=sort)
            log.info(
                "GET %s — SAFE MODE returned %d/%d items in %.1fs",
                api_path,
                len(filtered),
                len(items),
                time.monotonic() - t0,
            )
            return {
                "library_dir": str(library_dir),
                "count": len(filtered),
                "items": [i.to_dict() for i in filtered],
                "artists": list_artists_fn(items),
                "safe_mode": True,
                "query": _query_echo(q, artist, sort),
            }
        cache_t0 = time.monotonic()
        refresh_started = index_cache.ensure_background_refresh(library_dir, cache_dir=cache_dir)
        items = index_cache.get_cached(library_dir, cache_dir=cache_dir)
        building = index_cache.is_building()
        cache_elapsed = time.monotonic() - cache_t0
        if building and not items:
            ok, msg = check_library_accessible(library_dir)
            if not ok:
                return _unavailable(msg)
            cache_status = index_cache.status(library_dir, cache_dir=cache_dir)
            status_payload = build_index_status_payload(
                library_dir=library_dir,
                item_label=media_type,
                library_ok=True,
                library_message="ok",
                cache_status=cache_status,
            )
            now = time.monotonic()
            if quick_cache["items"] and (now - quick_cache["at"]) < 30.0:
                quick_items = quick_cache["items"]
            else:
                quick_items = quick_folder_scan(
                    library_dir,
                    suffixes=suffixes,
                    media_type=media_type,
                    stream_url_prefix=stream_url_prefix,
                )
                quick_cache["items"] = quick_items
                quick_cache["at"] = now
            filtered = query_fn(quick_items, q=q, artist=artist, sort_by=sort)
            log.info(
                "GET %s — quick scan %d items in %.2fs (refresh_started=%s, status=%s)",
                api_path,
                len(quick_items),
                time.monotonic() - cache_t0,
                refresh_started,
                status_payload["detail"],
            )
            return {
                "count": len(filtered),
                "items": [i.to_dict() for i in filtered],
                "artists": list_artists_fn(quick_items),
                "refreshing": True,
                **status_payload,
                "query": _query_echo(q, artist, sort),
            }
        query_t0 = time.monotonic()
        filtered = query_fn(items, q=q, artist=artist, sort_by=sort)
        query_elapsed = time.monotonic() - query_t0
        cache_status = index_cache.status(library_dir, cache_dir=cache_dir)
        build_detail = (
            build_index_status_payload(
                library_dir=library_dir,
                item_label=media_type,
                library_ok=True,
                library_message="ok",
                cache_status=cache_status,
            )["detail"]
            if building
            else ""
        )
        log.info(
            "GET %s — %d/%d items in %.1fs (cache=%.2fs, query=%.2fs, refresh_started=%s, building=%s, q=%r, artist=%r, sort=%r)",
            api_path,
            len(filtered),
            len(items),
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
            "library_dir": str(library_dir),
            "count": len(filtered),
            "items": [i.to_dict() for i in filtered],
            "artists": list_artists_fn(items),
            "refreshing": building,
            "cache": cache_status,
            "detail": build_detail,
            "query": _query_echo(q, artist, sort),
        }

    def refresh_ep() -> dict[str, object]:
        """Invalidate the index cache and trigger a fresh rebuild from the filesystem."""
        index_cache.invalidate()
        quick_cache["items"] = []
        quick_cache["at"] = 0.0
        index_cache.ensure_background_refresh(library_dir, cache_dir=cache_dir)
        return {"ok": True, "detail": "Refresh started"}

    def status_ep() -> dict[str, object]:
        from hometools.streaming.core.issue_registry import summarize_issue_and_todos

        ok, msg = check_library_accessible(library_dir)
        cache_status = (
            {
                "label": f"{media_type}-index",
                "building": False,
                "cached_count": 0,
                "fresh": False,
                "ttl_seconds": 0,
                "cache_age_seconds": None,
                "library_dir": str(library_dir),
                "snapshot_path": "",
                "snapshot_exists": False,
                "build_running_for_seconds": None,
                "last_build_started_at": None,
                "last_build_finished_at": None,
                "last_build_duration_seconds": None,
                "last_build_reason": "safe-mode",
                "last_error": "",
            }
            if safe_mode
            else index_cache.status(library_dir, cache_dir=cache_dir)
        )
        summary = summarize_issue_and_todos(cache_dir)
        return build_index_status_payload(
            library_dir=library_dir,
            item_label=media_type,
            library_ok=ok,
            library_message="Safe mode active — no cache snapshot or thumbnail warmup" if safe_mode else msg,
            cache_status=cache_status,
            issues_summary=summary["issues"],
            todo_summary=summary["todos"],
        )

    app.get(api_path)(_named(items_ep, media_type, items_name))
    app.post(f"/api/{media_type}/refresh")(_named(refresh_ep, media_type, "refresh"))
    app.get(f"/api/{media_type}/status")(_named(status_ep, media_type, "status"))


def register_thumb_route(app: Any, cache_dir: Path, media_type: str, *, allow_sprite: bool = False) -> None:
    """``GET /thumb`` — ``size=lg`` (480px); ``size=sprite`` only if *allow_sprite*."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    def thumb(path: str, size: str = "sm") -> FileResponse:
        from urllib.parse import unquote

        from hometools.streaming.core import thumbnailer

        relative_path = unquote(path)
        if size == "lg":
            thumb_path = thumbnailer.get_thumbnail_lg_path(cache_dir, media_type, relative_path)
        elif size == "sprite" and allow_sprite:
            thumb_path = thumbnailer.get_sprite_path(cache_dir, relative_path)
        else:
            thumb_path = thumbnailer.get_thumbnail_path(cache_dir, media_type, relative_path)
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        return FileResponse(thumb_path, media_type="image/jpeg")

    app.get("/thumb")(thumb)
