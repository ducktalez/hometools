"""User-created playlists for the streaming servers.

Stores named playlists of media items (by relative_path).  Each server
(audio / video) maintains its own playlist file to avoid cross-server
collisions.

Storage file: ``<cache_dir>/playlists/<server>.json``

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


def _read_raw(path: Path) -> list[dict[str, Any]]:
    """Read playlists from disk (caller must hold _lock)."""
    try:
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        logger.debug("Failed to read playlists from %s", path, exc_info=True)
        return []


def _write_raw(path: Path, playlists: list[dict[str, Any]]) -> None:
    """Atomically write playlists to disk (caller must hold _lock)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            suffix=".json",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(playlists, tmp, ensure_ascii=False, indent=2)
            tmp_path_obj = Path(tmp.name)
        tmp_path_obj.replace(path)
    except Exception:
        logger.debug("Failed to write playlists to %s", path, exc_info=True)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def load_playlists(cache_dir: Path, server: str) -> list[dict[str, Any]]:
    """Load all saved playlists for *server* (``audio`` or ``video``).

    Each playlist dict has keys ``id``, ``name``, ``created``, ``items``.
    ``items`` is a list of relative-path strings.
    Returns ``[]`` on any error.
    """
    path = _playlists_path(cache_dir, server)
    with _lock:
        return _read_raw(path)


def get_playlist(cache_dir: Path, server: str, playlist_id: str) -> dict[str, Any] | None:
    """Return a single playlist by *playlist_id*, or ``None`` if not found."""
    playlists = load_playlists(cache_dir, server)
    for pl in playlists:
        if pl.get("id") == playlist_id:
            return pl
    return None


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

    new_pl: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "name": name.strip() or "Playlist",
        "created": datetime.now(timezone.utc).isoformat(),
        "items": [],
    }

    with _lock:
        playlists = _read_raw(path)
        playlists.insert(0, new_pl)
        if len(playlists) > _MAX_PLAYLISTS:
            playlists = playlists[:_MAX_PLAYLISTS]
        _write_raw(path, playlists)

    return new_pl


def delete_playlist(
    cache_dir: Path,
    server: str,
    playlist_id: str,
) -> list[dict[str, Any]]:
    """Delete a playlist by *playlist_id* and return the updated list."""
    path = _playlists_path(cache_dir, server)
    with _lock:
        playlists = _read_raw(path)
        playlists = [pl for pl in playlists if pl.get("id") != playlist_id]
        _write_raw(path, playlists)
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
        playlists = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                pl["name"] = name.strip() or pl.get("name", "Playlist")
                target = pl
                break
        if target is not None:
            _write_raw(path, playlists)
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
        playlists = _read_raw(path)
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
                target = pl
                break
        if target is not None:
            _write_raw(path, playlists)
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
        playlists = _read_raw(path)
        target = None
        for pl in playlists:
            if pl.get("id") == playlist_id:
                items = pl.get("items", [])
                pl["items"] = [p for p in items if p != relative_path]
                target = pl
                break
        if target is not None:
            _write_raw(path, playlists)
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
        playlists = _read_raw(path)
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
                target = pl
                break
        if target is not None:
            _write_raw(path, playlists)
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
        playlists = _read_raw(path)
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
                target = pl
                break
        if target is not None:
            _write_raw(path, playlists)
        return target
