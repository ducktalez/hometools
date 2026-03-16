"""Shared media item model used by both audio and video streaming."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True, slots=True)
class MediaItem:
    """Universal read-only representation of a streamable media file.

    Used by both audio and video catalogs so that shared query/sort/sync
    logic only needs to be written once.
    """

    relative_path: str
    title: str
    artist: str          # empty string for video items without a known director
    stream_url: str
    media_type: str      # "audio" or "video"

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""
        return asdict(self)


def normalize_relative_path(relative_path: str | Path) -> str:
    """Normalize a relative path to a stable POSIX-style string."""
    if isinstance(relative_path, Path):
        return relative_path.as_posix()
    return str(relative_path).replace("\\", "/")


def encode_relative_path(relative_path: str | Path) -> str:
    """Encode a relative path for use in query parameters."""
    return quote(normalize_relative_path(relative_path), safe="")

