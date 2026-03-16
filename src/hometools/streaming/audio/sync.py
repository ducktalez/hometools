"""Manual NAS-to-library sync helpers for the audio streaming prototype."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from hometools.utils import get_audio_files_in_folder, path_make_dir


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


def plan_audio_sync(source_root: Path, target_root: Path) -> list[SyncOperation]:
    """Plan copy operations for new or changed audio files."""
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"Audio source directory does not exist: {source_root}")

    source_root = source_root.resolve()
    target_root = target_root.resolve()
    operations: list[SyncOperation] = []

    for source in get_audio_files_in_folder(source_root):
        relative_path = source.resolve().relative_to(source_root)
        destination = target_root / relative_path
        reason = copy_reason(source, destination)
        if reason:
            operations.append(
                SyncOperation(
                    source=source,
                    destination=destination,
                    reason=reason,
                )
            )

    return operations


def execute_sync_plan(operations: list[SyncOperation]) -> int:
    """Execute a planned set of copy operations."""
    for operation in operations:
        path_make_dir(operation.destination)
        shutil.copy2(operation.source, operation.destination)
    return len(operations)


def sync_audio_library(source_root: Path, target_root: Path, dry_run: bool = False) -> list[SyncOperation]:
    """Synchronize new or changed audio files from source to target."""
    operations = plan_audio_sync(source_root, target_root)
    if dry_run:
        return operations
    execute_sync_plan(operations)
    return operations

