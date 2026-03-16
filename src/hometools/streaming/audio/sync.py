"""Manual NAS-to-library sync helpers for the audio streaming prototype.

Delegates to :mod:`hometools.streaming.core.sync` for the actual copy logic.
"""

from __future__ import annotations

from pathlib import Path

from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.core.sync import SyncOperation, sync_library


def plan_audio_sync(source_root: Path, target_root: Path) -> list[SyncOperation]:
    """Plan copy operations for new or changed audio files."""
    from hometools.streaming.core.sync import plan_sync

    return plan_sync(source_root, target_root, AUDIO_SUFFIX)


def sync_audio_library(source_root: Path, target_root: Path, dry_run: bool = False) -> list[SyncOperation]:
    """Synchronize new or changed audio files from source to target."""
    return sync_library(source_root, target_root, AUDIO_SUFFIX, dry_run=dry_run)
