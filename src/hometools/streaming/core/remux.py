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
import shutil
import struct
import subprocess
import threading
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


FASTSTART_SUFFIX = ".faststart.mp4"


def get_faststart_cache_path(cache_dir: Path, relative_path: str) -> Path:
    """Return the shadow-cache path for a faststart-converted MP4.

    >>> get_faststart_cache_path(Path("/cache"), "Series/ep01.mp4")
    PosixPath('/cache/video/Series/ep01.mp4.faststart.mp4')
    """
    return cache_dir / "video" / (relative_path + FASTSTART_SUFFIX)


def ensure_faststart_cache(
    file_path: Path,
    cache_dir: Path,
    relative_path: str,
) -> Path | None:
    """Ensure a faststart-converted copy of *file_path* exists in the shadow cache.

    Uses ``ffmpeg -c copy -movflags +faststart`` — purely a moov-atom
    rearrangement, no re-encoding.  Typically completes in a few seconds
    even for large files.

    MTime-based invalidation: regenerates if the source is newer than the cache.

    Returns the cached :class:`~pathlib.Path` on success, ``None`` on failure
    (ffmpeg missing, disk error, …).  Never raises.
    """
    out_path = get_faststart_cache_path(cache_dir, relative_path)

    try:
        # Check mtime-based invalidation
        if out_path.exists():
            src_mtime = file_path.stat().st_mtime
            cache_mtime = out_path.stat().st_mtime
            if cache_mtime >= src_mtime:
                logger.debug("ensure_faststart_cache — cache hit: %s", out_path.name)
                return out_path
            logger.info(
                "ensure_faststart_cache — source newer than cache, regenerating: %s",
                file_path.name,
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = out_path.with_suffix(".tmp.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(file_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-v",
            "warning",
            str(tmp_path),
        ]
        logger.info(
            "ensure_faststart_cache — creating faststart copy: %s → %s",
            file_path.name,
            out_path.name,
        )
        proc = subprocess.run(cmd, capture_output=True, timeout=300)
        if proc.returncode != 0:
            stderr_msg = proc.stderr.decode("utf-8", errors="replace")[:300]
            logger.warning(
                "ensure_faststart_cache — ffmpeg failed (rc=%d) for %s: %s",
                proc.returncode,
                file_path.name,
                stderr_msg,
            )
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            return None

        tmp_path.rename(out_path)
        logger.info("ensure_faststart_cache — done: %s", out_path.name)
        return out_path

    except FileNotFoundError:
        logger.warning("ensure_faststart_cache — ffmpeg not found, cannot create cache for %s", file_path.name)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ensure_faststart_cache — ffmpeg timed out for %s", file_path.name)
        return None
    except Exception:
        logger.warning("ensure_faststart_cache — unexpected error for %s", file_path.name, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Cached remux / transcode for non-native containers (AVI, MKV, FLV, …)
# ---------------------------------------------------------------------------

REMUX_SUFFIX = ".remux.mp4"


def get_remux_cache_path(cache_dir: Path, relative_path: str) -> Path:
    """Return the shadow-cache path for a remuxed/transcoded MP4 copy.

    >>> get_remux_cache_path(Path("/cache"), "Series/ep01.avi")
    PosixPath('/cache/video/Series/ep01.avi.remux.mp4')
    """
    return cache_dir / "video" / (relative_path + REMUX_SUFFIX)


def ensure_remux_cache(
    file_path: Path,
    cache_dir: Path,
    relative_path: str,
    *,
    copy: bool | None = None,
) -> Path | None:
    """Ensure a browser-playable MP4 copy of a non-native file exists in the cache.

    Unlike :func:`remux_stream` (a live ffmpeg pipe that cannot serve HTTP
    Range requests — so iOS Safari and most mobile browsers refuse to play
    it), this produces a **complete MP4 file with fast-start** that can be
    served via ``FileResponse`` with full Range/206 support.  That is what
    makes ``.avi`` / ``.mkv`` series play on phones.

    *copy* mirrors :func:`remux_stream`:
    ``True`` → ``-c copy`` (instant, codecs already browser-compatible),
    ``False`` → transcode to H.264/AAC (CPU-heavy),
    ``None`` → auto-detect via :func:`can_copy_codecs`.

    MTime-based invalidation: regenerates when the source is newer than the
    cache.  Returns the cached :class:`~pathlib.Path` on success, ``None`` on
    failure.  Never raises.
    """
    out_path = get_remux_cache_path(cache_dir, relative_path)

    try:
        if out_path.exists():
            src_mtime = file_path.stat().st_mtime
            if out_path.stat().st_mtime >= src_mtime:
                logger.debug("ensure_remux_cache — cache hit: %s", out_path.name)
                return out_path
            logger.info("ensure_remux_cache — source newer than cache, regenerating: %s", file_path.name)

        if copy is None:
            copy = can_copy_codecs(file_path)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_suffix(".tmp.mp4")

        if copy:
            codec_args = ["-c", "copy"]
            timeout = 600
            logger.info("ensure_remux_cache — remux (copy) %s → %s", file_path.name, out_path.name)
        else:
            codec_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k"]
            # Full transcode of a long episode can take a while on slow CPUs.
            timeout = 7200
            logger.info("ensure_remux_cache — transcode %s → H.264/AAC %s", file_path.name, out_path.name)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(file_path),
            *codec_args,
            "-movflags",
            "+faststart",
            "-v",
            "warning",
            str(tmp_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if proc.returncode != 0:
            stderr_msg = proc.stderr.decode("utf-8", errors="replace")[:300]
            logger.warning(
                "ensure_remux_cache — ffmpeg failed (rc=%d) for %s: %s",
                proc.returncode,
                file_path.name,
                stderr_msg,
            )
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            return None

        tmp_path.rename(out_path)
        logger.info("ensure_remux_cache — done: %s", out_path.name)
        return out_path

    except FileNotFoundError:
        logger.warning("ensure_remux_cache — ffmpeg not found, cannot create cache for %s", file_path.name)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ensure_remux_cache — ffmpeg timed out for %s", file_path.name)
        return None
    except Exception:
        logger.warning("ensure_remux_cache — unexpected error for %s", file_path.name, exc_info=True)
        return None


# Tracks in-flight background remux jobs so we never spawn two ffmpeg
# processes for the same file concurrently.
_remux_jobs_lock = threading.Lock()
_remux_jobs_active: set[str] = set()


def start_background_remux(
    file_path: Path,
    cache_dir: Path,
    relative_path: str,
    *,
    copy: bool | None = None,
) -> bool:
    """Build the remux cache for a single file in a daemon thread.

    De-duplicates concurrent requests for the same *relative_path*.  Returns
    ``True`` if a job was started (or is already running), ``False`` if ffmpeg
    is unavailable.  Best-effort, never raises.
    """
    if not shutil.which("ffmpeg"):
        return False

    with _remux_jobs_lock:
        if relative_path in _remux_jobs_active:
            return True
        _remux_jobs_active.add(relative_path)

    def _run() -> None:
        try:
            ensure_remux_cache(file_path, cache_dir, relative_path, copy=copy)
        finally:
            with _remux_jobs_lock:
                _remux_jobs_active.discard(relative_path)

    threading.Thread(target=_run, daemon=True, name="remux-cache").start()
    return True


def start_background_remux_generation(work: list[tuple[Path, Path, str]]) -> bool:
    """Pre-build remux caches for many non-native files in one daemon thread.

    *work* is a list of ``(file_path, cache_dir, relative_path)`` tuples.
    Files that already have a fresh cache are skipped.  Processes files
    sequentially (one ffmpeg at a time) to avoid saturating the CPU.

    Returns ``True`` if a worker was started, ``False`` otherwise.
    """
    if not work or not shutil.which("ffmpeg"):
        return False

    def _run() -> None:
        built = 0
        for file_path, cache_dir, relative_path in work:
            try:
                out = get_remux_cache_path(cache_dir, relative_path)
                if out.exists() and out.stat().st_mtime >= file_path.stat().st_mtime:
                    continue
                if ensure_remux_cache(file_path, cache_dir, relative_path) is not None:
                    built += 1
            except Exception:
                logger.debug("Background remux failed for %s", relative_path, exc_info=True)
        if built:
            logger.info("Background remux generation: %d non-native files cached", built)

    threading.Thread(target=_run, daemon=True, name="remux-bootstrap").start()
    return True


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
