"""On-the-fly remuxing / transcoding for browser-incompatible video formats.

The HTML5 ``<video>`` element only supports certain container/codec
combinations natively (MP4+H.264, WebM+VP8/VP9, OGG+Theora).  Files in
other formats (FLV, AVI, MKV with XviD, …) can still be streamed by
piping them through ffmpeg on the fly.

Strategy (same as Jellyfin):

1. **Remux** (``-c copy``): If the codecs are already browser-compatible
   (e.g. H.264 video in an FLV container), just change the container to
   fragmented MP4.  This is nearly instant.
2. **Transcode** (``-c:v libx264``): If the video codec is unsupported
   (e.g. XviD / MPEG-4 Part 2), re-encode to H.264 on the fly.  This
   uses CPU but starts streaming immediately.

Both modes output a *fragmented MP4* (``-movflags frag_keyframe+empty_moov``)
so the browser can start playback before the entire file is processed.

An additional check detects MP4 files whose ``moov`` atom is at the end
of the file (not *fast-start*).  These files require the browser to
download the entire file before playback can begin.  When detected, they
are served through the remux pipeline (``-c copy``) which outputs
fragmented MP4 that streams instantly.

Requirements:
- ``ffmpeg`` and ``ffprobe`` must be on ``$PATH``.  If missing, the
  functions return graceful fallbacks and the caller can serve the raw
  file instead (browser will likely fail to play it, but won't crash).
"""

from __future__ import annotations

import logging
import struct
import subprocess
from collections.abc import Generator
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions that the browser <video> element can play natively
BROWSER_NATIVE_EXTENSIONS: set[str] = {".mp4", ".m4v", ".webm", ".ogg", ".ogv"}

# Extensions that should be checked for fast-start (moov before mdat)
_FASTSTART_CHECK_EXTENSIONS: set[str] = {".mp4", ".m4v", ".mov"}

# Video codecs the browser can decode (lowercased ffprobe codec_name values)
_REMUXABLE_VIDEO_CODECS: set[str] = {
    "h264",
    "hevc",
    "h265",
    "vp8",
    "vp9",
    "av1",
    "theora",
}

# Audio codecs the browser can decode
_REMUXABLE_AUDIO_CODECS: set[str] = {
    "aac",
    "mp3",
    "vorbis",
    "opus",
    "flac",
    "pcm_s16le",
    "pcm_f32le",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def has_faststart(file_path: Path) -> bool:
    """Return True if the MP4/M4V file has the ``moov`` atom before ``mdat``.

    A *fast-start* file can begin playback immediately because the browser
    receives the metadata first.  Files with ``moov`` at the end require a
    full download before playback can begin.

    Returns True (optimistic) on any I/O error or for non-MP4 files.
    """
    if file_path.suffix.lower() not in _FASTSTART_CHECK_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            # Walk top-level atoms.  Each atom: 4-byte size (big-endian) + 4-byte type.
            # We only need to find whether 'moov' comes before 'mdat'.
            pos = 0
            while True:
                header = f.read(8)
                if len(header) < 8:
                    break
                size = struct.unpack(">I", header[:4])[0]
                atom_type = header[4:8]

                if atom_type == b"moov":
                    return True  # moov before mdat → fast-start
                if atom_type == b"mdat":
                    return False  # mdat before moov → NOT fast-start

                # Handle size == 0 (atom extends to EOF) and size == 1 (64-bit size)
                if size == 0:
                    break
                if size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = struct.unpack(">Q", ext)[0]
                    if size < 16:
                        break
                    f.seek(pos + size)
                else:
                    if size < 8:
                        break
                    f.seek(pos + size)
                pos = f.tell()
        # Neither moov nor mdat found → assume fast-start
        return True
    except (OSError, struct.error) as exc:
        logger.debug("has_faststart check failed for %s: %s", file_path.name, exc)
        return True  # optimistic fallback — serve via FileResponse


def needs_remux(file_path: Path) -> bool:
    """Return True if the file's container is not natively supported by browsers."""
    return file_path.suffix.lower() not in BROWSER_NATIVE_EXTENSIONS


def probe_codecs(file_path: Path) -> dict[str, str]:
    """Return ``{"video": "<codec>", "audio": "<codec>"}`` via ffprobe.

    Returns empty strings on failure.  Never raises.
    """
    result = {"video": "", "audio": ""}
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result["video"] = proc.stdout.strip().lower()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.debug("ffprobe (video) unavailable for %s", file_path)
        return result

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result["audio"] = proc.stdout.strip().lower()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return result


def can_copy_codecs(file_path: Path) -> bool:
    """Return True if the file's codecs are browser-compatible (remux only).

    When True, ffmpeg can use ``-c copy`` (instant).
    When False, transcoding is required (slower but still streams).
    """
    codecs = probe_codecs(file_path)
    if not codecs["video"]:
        return False
    video_ok = codecs["video"] in _REMUXABLE_VIDEO_CODECS
    audio_ok = codecs["audio"] in _REMUXABLE_AUDIO_CODECS or not codecs["audio"]
    return video_ok and audio_ok


def remux_stream(
    file_path: Path,
    *,
    copy: bool | None = None,
) -> Generator[bytes, None, None]:
    """Yield fragmented-MP4 chunks from ffmpeg.

    Parameters
    ----------
    file_path:
        The source video file.
    copy:
        ``True`` → remux only (``-c copy``), instant.
        ``False`` → transcode to H.264/AAC.
        ``None`` (default) → auto-detect via :func:`can_copy_codecs`.

    Yields
    ------
    bytes
        Chunks of the output MP4 stream (typically 64 KiB).

    If ffmpeg is not installed, yields nothing (caller should fall back
    to serving the raw file).
    """
    if copy is None:
        copy = can_copy_codecs(file_path)

    if copy:
        codec_args = ["-c", "copy"]
        logger.info("Remuxing (copy) %s → fragmented MP4", file_path.name)
    else:
        codec_args = [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ]
        logger.info("Transcoding %s → H.264/AAC fragmented MP4", file_path.name)

    cmd = [
        "ffmpeg",
        "-i",
        str(file_path),
        *codec_args,
        "-movflags",
        "frag_keyframe+empty_moov",
        "-f",
        "mp4",
        "-v",
        "warning",
        "pipe:1",
    ]

    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            yield chunk

        proc.wait(timeout=5)
        if proc.returncode != 0 and proc.stderr:
            stderr_tail = proc.stderr.read(500)
            logger.warning(
                "ffmpeg exited with code %d for %s: %s",
                proc.returncode,
                file_path.name,
                stderr_tail.decode("utf-8", errors="replace")[:300],
            )
    except FileNotFoundError:
        logger.warning("ffmpeg not found — cannot remux %s", file_path.name)
    except GeneratorExit:
        # Client disconnected — kill ffmpeg immediately
        if proc is not None:
            proc.kill()
            proc.wait(timeout=3)
        logger.debug("Client disconnected during remux of %s", file_path.name)
    except Exception:
        logger.warning("Remux failed for %s", file_path.name, exc_info=True)
        if proc is not None:
            proc.kill()
            proc.wait(timeout=3)
    finally:
        if proc is not None:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            if proc.poll() is None:
                proc.kill()
