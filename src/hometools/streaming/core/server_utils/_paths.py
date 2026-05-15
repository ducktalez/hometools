"""Path validation helpers (no filesystem I/O on resolve)."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote


def safe_resolve(p: Path) -> Path:
    """Normalise a path **without** filesystem I/O.

    ``Path.resolve()`` on Windows calls ``GetFinalPathNameByHandle`` which can
    hang indefinitely on unreachable UNC/SMB shares.  This function uses
    ``os.path.normpath`` + ``os.path.abspath`` instead — it resolves ``..``
    and ``.`` segments and makes the path absolute, but does **not** follow
    symlinks or touch the network.
    """
    return Path(os.path.normpath(os.path.abspath(str(p))))


def resolve_media_path(library_dir: Path, encoded_relative_path: str, allowed_suffixes: list[str]) -> Path:
    """Resolve and validate a requested media path inside a library root.

    Raises ValueError for path traversal or unsupported suffix, FileNotFoundError
    if the file does not exist on disk.
    """
    root = safe_resolve(library_dir)
    relative_path = Path(unquote(encoded_relative_path))
    candidate = safe_resolve(root / relative_path)

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path escapes the configured library.") from exc

    if not candidate.is_file():
        raise FileNotFoundError(f"Media file not found: {relative_path}")
    if candidate.suffix.lower() not in allowed_suffixes:
        raise ValueError(f"Unsupported suffix for streaming: {candidate.suffix}")

    return candidate
