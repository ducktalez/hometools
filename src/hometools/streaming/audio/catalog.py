"""Catalog helpers for the audio streaming prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

from hometools.audio.metadata import audiofile_assume_artist_title
from hometools.utils import get_audio_files_in_folder

VALID_SORT_FIELDS = {"artist", "title", "path"}


@dataclass(frozen=True, slots=True)
class AudioTrack:
    """Simple read-only representation of a streamable audio track."""

    relative_path: str
    artist: str
    title: str
    stream_url: str

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


def sort_tracks(tracks: list[AudioTrack], sort_by: str = "artist") -> list[AudioTrack]:
    """Return tracks sorted by a supported field."""
    field = sort_by if sort_by in VALID_SORT_FIELDS else "artist"
    if field == "title":
        return sorted(
            tracks,
            key=lambda track: (
                track.title.casefold(),
                track.artist.casefold(),
                track.relative_path.casefold(),
            ),
        )
    if field == "path":
        return sorted(
            tracks,
            key=lambda track: track.relative_path.casefold(),
        )
    return sorted(
        tracks,
        key=lambda track: (
            track.artist.casefold(),
            track.title.casefold(),
            track.relative_path.casefold(),
        ),
    )


def query_tracks(
    tracks: list[AudioTrack],
    q: str | None = None,
    artist: str | None = None,
    sort_by: str = "artist",
) -> list[AudioTrack]:
    """Filter and sort tracks by search text and artist."""
    needle = (q or "").strip().casefold()
    artist_filter = (artist or "").strip().casefold()

    filtered = tracks
    if artist_filter and artist_filter != "all":
        filtered = [track for track in filtered if track.artist.casefold() == artist_filter]

    if needle:
        filtered = [
            track
            for track in filtered
            if needle in track.artist.casefold()
            or needle in track.title.casefold()
            or needle in track.relative_path.casefold()
        ]

    return sort_tracks(filtered, sort_by=sort_by)


def list_artists(tracks: list[AudioTrack]) -> list[str]:
    """Return unique artists sorted case-insensitively."""
    return sorted({track.artist for track in tracks}, key=str.casefold)


def build_audio_index(library_dir: Path) -> list[AudioTrack]:
    """Build a read-only track index from a local audio library."""
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = library_dir.resolve()
    tracks: list[AudioTrack] = []

    for audio_file in get_audio_files_in_folder(root):
        relative_path = audio_file.resolve().relative_to(root).as_posix()
        artist, title = audiofile_assume_artist_title(audio_file)
        tracks.append(
            AudioTrack(
                relative_path=relative_path,
                artist=artist,
                title=title,
                stream_url=f"/audio/stream?path={encode_relative_path(relative_path)}",
            )
        )

    return sort_tracks(tracks, sort_by="artist")


