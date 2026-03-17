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
from hometools.utils import run_text_subprocess

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
    """Return the raw POPM rating (0–255) of an audio file.

    Only MP3 files carry ID3 POPM frames.  M4A/FLAC/other formats
    return 0 silently because they have no equivalent tag.
    """
    if p.suffix.lower() != ".mp3":
        return 0
    try:
        audio = MP3(p, ID3=ID3)
        popm_tags = audio.tags.getall("POPM")
        if not popm_tags:
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


# ---------------------------------------------------------------------------
# Generic embedded metadata reading
# ---------------------------------------------------------------------------


def _first_text(value) -> str:
    """Extract the first text string from a mutagen tag value.

    Handles ID3 text frames (``.text`` attribute), MP4/Vorbis lists,
    and plain strings.
    """
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    if hasattr(value, "text"):  # ID3 TextFrame (TIT2, TPE1, …)
        return str(value.text[0]).strip() if value.text else ""
    return str(value).strip()


def _find_tag(tags, *keys: str) -> str:
    """Return the first matching tag value from *tags* for the given *keys*."""
    for key in keys:
        if key in tags:
            return _first_text(tags[key])
    return ""


def _read_metadata_ffprobe(p: Path) -> dict[str, str] | None:
    """Try to read title/artist via ``ffprobe`` (useful for video containers)."""
    import json
    import subprocess

    try:
        result = run_text_subprocess(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(p)],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        fmt_tags = data.get("format", {}).get("tags", {})
        # ffprobe tag keys can vary in case — normalise to lower
        tags_lower = {k.lower(): v for k, v in fmt_tags.items()}
        title = tags_lower.get("title", "")
        artist = tags_lower.get("artist", "") or tags_lower.get("album_artist", "")

        if title or artist:
            return {"title": title, "artist": artist}
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass

    return None


def read_embedded_metadata(p: Path) -> dict[str, str] | None:
    """Read *title* and *artist* from embedded file metadata.

    Supports every format that **mutagen** can open (MP3, M4A/MP4, FLAC,
    OGG, Opus, WMA, …).  For container formats mutagen cannot handle
    (e.g. MKV, AVI) a ``ffprobe`` fallback is attempted.

    Returns ``{'title': …, 'artist': …}`` or ``None`` when nothing useful
    was found.
    """
    # 1) Try mutagen — works for audio and MP4-based containers
    try:
        audio = File(p)
        if audio is not None and audio.tags:
            title = _find_tag(
                audio.tags,
                "\xa9nam",  # MP4/M4A (©nam)
                "title",
                "TITLE",  # Vorbis (FLAC/OGG)
                "TIT2",  # ID3 (MP3)
                "Title",  # ASF (WMA)
            )
            artist = _find_tag(
                audio.tags,
                "\xa9ART",  # MP4/M4A (©ART)
                "artist",
                "ARTIST",  # Vorbis (FLAC/OGG)
                "TPE1",  # ID3 (MP3)
                "Author",  # ASF (WMA)
            )
            if title or artist:
                return {"title": title, "artist": artist}
    except Exception:
        pass

    # 2) Fallback: ffprobe (for video formats mutagen cannot read)
    return _read_metadata_ffprobe(p)


def audiofile_assume_artist_title(p: Path, lut: dict | None = None) -> tuple[str, str]:
    """Determine artist and title, preferring embedded metadata over filename parsing.

    Priority (highest wins):
      1. LUT (lookup-table) overrides — when provided and the file is listed.
      2. Embedded file metadata (ID3, MP4 tags, Vorbis comments, …).
      3. Filename parsing via :func:`split_stem`.
    """
    # Fallback: derive from filename
    parts = split_stem(p.stem)
    artist = parts[0] if parts else "Unknown"
    title = parts[1] if len(parts) > 1 else "MISSING"

    # Try embedded metadata
    meta = read_embedded_metadata(p)
    if meta:
        if meta.get("artist", "").strip():
            artist = meta["artist"].strip()
        if meta.get("title", "").strip():
            title = meta["title"].strip()

    # LUT overrides (highest priority)
    if lut and p.as_posix() in lut:
        tag = lut[p.as_posix()].get("TAG", {})
        artist = re.sub(r"\| - Topic", "", tag.get("artist", artist))
        title = tag.get("title", title)

    return artist, title
