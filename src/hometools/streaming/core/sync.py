"""Generic NAS-to-library sync helpers shared by audio and video streaming.

INSTRUCTIONS (local):
- Sync is **always** explicit (CLI command). Never auto-pull.
- ``plan_sync`` takes a suffix list so the same logic works for any media type.
- ``copy_reason`` returns None when no copy is needed — callers filter on truthiness.
- Uses ``shutil.copy2`` (preserves mtime) so that ``copy_reason`` can detect "source-newer".
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from hometools.utils import get_files_in_folder, path_make_dir


@dataclass(frozen=True, slots=True)
class SyncOperation:
    """Description of a file copy required to update the local library."""

    source: Path
    destination: Path
    reason: str


def copy_reason(source: Path, destination: Path) -> str | None:
    """Return why *source* should be copied to *destination*, or ``None``."""
    if not destination.exists():
        return "missing"
    source_stat = source.stat()
    destination_stat = destination.stat()
    if source_stat.st_size != destination_stat.st_size:
        return "size-changed"
    if int(source_stat.st_mtime) > int(destination_stat.st_mtime):
        return "source-newer"
    return None


def plan_sync(source_root: Path, target_root: Path, suffixes: list[str]) -> list[SyncOperation]:
    """Plan copy operations for new or changed media files with given suffixes."""
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    source_root = source_root.resolve()
    target_root = target_root.resolve()
    operations: list[SyncOperation] = []

    for source in get_files_in_folder(source_root, suffix_accepted=suffixes):
        relative_path = source.resolve().relative_to(source_root)
        destination = target_root / relative_path
        reason = copy_reason(source, destination)
        if reason:
            operations.append(SyncOperation(source=source, destination=destination, reason=reason))

    return operations


def execute_sync_plan(operations: list[SyncOperation]) -> int:
    """Execute a planned set of copy operations."""
    for op in operations:
        path_make_dir(op.destination)
        shutil.copy2(op.source, op.destination)
    return len(operations)


def sync_library(source_root: Path, target_root: Path, suffixes: list[str], dry_run: bool = False) -> list[SyncOperation]:
    """Synchronize new or changed media files from source to target."""
    operations = plan_sync(source_root, target_root, suffixes)
    if not dry_run:
        execute_sync_plan(operations)
    return operations

