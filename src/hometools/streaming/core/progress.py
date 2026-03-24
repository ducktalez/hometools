"""Playback progress persistence for the streaming servers.

Stores the last playback position per file in a JSON file inside the
shadow cache directory.  Both audio and video servers use the same storage
so that progress is shared across media types.

INSTRUCTIONS (local):
- Thread-safe: all reads/writes are protected by a module-level lock.
- Atomic writes via ``NamedTemporaryFile`` + ``replace``.
- Public functions never raise; they return sensible defaults on failure.
- Storage file: ``<cache_dir>/progress/playback_progress.json``.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_PROGRESS_DIR = "progress"
_PROGRESS_FILE = "playback_progress.json"
_VERSION = 1

_lock = threading.Lock()


def _progress_path(cache_dir: Path) -> Path:
    """Return the on-disk path for the progress JSON file."""
    return cache_dir / _PROGRESS_DIR / _PROGRESS_FILE


def save_progress(
    cache_dir: Path,
    relative_path: str,
    position_seconds: float,
    duration: float = 0.0,
) -> bool:
    """Persist playback position for *relative_path*.

    Returns ``True`` on success, ``False`` on any error.
    """
    if not relative_path:
        return False

    with _lock:
        try:
            data = _load_unlocked(cache_dir)
            data[relative_path] = {
                "position_seconds": round(position_seconds, 2),
                "duration": round(duration, 2),
                "timestamp": time.time(),
            }
            _save_unlocked(cache_dir, data)
            return True
        except Exception:
            logger.debug("Failed to save progress for %s", relative_path, exc_info=True)
            return False


def delete_progress(cache_dir: Path, relative_path: str) -> bool:
    """Remove stored progress for *relative_path*.

    Returns ``True`` if the entry was removed, ``False`` on error or
    when no entry existed.
    """
    if not relative_path:
        return False

    with _lock:
        try:
            data = _load_unlocked(cache_dir)
            if relative_path not in data:
                return False
            del data[relative_path]
            _save_unlocked(cache_dir, data)
            return True
        except Exception:
            logger.debug("Failed to delete progress for %s", relative_path, exc_info=True)
            return False


def load_progress(cache_dir: Path, relative_path: str) -> dict[str, Any] | None:
    """Load stored progress for *relative_path*.

    Returns the entry dict (``position_seconds``, ``duration``,
    ``timestamp``) or ``None`` when not found or on error.
    """
    if not relative_path:
        return None

    with _lock:
        try:
            data = _load_unlocked(cache_dir)
            entry = data.get(relative_path)
            if isinstance(entry, dict):
                return entry
            return None
        except Exception:
            logger.debug("Failed to load progress for %s", relative_path, exc_info=True)
            return None


def load_all_progress(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all stored progress entries.

    Returns a dict of ``{relative_path: entry}`` or an empty dict on error.
    """
    with _lock:
        try:
            return _load_unlocked(cache_dir)
        except Exception:
            logger.debug("Failed to load all progress", exc_info=True)
            return {}


def get_recent_progress(cache_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    """Return the *limit* most recently played items, newest first.

    Each entry is the stored progress dict plus a ``"relative_path"`` key.
    Items without a ``"timestamp"`` field are sorted last.
    """
    all_data = load_all_progress(cache_dir)
    entries = [{"relative_path": path, **entry} for path, entry in all_data.items() if isinstance(entry, dict)]
    entries.sort(key=lambda e: e.get("timestamp", 0.0), reverse=True)
    return entries[:limit]


# ---------------------------------------------------------------------------
# Internal helpers (must be called with _lock held)
# ---------------------------------------------------------------------------


def _load_unlocked(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Read the progress file.  Returns an empty dict on any error."""
    path = _progress_path(cache_dir)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("items"), dict):
            return raw["items"]
    except Exception:
        logger.debug("Could not parse progress file %s", path, exc_info=True)
    return {}


def _save_unlocked(cache_dir: Path, data: dict[str, dict[str, Any]]) -> None:
    """Atomically write the progress file."""
    path = _progress_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _VERSION, "items": data}
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
