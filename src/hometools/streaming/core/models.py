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

    INSTRUCTIONS (local):
    - Frozen: never mutate, always create a new instance.
    - ``artist`` is overloaded: actual artist for audio, folder name for video.
      Core code must tolerate empty strings.
    - Add new fields at the end to keep backward compatibility with to_dict().
    - Every new field must be JSON-serializable (str/int/float/bool/None).
    """

    relative_path: str
    title: str
    artist: str  # audio: artist name, video: top-level folder (may be "")
    stream_url: str
    media_type: str  # "audio" or "video"
    thumbnail_url: str = ""  # URL to shadow-cached thumbnail (empty = no thumb)
    rating: float = 0.0  # 0.0–5.0 star rating (POPM for audio, 0.0 = unrated)
    season: int = 0  # series season number (0 = not a series episode)
    episode: int = 0  # series episode number (0 = not a series episode)
    mtime: float = 0.0  # file modification time (Unix timestamp, 0.0 = unknown)
    thumbnail_lg_url: str = ""  # URL to large (480 px) shadow-cached thumbnail

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
