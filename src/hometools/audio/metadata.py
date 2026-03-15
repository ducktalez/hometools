"""Audio metadata reading and writing helpers."""

import logging
import re
from pathlib import Path

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3, POPM
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from hometools.audio.sanitize import split_stem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tag I/O
# ---------------------------------------------------------------------------


def get_audio_metadata(file_path: Path) -> dict | None:
    """Read basic metadata (title, artist, album, genre) via EasyID3."""
    try:
        audio = EasyID3(file_path)
        return {
            "title": audio.get("title", ["Unknown"])[0],
            "artist": audio.get("artist", ["Unknown"])[0],
            "album": audio.get("album", ["Unknown"])[0],
            "genre": audio.get("genre", ["Unknown"])[0],
        }
    except Exception as e:
        logger.error(f"Error reading metadata from {file_path}: {e}")
        return None


def read_all_tags(p: Path) -> dict:
    """Read every tag from an audio file as a plain dict."""
    audio = File(p)
    if audio is None or not hasattr(audio, "tags") or audio.tags is None:
        return {}
    return dict(audio.tags)


def write_all_tags(p: Path, tags: dict) -> bool:
    """Write a dict of tags back to an audio file."""
    audio = File(p)
    if audio is None:
        logger.error(f"Could not open {p.name}")
        return False
    if audio.tags is None:
        audio.add_tags()
    for key, value in tags.items():
        audio.tags[key] = value
    audio.save()
    logger.info(f"Tags restored for {p.name}")
    return True


# ---------------------------------------------------------------------------
# POPM (rating) helpers
# ---------------------------------------------------------------------------


def get_popm_rating(p: Path) -> int:
    """Return the raw POPM rating (0–255) of an MP3 file."""
    try:
        audio = MP3(p, ID3=ID3)
        popm_tags = audio.tags.getall("POPM")
        if not popm_tags:
            logger.warning(f"No POPM rating found for {p.name}")
            return 0
        return popm_tags[0].rating
    except Exception as e:
        logger.error(f"Error reading POPM from {p.name}: {e}")
        return 0


def set_popm_rating(p: Path, rating: int, email: str = "default", playcount: int = 0) -> bool:
    """Set the POPM rating (0–255) of an MP3 file."""
    if not 0 <= rating <= 255:
        raise ValueError("Rating must be between 0 and 255.")
    try:
        audio = MP3(p, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        popm = POPM(email=email, rating=rating, count=playcount)
        audio.tags.setall("POPM", [popm])
        audio.save()
        logger.info(f"{p.name}: rating set to {rating}")
        return True
    except Exception as e:
        logger.error(f"Error writing POPM to {p.name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Format-aware tag access
# ---------------------------------------------------------------------------


def _open_audio(p: Path):
    """Open an audio file with the correct mutagen class for its format."""
    ext = p.suffix.lower()
    if ext == ".mp3":
        return MP3(p, ID3=EasyID3)
    elif ext == ".flac":
        return FLAC(p)
    elif ext in (".m4a", ".mp4"):
        return MP4(p)
    else:
        raise ValueError(f"Unsupported audio format: {ext}")


def audiofile_assume_artist_title(p: Path, lut: dict | None = None) -> tuple[str, str]:
    """Guess artist and title from file name, falling back to metadata if available."""
    parts = split_stem(p.stem)

    artist = parts[0] if parts else "Unknown"
    title = parts[1] if len(parts) > 1 else "MISSING"

    if lut and p.as_posix() in lut:
        tag = lut[p.as_posix()].get("TAG", {})
        artist = re.sub(r'\| - Topic', '', tag.get("artist", artist))
        title = tag.get("title", title)

    return artist, title
