"""Generic catalog helpers shared by audio and video streaming.

INSTRUCTIONS (local):
- All functions accept ``list[MediaItem]`` — never audio- or video-specific types.
- ``sort_items`` falls back to "artist" for unknown sort fields.
- ``list_artists`` excludes empty strings (video items without a folder).
- Add new sort fields to ``VALID_SORT_FIELDS`` and handle them in ``sort_items``.
- ``parse_season_episode`` is the single source of truth for extracting S/E
  numbers from filenames.  Both the streaming catalog and the video organizer
  should use it.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from hometools.streaming.core.models import MediaItem, encode_relative_path

logger = logging.getLogger(__name__)

VALID_SORT_FIELDS = {"artist", "title", "path"}

# ---------------------------------------------------------------------------
# Season / episode parsing
# ---------------------------------------------------------------------------

# Ordered list of patterns — first match wins.
_SEASON_EPISODE_PATTERNS: list[re.Pattern[str]] = [
    # S01E02, s1e3, S01E1034
    re.compile(r"S(\d{1,2})E(\d{1,4})", re.IGNORECASE),
    # 1x02, 01x03
    re.compile(r"(\d{1,2})x(\d{1,4})", re.IGNORECASE),
]


def parse_season_episode(filename: str) -> tuple[int, int]:
    """Extract season and episode numbers from a filename string.

    Tries common patterns (``S01E02``, ``1x02``) and returns ``(season, episode)``.
    Returns ``(0, 0)`` when no pattern matches — never raises.

    Parameters
    ----------
    filename:
        The filename stem (or full name) to parse.

    Examples
    --------
    >>> parse_season_episode("Breaking.Bad.S02E03.720p.mkv")
    (2, 3)
    >>> parse_season_episode("show.1x05.title.mp4")
    (1, 5)
    >>> parse_season_episode("Random Movie 2024.mp4")
    (0, 0)
    """
    for pattern in _SEASON_EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            try:
                return int(match.group(1)), int(match.group(2))
            except (ValueError, IndexError):
                continue
    return 0, 0


def sort_items(items: list[MediaItem], sort_by: str = "artist") -> list[MediaItem]:
    """Return items sorted by a supported field.

    Series episodes (``season > 0``) are sorted by ``(season, episode)``
    within their group so that ``S01E02`` always comes before ``S01E10``
    regardless of the title string.
    """
    field = sort_by if sort_by in VALID_SORT_FIELDS else "artist"
    if field == "title":
        # Series-aware title sort: non-series items sort by title first,
        # series items sort chronologically by (season, episode).
        return sorted(
            items,
            key=lambda i: (
                0 if (i.season == 0 and i.episode == 0) else 1,
                i.season,
                i.episode,
                i.title.casefold(),
                i.artist.casefold(),
                i.relative_path.casefold(),
            ),
        )
    if field == "path":
        return sorted(items, key=lambda i: i.relative_path.casefold())
    # Default: group by artist/folder, then season/episode, then title
    return sorted(
        items,
        key=lambda i: (
            i.artist.casefold(),
            i.season,
            i.episode,
            i.title.casefold(),
            i.relative_path.casefold(),
        ),
    )


def query_items(
    items: list[MediaItem],
    q: str | None = None,
    artist: str | None = None,
    sort_by: str = "artist",
) -> list[MediaItem]:
    """Filter and sort items by search text and optional artist."""
    needle = (q or "").strip().casefold()
    artist_filter = (artist or "").strip().casefold()

    filtered = items
    if artist_filter and artist_filter != "all":
        filtered = [i for i in filtered if i.artist.casefold() == artist_filter]
    if needle:
        filtered = [
            i for i in filtered if needle in i.artist.casefold() or needle in i.title.casefold() or needle in i.relative_path.casefold()
        ]
    return sort_items(filtered, sort_by=sort_by)


def list_artists(items: list[MediaItem]) -> list[str]:
    """Return unique non-empty artists sorted case-insensitively."""
    return sorted({i.artist for i in items if i.artist}, key=str.casefold)


def quick_folder_scan(
    library_dir: Path,
    *,
    suffixes: list[str] | set[str],
    media_type: str,
    stream_url_prefix: str,
) -> list[MediaItem]:
    """Fast directory scan for immediate folder display during index building.

    Creates minimal ``MediaItem`` instances from the filesystem without reading
    metadata or checking thumbnails.  Much faster than a full index build
    because it only does path manipulation after the directory walk.

    Parameters
    ----------
    library_dir:
        Root of the media library.
    suffixes:
        Accepted file suffixes (e.g. ``AUDIO_SUFFIX`` or ``VIDEO_SUFFIX``).
    media_type:
        ``"audio"`` or ``"video"``.
    stream_url_prefix:
        URL prefix for stream URLs (e.g. ``"/audio/stream"``).
    """
    from hometools.streaming.core.server_utils import safe_resolve
    from hometools.utils import get_files_in_folder

    if not library_dir.exists() or not library_dir.is_dir():
        return []

    t0 = time.monotonic()
    root = safe_resolve(library_dir)
    files = get_files_in_folder(root, suffix_accepted=suffixes)
    items: list[MediaItem] = []

    for f in files:
        relative_path = safe_resolve(f).relative_to(root).as_posix()
        parts = Path(relative_path).parts
        artist = parts[0] if len(parts) > 1 else ""
        title = f.stem
        stream_url = f"{stream_url_prefix}?path={encode_relative_path(relative_path)}"
        season, episode = parse_season_episode(f.name)
        items.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=artist,
                stream_url=stream_url,
                media_type=media_type,
                season=season,
                episode=episode,
            )
        )

    # Apply per-folder YAML overrides (title, season, episode, series_title)
    from hometools.streaming.core.media_overrides import apply_overrides

    items = apply_overrides(items, root)

    default_sort = "artist" if media_type == "audio" else "title"
    result = sort_items(items, sort_by=default_sort)
    elapsed = time.monotonic() - t0
    logger.info(
        "Quick folder scan: %d %s items in %.2fs (no metadata/thumbnails)",
        len(result),
        media_type,
        elapsed,
    )
    return result
