"""Catalog helpers for the audio streaming prototype.

Built on top of :mod:`hometools.streaming.core` so that query, sort and
filter logic is shared with the video streaming component.

INSTRUCTIONS (local):
- ``AudioTrack`` is a legacy alias for ``MediaItem``. Use ``MediaItem`` in new code.
- ``build_audio_index`` uses ``audiofile_assume_artist_title`` from the tools
  package — if that function changes, the catalog output changes.
- Re-exports from core (``sort_tracks``, ``query_tracks``, ``list_artists``)
  are renamed wrappers so audio-specific call sites read naturally.
- Thumbnail lookups are **non-blocking**: ``build_audio_index`` only checks
  the on-disk cache.  Background generation is triggered separately via
  ``start_background_thumbnail_generation(collect_thumbnail_work(...))``.
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
from hometools.streaming.core.thumbnailer import check_thumbnail_cached
from hometools.utils import get_audio_files_in_folder

# Legacy alias so existing imports keep working
AudioTrack = MediaItem


def build_audio_index(library_dir: Path, *, cache_dir: Path | None = None) -> list[MediaItem]:
    """Build a read-only track index from a local audio library.

    Thumbnail URLs are only included when a cached thumbnail already exists
    on disk — no extraction is attempted here so startup stays fast.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    tracks: list[MediaItem] = []

    for audio_file in get_audio_files_in_folder(root):
        relative_path = safe_resolve(audio_file).relative_to(root).as_posix()
        artist, title = audiofile_assume_artist_title(audio_file)

        thumbnail_url = ""
        if cache_dir is not None:
            thumb = check_thumbnail_cached(cache_dir, "audio", relative_path)
            if thumb is not None:
                thumbnail_url = f"/thumb?path={encode_relative_path(relative_path)}"

        tracks.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=artist,
                stream_url=f"/audio/stream?path={encode_relative_path(relative_path)}",
                media_type="audio",
                thumbnail_url=thumbnail_url,
            )
        )

    return sort_tracks(tracks, sort_by="artist")


def collect_thumbnail_work(
    library_dir: Path, cache_dir: Path,
) -> list[tuple[Path, Path, str, str]]:
    """Return a list of ``(media_path, cache_dir, media_type, relative_path)``
    tuples for all audio files in the library — ready for
    :func:`~hometools.streaming.core.thumbnailer.start_background_thumbnail_generation`.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    work: list[tuple[Path, Path, str, str]] = []

    for audio_file in get_audio_files_in_folder(root):
        relative_path = safe_resolve(audio_file).relative_to(root).as_posix()
        work.append((audio_file, cache_dir, "audio", relative_path))

    return work

