"""PWA Shortcuts persistence for the streaming servers.

Stores user-defined shortcuts (favorites) for quick access from the
home screen.  Each shortcut maps a media item's relative path to a
display name and optional icon URL.

Storage file: ``<cache_dir>/shortcuts/<server>.json``
(separate files for audio and video to avoid conflicts).

Thread-safe: all reads/writes are protected by a module-level lock.
Atomic writes via ``NamedTemporaryFile`` + ``replace``.
Public functions never raise; they return sensible defaults on failure.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_SHORTCUTS_DIR = "shortcuts"
_MAX_SHORTCUTS = 20  # PWA manifest supports max ~20 shortcuts on most platforms

_lock = threading.Lock()


def _shortcuts_path(cache_dir: Path, server: str) -> Path:
    """Return the on-disk path for the shortcuts JSON file."""
    return cache_dir / _SHORTCUTS_DIR / f"{server}.json"


def load_shortcuts(cache_dir: Path, server: str) -> list[dict[str, Any]]:
    """Load all saved shortcuts for *server* (``audio`` or ``video``).

    Returns a list of dicts with keys ``id``, ``title``, ``url``, ``icon``.
    Returns ``[]`` on any error.
    """
    path = _shortcuts_path(cache_dir, server)
    try:
        with _lock:
            if not path.exists():
                return []
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return []
    except Exception:
        logger.debug("Failed to load shortcuts from %s", path, exc_info=True)
        return []


def save_shortcut(
    cache_dir: Path,
    server: str,
    *,
    item_id: str,
    title: str,
    url: str,
    icon: str = "",
) -> list[dict[str, Any]]:
    """Add or update a shortcut and return the updated list.

    If a shortcut with the same *item_id* already exists, it is updated.
    Newest shortcuts are prepended.  List is capped at ``_MAX_SHORTCUTS``.
    """
    shortcuts = load_shortcuts(cache_dir, server)

    entry: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "url": url,
        "icon": icon,
    }

    # Remove existing entry with same id (if any)
    shortcuts = [s for s in shortcuts if s.get("id") != item_id]
    # Prepend new entry
    shortcuts.insert(0, entry)
    # Cap list
    shortcuts = shortcuts[:_MAX_SHORTCUTS]

    _write_shortcuts(cache_dir, server, shortcuts)
    return shortcuts


def remove_shortcut(cache_dir: Path, server: str, item_id: str) -> list[dict[str, Any]]:
    """Remove a shortcut by *item_id* and return the updated list."""
    shortcuts = load_shortcuts(cache_dir, server)
    shortcuts = [s for s in shortcuts if s.get("id") != item_id]
    _write_shortcuts(cache_dir, server, shortcuts)
    return shortcuts


def _write_shortcuts(cache_dir: Path, server: str, shortcuts: list[dict[str, Any]]) -> None:
    """Atomically write the shortcuts list to disk."""
    path = _shortcuts_path(cache_dir, server)
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                mode="w",
                suffix=".json",
                dir=path.parent,
                delete=False,
                encoding="utf-8",
            ) as tmp:
                json.dump(shortcuts, tmp, ensure_ascii=False, indent=2)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)
    except Exception:
        logger.debug("Failed to write shortcuts to %s", path, exc_info=True)
