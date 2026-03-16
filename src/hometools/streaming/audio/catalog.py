"""Catalog helpers for the audio streaming prototype.

Built on top of :mod:`hometools.streaming.core` so that query, sort and
filter logic is shared with the video streaming component.

INSTRUCTIONS (local):
- ``AudioTrack`` is a legacy alias for ``MediaItem``. Use ``MediaItem`` in new code.
- ``build_audio_index`` uses ``audiofile_assume_artist_title`` from the tools
  package — if that function changes, the catalog output changes.
- Re-exports from core (``sort_tracks``, ``query_tracks``, ``list_artists``)
  are renamed wrappers so audio-specific call sites read naturally.
"""

from __future__ import annotations

from pathlib import Path

from hometools.audio.metadata import audiofile_assume_artist_title
from hometools.streaming.core.catalog import (  # noqa: F401 – re-export
    list_artists,
    query_items as query_tracks,
    sort_items as sort_tracks,
)
from hometools.streaming.core.models import MediaItem, encode_relative_path  # noqa: F401
from hometools.streaming.core.server_utils import safe_resolve
from hometools.utils import get_audio_files_in_folder

# Legacy alias so existing imports keep working
AudioTrack = MediaItem


def build_audio_index(library_dir: Path) -> list[MediaItem]:
    """Build a read-only track index from a local audio library."""
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    tracks: list[MediaItem] = []

    for audio_file in get_audio_files_in_folder(root):
        relative_path = safe_resolve(audio_file).relative_to(root).as_posix()
        artist, title = audiofile_assume_artist_title(audio_file)
        tracks.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=artist,
                stream_url=f"/audio/stream?path={encode_relative_path(relative_path)}",
                media_type="audio",
            )
        )

    return sort_tracks(tracks, sort_by="artist")
