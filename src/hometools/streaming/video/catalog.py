"""Catalog helpers for the video streaming prototype.

Built on top of :mod:`hometools.streaming.core` — same query/sort/filter
logic as the audio streaming component.
"""

from __future__ import annotations

import re
from pathlib import Path

from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import (  # noqa: F401 – re-export
    list_artists,
    query_items as query_videos,
    sort_items as sort_videos,
)
from hometools.streaming.core.models import MediaItem, encode_relative_path  # noqa: F401
from hometools.utils import get_files_in_folder


def _title_from_filename(stem: str) -> str:
    """Extract a human-readable title from a video filename stem.

    Strips common codec / resolution tags and normalises separators.
    """
    # Replace dots and underscores used as word separators
    title = re.sub(r'[._]', ' ', stem)
    # Strip resolution, codec, source tags
    title = re.sub(r'\b(1080|720|480|2160|4k)p?\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b(x264|x265|h\.?264|h\.?265|hevc|avc|BluRay|BDRip|WEBRip|WEB-DL|HDRip|DVDRip|DD5\.?1|AAC|DTS)\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\[.*?]', '', title)
    title = re.sub(r'\(.*?\)', '', title)
    # Collapse whitespace
    title = re.sub(r'\s{2,}', ' ', title).strip()
    return title or stem


def _folder_as_artist(file_path: Path, library_root: Path) -> str:
    """Use the first directory level below the library root as 'artist' (folder name)."""
    try:
        relative = file_path.resolve().relative_to(library_root.resolve())
        parts = relative.parts
        if len(parts) > 1:
            return parts[0]
    except ValueError:
        pass
    return ""


def build_video_index(library_dir: Path) -> list[MediaItem]:
    """Build a read-only video index from a local video library."""
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = library_dir.resolve()
    items: list[MediaItem] = []

    for video_file in get_files_in_folder(root, suffix_accepted=VIDEO_SUFFIX):
        relative_path = video_file.resolve().relative_to(root).as_posix()
        title = _title_from_filename(video_file.stem)
        folder = _folder_as_artist(video_file, root)
        items.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=folder,
                stream_url=f"/video/stream?path={encode_relative_path(relative_path)}",
                media_type="video",
            )
        )

    return sort_videos(items, sort_by="title")

