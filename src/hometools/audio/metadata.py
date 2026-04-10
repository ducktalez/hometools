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


def write_track_tags(p: Path, *, title: str | None = None, artist: str | None = None, album: str | None = None) -> bool:
    """Write title/artist/album tags to an audio file.

    Supports MP3 (ID3), M4A/MP4 (iTunes atoms), FLAC, OGG/Vorbis, WMA.
    Skips fields that are ``None`` (not provided).
    Never raises — returns False on failure.
    """
    if title is None and artist is None and album is None:
        return True  # nothing to do

    ext = p.suffix.lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3, TALB, TIT2, TPE1, ID3NoHeaderError

            try:
                tags = ID3(p)
            except ID3NoHeaderError:
                tags = ID3()
            if title is not None:
                tags["TIT2"] = TIT2(encoding=3, text=title)
            if artist is not None:
                tags["TPE1"] = TPE1(encoding=3, text=artist)
            if album is not None:
                tags["TALB"] = TALB(encoding=3, text=album)
            tags.save(p)

        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(p)
            if audio.tags is None:
                audio.add_tags()
            if title is not None:
                audio.tags["\xa9nam"] = [title]
            if artist is not None:
                audio.tags["\xa9ART"] = [artist]
            if album is not None:
                audio.tags["\xa9alb"] = [album]
            audio.save()

        else:
            # FLAC, OGG, Opus, WMA — generic Vorbis / ASF tags via mutagen.File
            audio = File(p)
            if audio is None:
                logger.error("write_track_tags: could not open %s", p.name)
                return False
            if audio.tags is None:
                audio.add_tags()
            if title is not None:
                audio.tags["title"] = [title]
            if artist is not None:
                audio.tags["artist"] = [artist]
            if album is not None:
                audio.tags["album"] = [album]
            audio.save()

        logger.info("write_track_tags: updated %s (title=%r, artist=%r, album=%r)", p.name, title, artist, album)
        return True

    except Exception as exc:
        logger.error("write_track_tags: failed for %s: %s", p.name, exc)
        return False


# ---------------------------------------------------------------------------
# POPM (rating) helpers
# ---------------------------------------------------------------------------

# Windows Media Player / foobar2000 / MusicBee / Mp3tag standard mapping.
# Using this instead of a linear scale ensures interoperability with all
# major tagging tools and Windows Explorer.
_POPM_TO_STARS: list[tuple[int, float]] = [
    # (upper_bound_exclusive, stars)
    (1, 0.0),  # 0         = unrated
    (32, 1.0),  # 1  – 31   = 1★
    (96, 2.0),  # 32 – 95   = 2★
    (160, 3.0),  # 96 – 159  = 3★
    (224, 4.0),  # 160 – 223 = 4★
]
# 224–255 = 5★ (handled as fallback)

_STARS_TO_POPM: dict[int, int] = {0: 0, 1: 1, 2: 64, 3: 128, 4: 196, 5: 255}


def popm_raw_to_stars(raw: int) -> float:
    """Convert a raw POPM value (0–255) to a 0–5 star rating.

    Uses the Windows Media Player standard step mapping so ratings are
    compatible with foobar2000, MusicBee, Mp3tag, and Windows Explorer.
    """
    for upper, stars in _POPM_TO_STARS:
        if raw < upper:
            return stars
    return 5.0


def stars_to_popm_raw(stars: float) -> int:
    """Convert a 0–5 star rating to a raw POPM value (0–255).

    Uses the Windows Media Player standard canonical values:
    0→0, 1→1, 2→64, 3→128, 4→196, 5→255.
    """
    rounded = max(0, min(5, round(stars)))
    return _STARS_TO_POPM.get(rounded, 0)


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
# M4A / FLAC / OGG rating atoms
# ---------------------------------------------------------------------------

_M4A_RATING_ATOM = "----:com.apple.iTunes:RATING"

# Canonical write values for the 0-100 percentage scale used by
# Mp3tag, MediaMonkey, foobar2000 and other MP4-aware taggers.
_STARS_TO_M4A: dict[int, int] = {0: 0, 1: 20, 2: 40, 3: 60, 4: 80, 5: 100}


def _m4a_rating_to_stars(raw_value: int) -> float:
    """Convert an M4A freeform rating value to 0–5 stars.

    Values ≤ 5 are treated as a direct star count (some tools store 1–5).
    Values > 5 are treated as a 0–100 percentage scale (20 per star).
    """
    if raw_value <= 0:
        return 0.0
    if raw_value <= 5:
        return float(raw_value)
    return min(5.0, round(raw_value / 20))


def _read_m4a_rating(p: Path) -> float:
    """Read star rating from an M4A/MP4 file (0.0–5.0).

    Handles both UTF-8 text values (e.g. ``b"80"``) written by Mp3tag /
    MediaMonkey / our own writer and raw binary values (e.g. ``\\x50``)
    that some other tools produce.
    """
    try:
        audio = MP4(p)
        if audio.tags is None:
            return 0.0
        # Try freeform rating atom (----:com.apple.iTunes:RATING)
        val = audio.tags.get(_M4A_RATING_ATOM)
        if val:
            raw_bytes = bytes(val[0])
            # 1) Try UTF-8 text parsing first (most common: b"80", b"60" …)
            try:
                raw = int(raw_bytes.decode("utf-8", errors="ignore").strip())
            except (ValueError, UnicodeDecodeError):
                # 2) Fallback: interpret as a binary integer
                if len(raw_bytes) == 1:
                    raw = raw_bytes[0]  # single byte → ordinal value
                elif raw_bytes:
                    raw = int.from_bytes(raw_bytes, byteorder="big")
                else:
                    raw = 0
            return _m4a_rating_to_stars(raw)
    except Exception as exc:
        logger.debug("_read_m4a_rating %s: %s", p.name, exc)
    return 0.0


def _write_m4a_rating(p: Path, stars: float) -> bool:
    """Write star rating to an M4A/MP4 file as a freeform iTunes atom."""
    from mutagen.mp4 import MP4FreeForm

    rounded = max(0, min(5, round(stars)))
    value = _STARS_TO_M4A.get(rounded, 0)
    try:
        audio = MP4(p)
        if audio.tags is None:
            audio.add_tags()
        audio.tags[_M4A_RATING_ATOM] = [
            MP4FreeForm(str(value).encode("utf-8"), dataformat=1)  # 1 = UTF-8
        ]
        audio.save()
        logger.info("%s: M4A rating set to %d (stars=%s)", p.name, value, stars)
        return True
    except Exception as exc:
        logger.error("Error writing M4A rating to %s: %s", p.name, exc)
        return False


def _read_vorbis_rating(p: Path) -> float:
    """Read star rating from a FLAC/OGG file via Vorbis comments (0.0–5.0)."""
    try:
        audio = File(p)
        if audio is None or not audio.tags:
            return 0.0
        tags = audio.tags

        # 1. FMPS_RATING — 0.0–1.0 float (Free Music Player Specifications)
        for key in ("FMPS_RATING", "fmps_rating"):
            val = tags.get(key)
            if val:
                fval = float(val[0] if isinstance(val, list) else val)
                return min(5.0, round(fval * 5))

        # 2. RATING — direct integer 1–5 (foobar2000, others)
        for key in ("RATING", "rating"):
            val = tags.get(key)
            if val:
                ival = float(val[0] if isinstance(val, list) else val)
                if ival <= 5:
                    return float(max(0, round(ival)))
                # 0–100 percentage scale
                return min(5.0, round(ival / 20))
    except Exception as exc:
        logger.debug("_read_vorbis_rating %s: %s", p.name, exc)
    return 0.0


def _write_vorbis_rating(p: Path, stars: float) -> bool:
    """Write star rating to a FLAC/OGG file as Vorbis comments."""
    rounded = max(0, min(5, round(stars)))
    fmps_value = str(rounded / 5)  # 0.0–1.0
    try:
        audio = File(p)
        if audio is None:
            logger.error("_write_vorbis_rating: could not open %s", p.name)
            return False
        if audio.tags is None:
            audio.add_tags()
        audio.tags["FMPS_RATING"] = [fmps_value]
        audio.tags["RATING"] = [str(rounded)]
        audio.save()
        logger.info("%s: Vorbis rating set to %s (FMPS=%s)", p.name, rounded, fmps_value)
        return True
    except Exception as exc:
        logger.error("Error writing Vorbis rating to %s: %s", p.name, exc)
        return False


# ---------------------------------------------------------------------------
# Format-aware rating access (unified)
# ---------------------------------------------------------------------------


def get_rating_stars(p: Path) -> float:
    """Read star rating (0.0–5.0) from any supported audio format.

    Supported formats:
    - **MP3**: ID3 POPM frame (WMP standard step mapping via ``popm_raw_to_stars``)
    - **M4A/MP4**: ``----:com.apple.iTunes:RATING`` freeform atom (0–100 scale)
    - **FLAC/OGG**: ``FMPS_RATING`` (0.0–1.0) or ``RATING`` (1–5) Vorbis comment

    Returns ``0.0`` (unrated) for unsupported formats or on any error.
    """
    ext = p.suffix.lower()
    if ext == ".mp3":
        return popm_raw_to_stars(get_popm_rating(p))
    if ext in (".m4a", ".mp4", ".aac"):
        return _read_m4a_rating(p)
    if ext in (".flac", ".ogg", ".opus"):
        return _read_vorbis_rating(p)
    return 0.0


def set_rating_stars(p: Path, stars: float) -> bool:
    """Write star rating (0.0–5.0) to any supported audio format.

    Supported formats:
    - **MP3**: ID3 POPM frame (WMP canonical values via ``stars_to_popm_raw``)
    - **M4A/MP4**: ``----:com.apple.iTunes:RATING`` freeform atom (0–100 scale)
    - **FLAC/OGG**: ``FMPS_RATING`` + ``RATING`` Vorbis comments

    Returns ``False`` for unsupported formats or on any error.
    """
    ext = p.suffix.lower()
    if ext == ".mp3":
        return set_popm_rating(p, stars_to_popm_raw(stars))
    if ext in (".m4a", ".mp4", ".aac"):
        return _write_m4a_rating(p, stars)
    if ext in (".flac", ".ogg", ".opus"):
        return _write_vorbis_rating(p, stars)
    logger.warning("set_rating_stars: unsupported format %s for %s", ext, p.name)
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


def get_genre(p: Path) -> str:
    """Read the genre tag from an audio file.

    Supports MP3 (ID3 TCON), M4A/MP4 (©gen), FLAC/OGG (genre/GENRE).
    Returns an empty string when no genre is found.
    Never raises — returns ``""`` on any error.
    """
    try:
        audio = File(p)
        if audio is None or not audio.tags:
            return ""
        return _find_tag(
            audio.tags,
            "\xa9gen",  # MP4/M4A (©gen)
            "genre",
            "GENRE",  # Vorbis (FLAC/OGG)
            "TCON",  # ID3 (MP3)
        )
    except Exception as exc:
        logger.debug("get_genre %s: %s", p.name, exc)
    return ""


def get_lyrics(p: Path) -> str | None:
    """Read embedded lyrics from an audio file.

    Supports:
    - MP3: ID3 USLT (Unsynchronized Lyrics) frames
    - M4A/MP4: ``©lyr`` atom
    - FLAC/OGG: ``LYRICS`` or ``UNSYNCEDLYRICS`` Vorbis comment

    Returns the lyrics text or ``None`` if not found.
    Never raises — returns ``None`` on any error.
    """
    ext = p.suffix.lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3

            tags = ID3(p)
            uslt_frames = tags.getall("USLT")
            if uslt_frames:
                return str(uslt_frames[0].text).strip() or None
            return None
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(p)
            if audio.tags and "\xa9lyr" in audio.tags:
                text = audio.tags["\xa9lyr"]
                return str(text[0]).strip() if text else None
            return None
        else:
            # FLAC, OGG, Opus — Vorbis comments
            audio = File(p)
            if audio is None or not audio.tags:
                return None
            for key in ("lyrics", "LYRICS", "unsyncedlyrics", "UNSYNCEDLYRICS"):
                val = audio.tags.get(key)
                if val:
                    text = val[0] if isinstance(val, list) else str(val)
                    return str(text).strip() or None
    except Exception as exc:
        logger.debug("get_lyrics %s: %s", p.name, exc)
    return None


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
