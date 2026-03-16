"""Catalog helpers for the video streaming prototype.

Built on top of :mod:`hometools.streaming.core` — same query/sort/filter
logic as the audio streaming component.

INSTRUCTIONS (local):
- ``_title_from_filename`` strips codec/resolution tags. Keep the regex list
  updated when new common tags appear. Test via ``test_streaming_video.py``.
- ``_folder_as_artist`` uses the first subfolder as category. Videos at the
  library root get ``artist=""``.
- Default sort is **title** (not artist) because video folders are less
  meaningful than music artists.
- Thumbnail lookups are **non-blocking**: ``build_video_index`` only checks
  the on-disk cache.  Background generation is triggered separately via
  ``start_background_thumbnail_generation(collect_thumbnail_work(...))``.
"""

from __future__ import annotations

import re
from pathlib import Path

from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists
from hometools.streaming.core.catalog import query_items as query_videos
from hometools.streaming.core.catalog import sort_items as sort_videos
from hometools.streaming.core.models import MediaItem, encode_relative_path
from hometools.streaming.core.server_utils import safe_resolve
from hometools.streaming.core.thumbnailer import check_thumbnail_cached
from hometools.utils import get_files_in_folder

__all__ = [
    "MediaItem",
    "build_video_index",
    "collect_thumbnail_work",
    "encode_relative_path",
    "list_artists",
    "query_videos",
    "sort_videos",
]


def _title_from_filename(stem: str) -> str:
    """Extract a human-readable title from a video filename stem.

    Strips common codec / resolution tags and normalises separators.
    """
    # Replace dots and underscores used as word separators
    title = re.sub(r"[._]", " ", stem)
    # Strip resolution, codec, source tags
    title = re.sub(r"\b(1080|720|480|2160|4k)p?\b", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\b(x264|x265|h\.?264|h\.?265|hevc|avc|BluRay|BDRip|WEBRip|WEB-DL|HDRip|DVDRip|DD5\.?1|AAC|DTS)\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\[.*?]", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    # Collapse whitespace
    title = re.sub(r"\s{2,}", " ", title).strip()
    return title or stem


def _folder_as_artist(file_path: Path, library_root: Path) -> str:
    """Use the first directory level below the library root as 'artist' (folder name)."""
    try:
        relative = safe_resolve(file_path).relative_to(safe_resolve(library_root))
        parts = relative.parts
        if len(parts) > 1:
            return parts[0]
    except ValueError:
        pass
    return ""


def build_video_index(library_dir: Path, *, cache_dir: Path | None = None) -> list[MediaItem]:
    """Build a read-only video index from a local video library.

    Thumbnail URLs are only included when a cached thumbnail already exists
    on disk — no extraction is attempted here so startup stays fast.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    items: list[MediaItem] = []

    for video_file in get_files_in_folder(root, suffix_accepted=VIDEO_SUFFIX):
        relative_path = safe_resolve(video_file).relative_to(root).as_posix()
        title = _title_from_filename(video_file.stem)
        folder = _folder_as_artist(video_file, root)

        thumbnail_url = ""
        if cache_dir is not None:
            thumb = check_thumbnail_cached(cache_dir, "video", relative_path)
            if thumb is not None:
                thumbnail_url = f"/thumb?path={encode_relative_path(relative_path)}"

        items.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=folder,
                stream_url=f"/video/stream?path={encode_relative_path(relative_path)}",
                media_type="video",
                thumbnail_url=thumbnail_url,
            )
        )

    return sort_videos(items, sort_by="title")


def collect_thumbnail_work(
    library_dir: Path,
    cache_dir: Path,
) -> list[tuple[Path, Path, str, str]]:
    """Return a list of ``(media_path, cache_dir, media_type, relative_path)``
    tuples for all video files in the library — ready for
    :func:`~hometools.streaming.core.thumbnailer.start_background_thumbnail_generation`.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    work: list[tuple[Path, Path, str, str]] = []

    for video_file in get_files_in_folder(root, suffix_accepted=VIDEO_SUFFIX):
        relative_path = safe_resolve(video_file).relative_to(root).as_posix()
        work.append((video_file, cache_dir, "video", relative_path))

    return work
