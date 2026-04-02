"""User-created playlists for the streaming servers.

Stores named playlists of media items (by relative_path).  Each server
(audio / video) maintains its own playlist file to avoid cross-server
collisions.

Storage file: ``<cache_dir>/playlists/<server>.json``

Storage format (v2)::

    {
      "revision": 42,
      "playlists": [ {id, name, created, updated_at, items}, ... ]
    }

Legacy format (v1, bare array) is transparently migrated on first write.

Thread-safe: all reads/writes are protected by a module-level lock.
Atomic writes via ``NamedTemporaryFile`` + ``replace``.
Public functions never raise; they return sensible defaults on failure.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_PLAYLISTS_DIR = "playlists"
_MAX_PLAYLISTS = 50
_MAX_ITEMS_PER_PLAYLIST = 500

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _playlists_path(cache_dir: Path, server: str) -> Path:
    """Return the on-disk path for the playlists JSON file."""
    return cache_dir / _PLAYLISTS_DIR / f"{server}.json"


def _changelog_path(cache_dir: Path, server: str) -> Path:
    """Return the on-disk path for the changelog JSONL file."""
    return cache_dir / _PLAYLISTS_DIR / f"changelog_{server}.jsonl"


def _read_raw(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Read playlists + revision from disk (caller must hold _lock).

    Returns ``(playlists, revision)``.  Transparently handles both v1
    (bare array) and v2 (envelope with revision) formats.
    """
    try:
        if not path.exists():
            return [], 0
        data = json.loads(path.read_text(encoding="utf-8"))
        # v2 envelope format
        if isinstance(data, dict):
            playlists = data.get("playlists", [])
            revision = int(data.get("revision", 0))
            return (playlists if isinstance(playlists, list) else []), revision
        # v1 legacy: bare array
        if isinstance(data, list):
            return data, 0
        return [], 0
    except Exception:
        logger.debug("Failed to read playlists from %s", path, exc_info=True)
        return [], 0


def _write_raw(path: Path, playlists: list[dict[str, Any]], revision: int) -> None:
    """Atomically write playlists to disk in v2 envelope format (caller must hold _lock)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope: dict[str, Any] = {
            "revision": revision,
            "playlists": playlists,
        }
        with NamedTemporaryFile(
            mode="w",
            suffix=".json",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(envelope, tmp, ensure_ascii=False, indent=2)
            tmp_path_obj = Path(tmp.name)
        tmp_path_obj.replace(path)
    except Exception:
        logger.debug("Failed to write playlists to %s", path, exc_info=True)


def _now_iso() -> str:
    """Return the current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


def _append_changelog(
    cache_dir: Path,
    server: str,
    *,
    action: str,
    playlist_id: str = "",
    detail: str = "",
) -> None:
    """Append an entry to the playlist changelog JSONL (best-effort)."""
    try:
        path = _changelog_path(cache_dir, server)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": _now_iso(),
            "action": action,
            "playlist_id": playlist_id,
            "detail": detail,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logger.debug("Failed to append changelog for %s/%s", server, action, exc_info=True)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def load_playlists(cache_dir: Path, server: str) -> list[dict[str, Any]]:
    """Load all saved playlists for *server* (``audio`` or ``video``).

    Each playlist dict has keys ``id``, ``name``, ``created``, ``updated_at``,
    ``items``.  ``items`` is a list of relative-path strings.
    Returns ``[]`` on any error.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, _rev = _read_raw(path)
        return playlists


def get_playlist(cache_dir: Path, server: str, playlist_id: str) -> dict[str, Any] | None:
    """Return a single playlist by *playlist_id*, or ``None`` if not found."""
    playlists = load_playlists(cache_dir, server)
    for pl in playlists:
        if pl.get("id") == playlist_id:
            return pl
    return None


def get_revision(cache_dir: Path, server: str) -> int:
    """Return the current playlist revision number (0 if none saved yet).

    Lightweight — reads the file but only extracts the revision counter.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        _playlists, revision = _read_raw(path)
        return revision


def load_playlists_with_revision(cache_dir: Path, server: str) -> tuple[list[dict[str, Any]], int]:
    """Load all playlists together with the current revision number.

    Returns ``(playlists, revision)``.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        return _read_raw(path)


# ---------------------------------------------------------------------------
# Create / Delete
# ---------------------------------------------------------------------------


def create_playlist(
    cache_dir: Path,
    server: str,
    *,
    name: str,
) -> dict[str, Any]:
    """Create a new empty playlist and return it.

    Returns the newly created playlist dict.  If there are already
    ``_MAX_PLAYLISTS`` playlists, the oldest one is silently removed.
    """
    path = _playlists_path(cache_dir, server)
    now = _now_iso()

    new_pl: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "name": name.strip() or "Playlist",
        "created": now,
        "updated_at": now,
        "items": [],
    }

    with _lock:
        playlists, revision = _read_raw(path)
        playlists.insert(0, new_pl)
        if len(playlists) > _MAX_PLAYLISTS:
            playlists = playlists[:_MAX_PLAYLISTS]
        revision += 1
        _write_raw(path, playlists, revision)

    _append_changelog(cache_dir, server, action="create", playlist_id=new_pl["id"], detail=name.strip())
    return new_pl


def delete_playlist(
    cache_dir: Path,
    server: str,
    playlist_id: str,
) -> list[dict[str, Any]]:
    """Delete a playlist by *playlist_id* and return the updated list."""
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        playlists = [pl for pl in playlists if pl.get("id") != playlist_id]
        revision += 1
        _write_raw(path, playlists, revision)
        _append_changelog(cache_dir, server, action="delete", playlist_id=playlist_id)
        return playlists


def rename_playlist(
    cache_dir: Path,
    server: str,
    playlist_id: str,
    *,
    name: str,
) -> dict[str, Any] | None:
    """Rename a playlist.  Returns the updated playlist or ``None``."""
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                pl["name"] = name.strip() or pl.get("name", "Playlist")
                pl["updated_at"] = _now_iso()
                target = pl
                break
        if target is not None:
            revision += 1
            _write_raw(path, playlists, revision)
            _append_changelog(cache_dir, server, action="rename", playlist_id=playlist_id, detail=name.strip())
        return target


# ---------------------------------------------------------------------------
# Item management
# ---------------------------------------------------------------------------


def add_item(
    cache_dir: Path,
    server: str,
    playlist_id: str,
    *,
    relative_path: str,
) -> dict[str, Any] | None:
    """Add *relative_path* to the playlist.  Returns the updated playlist.

    Duplicates within the same playlist are silently ignored.
    Returns ``None`` if the playlist does not exist.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                items = pl.get("items", [])
                if relative_path not in items:
                    if len(items) >= _MAX_ITEMS_PER_PLAYLIST:
                        target = pl
                        break
                    items.append(relative_path)
                    pl["items"] = items
                pl["updated_at"] = _now_iso()
                target = pl
                break
        if target is not None:
            revision += 1
            _write_raw(path, playlists, revision)
            _append_changelog(cache_dir, server, action="add_item", playlist_id=playlist_id, detail=relative_path)
        return target


def remove_item(
    cache_dir: Path,
    server: str,
    playlist_id: str,
    *,
    relative_path: str,
) -> dict[str, Any] | None:
    """Remove *relative_path* from the playlist.  Returns the updated playlist.

    Returns ``None`` if the playlist does not exist.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                items = pl.get("items", [])
                pl["items"] = [p for p in items if p != relative_path]
                pl["updated_at"] = _now_iso()
                target = pl
                break
        if target is not None:
            revision += 1
            _write_raw(path, playlists, revision)
            _append_changelog(cache_dir, server, action="remove_item", playlist_id=playlist_id, detail=relative_path)
        return target


def move_item(
    cache_dir: Path,
    server: str,
    playlist_id: str,
    *,
    relative_path: str,
    direction: str,
) -> dict[str, Any] | None:
    """Move *relative_path* up or down within the playlist.

    *direction* must be ``"up"`` (towards index 0) or ``"down"``.
    If the item is already at the boundary, the list stays unchanged.
    Returns the updated playlist, or ``None`` if playlist/item not found.
    """
    if direction not in ("up", "down"):
        return None
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                items = pl.get("items", [])
                try:
                    idx = items.index(relative_path)
                except ValueError:
                    return None
                new_idx = idx - 1 if direction == "up" else idx + 1
                if 0 <= new_idx < len(items):
                    items[idx], items[new_idx] = items[new_idx], items[idx]
                    pl["items"] = items
                pl["updated_at"] = _now_iso()
                target = pl
                break
        if target is not None:
            revision += 1
            _write_raw(path, playlists, revision)
            _append_changelog(cache_dir, server, action="move_item", playlist_id=playlist_id, detail=f"{relative_path} {direction}")
        return target


def reorder_item(
    cache_dir: Path,
    server: str,
    playlist_id: str,
    *,
    relative_path: str,
    to_index: int,
) -> dict[str, Any] | None:
    """Move *relative_path* to position *to_index* within the playlist.

    *to_index* is clamped to ``[0, len(items)-1]``.  If the item is
    already at *to_index* the list stays unchanged (no-op write).
    Returns the updated playlist, or ``None`` if playlist/item not found.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists, revision = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                items = pl.get("items", [])
                try:
                    old_idx = items.index(relative_path)
                except ValueError:
                    return None
                clamped = max(0, min(to_index, len(items) - 1))
                if old_idx != clamped:
                    items.pop(old_idx)
                    items.insert(clamped, relative_path)
                    pl["items"] = items
                pl["updated_at"] = _now_iso()
                target = pl
                break
        if target is not None:
            revision += 1
            _write_raw(path, playlists, revision)
            _append_changelog(cache_dir, server, action="reorder_item", playlist_id=playlist_id, detail=f"{relative_path} → {to_index}")
        return target
