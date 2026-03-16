"""Generic catalog helpers shared by audio and video streaming.

INSTRUCTIONS (local):
- All functions accept ``list[MediaItem]`` — never audio- or video-specific types.
- ``sort_items`` falls back to "artist" for unknown sort fields.
- ``list_artists`` excludes empty strings (video items without a folder).
- Add new sort fields to ``VALID_SORT_FIELDS`` and handle them in ``sort_items``.
"""

from __future__ import annotations

from hometools.streaming.core.models import MediaItem

VALID_SORT_FIELDS = {"artist", "title", "path"}


def sort_items(items: list[MediaItem], sort_by: str = "artist") -> list[MediaItem]:
    """Return items sorted by a supported field."""
    field = sort_by if sort_by in VALID_SORT_FIELDS else "artist"
    if field == "title":
        return sorted(items, key=lambda i: (i.title.casefold(), i.artist.casefold(), i.relative_path.casefold()))
    if field == "path":
        return sorted(items, key=lambda i: i.relative_path.casefold())
    return sorted(items, key=lambda i: (i.artist.casefold(), i.title.casefold(), i.relative_path.casefold()))


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
