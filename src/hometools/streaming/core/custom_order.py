"""Server-side persistence for custom item ordering (folder + favorites).

Stores user-defined sort orders per folder (or for the virtual ``__favorites__``
context) so that the custom arrangement survives browser-clear and works across
devices.

Storage layout::

    <cache_dir>/custom_order/<server>/<hash>.json

where ``<hash>`` is the MD5 hex-digest of the normalised folder path (or the
literal string ``__favorites__``).

Thread-safe: all reads/writes are protected by a module-level lock.
Atomic writes via ``NamedTemporaryFile`` + ``replace``.
Public functions never raise; they return sensible defaults on failure.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_ORDER_DIR = "custom_order"
_MAX_ITEMS = 5000

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _order_key(folder_path: str) -> str:
    """Return a filesystem-safe hash for the given folder path."""
    normalised = folder_path.strip().replace("\\", "/")
    return hashlib.md5(normalised.encode("utf-8")).hexdigest()


def _order_path(cache_dir: Path, server: str, folder_path: str) -> Path:
    """Return the on-disk path for the order JSON file."""
    return cache_dir / _ORDER_DIR / server / f"{_order_key(folder_path)}.json"


def _read_raw(path: Path) -> dict[str, Any]:
    """Read order data from disk (caller must hold ``_lock``)."""
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.debug("Failed to read custom order from %s", path, exc_info=True)
        return {}


def _write_raw(path: Path, data: dict[str, Any]) -> None:
    """Atomically write order data to disk (caller must hold ``_lock``)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            suffix=".json",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path_obj = Path(tmp.name)
        tmp_path_obj.replace(path)
    except Exception:
        logger.debug("Failed to write custom order to %s", path, exc_info=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_order(
    cache_dir: Path,
    server: str,
    folder_path: str,
) -> list[str]:
    """Load the custom item order for *folder_path*.

    Returns a list of ``relative_path`` strings in the user's preferred order,
    or an empty list if no custom order has been saved.
    """
    with _lock:
        path = _order_path(cache_dir, server, folder_path)
        data = _read_raw(path)
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        return items


def save_order(
    cache_dir: Path,
    server: str,
    folder_path: str,
    items: list[str],
) -> list[str]:
    """Persist the custom item order for *folder_path*.

    *items* is the full ordered list of ``relative_path`` strings.
    Returns the stored list (truncated to ``_MAX_ITEMS``).
    """
    clamped = items[:_MAX_ITEMS]
    with _lock:
        path = _order_path(cache_dir, server, folder_path)
        data = {
            "folder_path": folder_path,
            "items": clamped,
        }
        _write_raw(path, data)
    return clamped


def delete_order(
    cache_dir: Path,
    server: str,
    folder_path: str,
) -> bool:
    """Delete the custom order for *folder_path*.

    Returns ``True`` if the file was removed, ``False`` otherwise.
    """
    with _lock:
        path = _order_path(cache_dir, server, folder_path)
        try:
            if path.exists():
                path.unlink()
                return True
        except Exception:
            logger.debug("Failed to delete custom order %s", path, exc_info=True)
        return False
