"""User-added extra library folders (outside the main library root).

Each extra folder is exposed as a virtual top-level folder named *alias*:
``relative_path = "<alias>/<path inside folder>"``.  The alias prefix keeps
the ``relative_path`` contract (progress, thumbnails, playlists, ...) intact.

Storage: ``<cache_dir>/extra_folders/<media_type>.json``.  Original media
files are never touched.  Every public function is exception-safe.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

from hometools.streaming.core.server_utils._paths import safe_resolve

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_BAD_ALIAS_CHARS = re.compile(r'[\\/:*?"<>|]+')


def _store_path(cache_dir: Path, media_type: str) -> Path:
    return cache_dir / "extra_folders" / f"{media_type}.json"


def list_extra_folders(cache_dir: Path | None, media_type: str) -> list[dict[str, str]]:
    """Return ``[{"alias": ..., "path": ...}]``.  ``[]`` on any failure."""
    if cache_dir is None:
        return []
    try:
        p = _store_path(cache_dir, media_type)
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        out: list[dict[str, str]] = []
        for e in data.get("folders", []):
            alias = str(e.get("alias") or "").strip()
            path = str(e.get("path") or "").strip()
            if alias and path:
                out.append({"alias": alias, "path": path})
        return out
    except Exception:
        logger.debug("Could not read extra folders", exc_info=True)
        return []


def _save(cache_dir: Path, media_type: str, folders: list[dict[str, str]]) -> bool:
    try:
        p = _store_path(cache_dir, media_type)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"version": 1, "folders": folders}, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        logger.debug("Could not save extra folders", exc_info=True)
        return False


def extra_roots(cache_dir: Path | None, media_type: str) -> dict[str, Path]:
    """Map ``alias -> normalised root path`` (no filesystem I/O)."""
    return {e["alias"]: safe_resolve(Path(e["path"]).expanduser()) for e in list_extra_folders(cache_dir, media_type)}


def add_extra_folder(
    cache_dir: Path,
    media_type: str,
    path: str,
    alias: str = "",
    *,
    library_dir: Path | None = None,
) -> dict[str, str] | None:
    """Register *path*; return the stored entry or ``None`` if invalid.

    Rejects non-directories, duplicates and paths inside/equal to *library_dir*.
    The alias defaults to the folder name and is made unique.
    """
    try:
        raw = path.strip().strip('"')
        if not raw:
            return None
        root = safe_resolve(Path(raw).expanduser())
        if not root.is_dir():
            return None
        if library_dir is not None:
            lib = safe_resolve(library_dir)
            if root == lib or lib in root.parents:
                return None
        with _LOCK:
            folders = list_extra_folders(cache_dir, media_type)
            if any(safe_resolve(Path(f["path"])) == root for f in folders):
                return None
            base = _BAD_ALIAS_CHARS.sub(" ", alias or root.name or "Ordner").strip() or "Ordner"
            taken = {f["alias"].lower() for f in folders}
            name, n = base, 2
            while name.lower() in taken:
                name = f"{base} ({n})"
                n += 1
            entry = {"alias": name, "path": str(root)}
            folders.append(entry)
            return entry if _save(cache_dir, media_type, folders) else None
    except Exception:
        logger.debug("add_extra_folder failed", exc_info=True)
        return None


def remove_extra_folder(cache_dir: Path, media_type: str, alias: str) -> bool:
    """Unregister the folder with *alias*.  The folder on disk is untouched."""
    try:
        with _LOCK:
            folders = list_extra_folders(cache_dir, media_type)
            kept = [f for f in folders if f["alias"] != alias]
            if len(kept) == len(folders):
                return False
            return _save(cache_dir, media_type, kept)
    except Exception:
        logger.debug("remove_extra_folder failed", exc_info=True)
        return False


def split_extra_path(relative_path: str, roots: dict[str, Path]) -> tuple[Path, str] | None:
    """If *relative_path* starts with an extra alias → ``(root, sub_path)``."""
    rel = relative_path.replace("\\", "/").lstrip("/")
    head, _, tail = rel.partition("/")
    root = roots.get(head)
    if root is None or not tail:
        return None
    return root, tail
