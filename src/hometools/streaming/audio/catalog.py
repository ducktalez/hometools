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

import logging
import time
from pathlib import Path

from hometools.audio.metadata import audiofile_assume_artist_title, get_genre, get_rating_stars
from hometools.streaming.core.catalog import list_artists
from hometools.streaming.core.catalog import query_items as query_tracks
from hometools.streaming.core.catalog import sort_items as sort_tracks
from hometools.streaming.core.models import MediaItem, encode_relative_path
from hometools.streaming.core.server_utils import safe_resolve
from hometools.streaming.core.thumbnailer import check_thumbnail_cached, check_thumbnail_lg_cached
from hometools.utils import get_audio_files_in_folder

# Legacy alias so existing imports keep working
AudioTrack = MediaItem

logger = logging.getLogger(__name__)

__all__ = [
    "AudioTrack",
    "MediaItem",
    "build_audio_index",
    "collect_thumbnail_work",
    "encode_relative_path",
    "list_artists",
    "query_tracks",
    "sort_tracks",
]


def build_audio_index(library_dir: Path, *, cache_dir: Path | None = None) -> list[MediaItem]:
    """Build a read-only track index from a local audio library.

    Thumbnail URLs are only included when a cached thumbnail already exists
    on disk — no extraction is attempted here so startup stays fast.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    t0 = time.monotonic()
    root = safe_resolve(library_dir)
    scan_t0 = time.monotonic()
    audio_files = get_audio_files_in_folder(root)
    scan_elapsed = time.monotonic() - scan_t0
    tracks: list[MediaItem] = []
    cached_thumbnails = 0

    logger.info(
        "Building audio index for %s — %d files discovered in %.2fs",
        root,
        len(audio_files),
        scan_elapsed,
    )

    for audio_file in audio_files:
        relative_path = safe_resolve(audio_file).relative_to(root).as_posix()
        artist, title = audiofile_assume_artist_title(audio_file)

        thumbnail_url = ""
        thumbnail_lg_url = ""
        if cache_dir is not None:
            thumb = check_thumbnail_cached(cache_dir, "audio", relative_path)
            if thumb is not None:
                cached_thumbnails += 1
                thumbnail_url = f"/thumb?path={encode_relative_path(relative_path)}"
            thumb_lg = check_thumbnail_lg_cached(cache_dir, "audio", relative_path)
            if thumb_lg is not None:
                thumbnail_lg_url = f"/thumb?path={encode_relative_path(relative_path)}&size=lg"

        # Rating: format-aware (MP3 POPM, M4A freeform atom, FLAC Vorbis comment)
        stars = get_rating_stars(audio_file)

        # Genre tag
        genre = get_genre(audio_file)

        try:
            file_mtime = audio_file.stat().st_mtime
        except OSError:
            file_mtime = 0.0

        tracks.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=artist,
                stream_url=f"/audio/stream?path={encode_relative_path(relative_path)}",
                media_type="audio",
                thumbnail_url=thumbnail_url,
                rating=stars,
                mtime=file_mtime,
                thumbnail_lg_url=thumbnail_lg_url,
                genre=genre,
            )
        )

    elapsed = time.monotonic() - t0
    logger.info(
        "Audio index built: %d items in %.1fs [scan=%.2fs, cached_thumbs=%d]",
        len(tracks),
        elapsed,
        scan_elapsed,
        cached_thumbnails,
    )
    return sort_tracks(tracks, sort_by="artist")


def collect_thumbnail_work(
    library_dir: Path,
    cache_dir: Path,
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
