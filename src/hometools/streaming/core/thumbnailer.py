"""Shadow-cache thumbnail generation for audio covers and video frames.

INSTRUCTIONS (local):
- Thumbnails are stored in a *shadow cache directory* that mirrors the
  library folder structure.  Original media files are **never** modified.
- ``check_thumbnail_cached()`` is the **fast path** used during catalog
  building — it only checks whether a thumbnail already exists on disk.
  This keeps server startup instantaneous regardless of library size.
- ``start_background_thumbnail_generation()`` spawns a daemon thread that
  lazily generates missing thumbnails after the server is up.  Callers
  never block on thumbnail extraction.
- ``ensure_thumbnail()`` still exists for one-off / CLI use but should
  **not** be called in hot catalog-build loops.
- Audio covers are extracted via *mutagen* and resized with *Pillow* (both
  optional — missing libraries just mean no thumbnail, never a crash).
- Video thumbnails are extracted via *ffmpeg* (subprocess).
- All thumbnails are JPEG, max 120 px on the longest side.
- **Exception safety**: every public function in this module is designed to
  *never* raise.  Failures are logged and result in ``None`` / ``False``.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

THUMB_SUFFIX = ".thumb.jpg"
THUMB_MAX_PX = 120


# ---------------------------------------------------------------------------
# Pure path helpers
# ---------------------------------------------------------------------------


def get_thumbnail_path(cache_dir: Path, media_type: str, relative_path: str) -> Path:
    """Return the expected thumbnail path inside the shadow cache.

    >>> get_thumbnail_path(Path("/cache"), "audio", "Artist/Song.mp3")
    PosixPath('/cache/audio/Artist/Song.mp3.thumb.jpg')
    """
    return cache_dir / media_type / (relative_path + THUMB_SUFFIX)


# ---------------------------------------------------------------------------
# Audio cover extraction (mutagen + Pillow)
# ---------------------------------------------------------------------------


def _extract_cover_bytes(media_path: Path) -> bytes | None:
    """Extract raw embedded cover art bytes from an audio file via mutagen."""
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        logger.debug("mutagen not installed — skipping audio cover extraction")
        return None

    try:
        audio = MutagenFile(media_path)
        if audio is None:
            return None

        # ID3 (MP3) — APIC frames
        if hasattr(audio, "tags") and audio.tags:
            for key in audio.tags:
                if key.startswith("APIC"):
                    return audio.tags[key].data

        # FLAC — pictures list
        if hasattr(audio, "pictures") and audio.pictures:
            return audio.pictures[0].data

        # MP4/M4A — covr atom
        if hasattr(audio, "tags") and audio.tags and "covr" in audio.tags:
            covers = audio.tags["covr"]
            if covers:
                return bytes(covers[0])

    except Exception:
        logger.debug("Could not extract cover from %s", media_path, exc_info=True)
    return None


def _resize_and_save_jpeg(raw_bytes: bytes, dest: Path) -> bool:
    """Resize cover art to max THUMB_MAX_PX and save as JPEG."""
    try:
        import io

        from PIL import Image
    except ImportError:
        # Pillow not available — save raw bytes as-is (may be larger)
        logger.debug("Pillow not installed — saving raw cover bytes")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw_bytes)
        return True

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX), Image.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=80)
        return True
    except Exception:
        logger.debug("Failed to resize cover for %s", dest, exc_info=True)
        return False


def extract_audio_cover(media_path: Path, thumb_path: Path) -> bool:
    """Extract embedded album cover from an audio file and save as thumbnail.

    Returns True if a thumbnail was created, False otherwise.
    """
    raw = _extract_cover_bytes(media_path)
    if raw is None:
        return False
    return _resize_and_save_jpeg(raw, thumb_path)


# ---------------------------------------------------------------------------
# Video thumbnail extraction (ffmpeg)
# ---------------------------------------------------------------------------


def extract_video_thumbnail(media_path: Path, thumb_path: Path, seek_sec: int = 5) -> bool:
    """Extract a video frame via ffmpeg and save as a JPEG thumbnail.

    Returns True if the thumbnail was created, False otherwise.
    """
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(seek_sec),
                "-i",
                str(media_path),
                "-frames:v",
                "1",
                "-vf",
                f"scale={THUMB_MAX_PX}:-1",
                str(thumb_path),
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and thumb_path.exists():
            return True
        logger.debug("ffmpeg failed for %s: %s", media_path, result.stderr[:200])
    except FileNotFoundError:
        logger.debug("ffmpeg not found — skipping video thumbnail")
    except subprocess.TimeoutExpired:
        logger.debug("ffmpeg timed out for %s", media_path)
    except Exception:
        logger.debug("Unexpected error extracting video thumb for %s", media_path, exc_info=True)
    return False


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def ensure_thumbnail(
    media_path: Path,
    cache_dir: Path,
    media_type: str,
    relative_path: str,
) -> Path | None:
    """Return the thumbnail path if available, generating it lazily if needed.

    Returns ``None`` when no thumbnail could be generated (missing cover,
    ffmpeg not installed, etc.).  Never raises.

    .. note::
        For hot-path catalog building use :func:`check_thumbnail_cached`
        instead — it avoids blocking on extraction.
    """
    try:
        thumb_path = get_thumbnail_path(cache_dir, media_type, relative_path)

        # Already cached — skip extraction
        if thumb_path.exists():
            return thumb_path

        if media_type == "audio":
            ok = extract_audio_cover(media_path, thumb_path)
        elif media_type == "video":
            ok = extract_video_thumbnail(media_path, thumb_path)
        else:
            ok = False

        return thumb_path if ok else None
    except Exception:
        logger.debug("ensure_thumbnail failed for %s", relative_path, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Non-blocking helpers (for server startup)
# ---------------------------------------------------------------------------


def check_thumbnail_cached(
    cache_dir: Path,
    media_type: str,
    relative_path: str,
) -> Path | None:
    """Return the thumbnail path *only* if it already exists on disk.

    This is the fast path used during catalog building — no extraction is
    attempted, so it never blocks.  Returns ``None`` if the thumbnail has
    not been generated yet.
    """
    try:
        thumb_path = get_thumbnail_path(cache_dir, media_type, relative_path)
        return thumb_path if thumb_path.exists() else None
    except Exception:
        logger.debug("check_thumbnail_cached failed for %s", relative_path, exc_info=True)
        return None


# Global lock to ensure only one background generation runs at a time
_bg_lock = threading.Lock()
_bg_running = False


def _generate_thumbnails_worker(
    items: list[tuple[Path, Path, str, str]],
) -> None:
    """Worker that generates thumbnails sequentially in a daemon thread.

    *items* is a list of ``(media_path, cache_dir, media_type, relative_path)``
    tuples.
    """
    global _bg_running
    generated = 0
    skipped = 0
    errors = 0

    try:
        for media_path, cache_dir, media_type, relative_path in items:
            try:
                thumb_path = get_thumbnail_path(cache_dir, media_type, relative_path)
                if thumb_path.exists():
                    skipped += 1
                    continue

                if media_type == "audio":
                    ok = extract_audio_cover(media_path, thumb_path)
                elif media_type == "video":
                    ok = extract_video_thumbnail(media_path, thumb_path)
                else:
                    ok = False

                if ok:
                    generated += 1
                else:
                    skipped += 1
            except Exception:
                errors += 1
                logger.debug(
                    "Background thumb generation failed for %s",
                    relative_path,
                    exc_info=True,
                )
    finally:
        with _bg_lock:
            _bg_running = False
        logger.info(
            "Background thumbnail generation finished: %d generated, %d skipped, %d errors",
            generated,
            skipped,
            errors,
        )


def start_background_thumbnail_generation(
    items: Iterable[tuple[Path, Path, str, str]],
) -> bool:
    """Spawn a daemon thread that generates missing thumbnails in the background.

    *items* is an iterable of ``(media_path, cache_dir, media_type, relative_path)``
    tuples — typically produced by scanning the library directory.

    Returns ``True`` if a new thread was started, ``False`` if one is already
    running (only one background generation at a time).

    Never raises.
    """
    global _bg_running

    try:
        work = list(items)
        if not work:
            return False

        with _bg_lock:
            if _bg_running:
                logger.debug("Background thumbnail generation already in progress")
                return False
            _bg_running = True

        logger.info("Starting background thumbnail generation for %d items", len(work))
        thread = threading.Thread(
            target=_generate_thumbnails_worker,
            args=(work,),
            daemon=True,
            name="thumbnailer-bg",
        )
        thread.start()
        return True
    except Exception:
        logger.debug("Failed to start background thumbnail generation", exc_info=True)
        with _bg_lock:
            _bg_running = False
        return False
