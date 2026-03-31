"""Pre-transcoding for the channel mixer — prepare videos before streaming.

The concat-demuxer based HLS pipeline requires all input files to have
**identical** codec parameters (resolution, frame rate, codec, sample rate).
This module converts arbitrary video files into a uniform intermediate
format and writes them to a temporary directory.

**Design rule — no live transcoding into the stream.**  Videos are always
pre-converted to a temporary MP4 file *before* the concat-based ffmpeg
process reads them.  This avoids race conditions where the stream stalls
because ffmpeg is still transcoding a slow source (NAS, network share).

Temporary files are deleted after playback via :func:`cleanup_prepared`.

Target format
-------------
- **Video:** H.264 (configurable encoder), 1280×720, 25 fps
- **Audio:** AAC, 128 kbps, stereo, 44100 Hz
- **Container:** MP4 (non-fragmented — concat demuxer reads files, not streams)
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Target parameters — must match across ALL files fed to the concat demuxer.
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TARGET_FPS = 25
TARGET_AUDIO_RATE = 44100
TARGET_AUDIO_BITRATE = "128k"
TARGET_AUDIO_CHANNELS = 2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def prepare_video(
    source: Path,
    tmp_dir: Path,
    *,
    encoder: str = "libx264",
    seek: float = 0,
    duration: float | None = None,
) -> Path | None:
    """Convert *source* to a uniform MP4 in *tmp_dir*.

    Parameters
    ----------
    source:
        Original video file (any format ffmpeg understands).
    tmp_dir:
        Directory for the output file.
    encoder:
        H.264 encoder (``libx264``, ``h264_nvenc``, ``h264_qsv``).
    seek:
        Start offset in seconds (for late-join trimming).
    duration:
        Maximum duration in seconds (for pünktliches Ende).

    Returns
    -------
    Path to the prepared MP4, or ``None`` on failure.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Deterministic output name based on source path + seek + duration
    key = f"{source}|{seek:.1f}|{duration or 'full'}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    out_path = tmp_dir / f"prep_{digest}.mp4"

    # Skip if already prepared (e.g. re-run after crash)
    if out_path.exists() and out_path.stat().st_size > 0:
        logger.debug("Already prepared: %s → %s", source.name, out_path.name)
        return out_path

    input_args: list[str] = []
    if seek > 1:
        input_args.extend(["-ss", f"{seek:.1f}"])
    input_args.extend(["-i", str(source)])
    if duration is not None and duration > 0:
        input_args.extend(["-t", f"{duration:.1f}"])

    vf = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}"
        ":force_original_aspect_ratio=decrease,"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1"
    )

    cmd = [
        "ffmpeg",
        "-y",
        *input_args,
        "-c:v",
        encoder,
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        TARGET_AUDIO_BITRATE,
        "-ac",
        str(TARGET_AUDIO_CHANNELS),
        "-ar",
        str(TARGET_AUDIO_RATE),
        "-vf",
        vf,
        "-r",
        str(TARGET_FPS),
        "-movflags",
        "+faststart",
        "-v",
        "warning",
        str(out_path),
    ]

    logger.info("Pre-transcoding: %s → %s", source.name, out_path.name)
    logger.debug("ffmpeg command: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=600,  # 10 min max per video
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            logger.error(
                "Pre-transcode failed for %s (exit %d): %s",
                source.name,
                proc.returncode,
                (proc.stderr or "")[:300],
            )
            _safe_unlink(out_path)
            return None
    except FileNotFoundError:
        logger.error("ffmpeg not found — channel mixer requires ffmpeg on PATH")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Pre-transcode timed out for %s", source.name)
        _safe_unlink(out_path)
        return None
    except Exception:
        logger.error("Pre-transcode error for %s", source.name, exc_info=True)
        _safe_unlink(out_path)
        return None

    if not out_path.exists() or out_path.stat().st_size == 0:
        logger.error("Pre-transcode produced empty file for %s", source.name)
        _safe_unlink(out_path)
        return None

    logger.info("Pre-transcode complete: %s (%.1f MB)", out_path.name, out_path.stat().st_size / 1e6)
    return out_path


def prepare_testcard(
    duration: float,
    tmp_dir: Path,
    *,
    channel_name: str = "Haus-TV",
    encoder: str = "libx264",
) -> Path | None:
    """Pre-render a TV test card (Sendepause) as a temporary MP4 file.

    Tries to render with text overlays (channel name, clock) first.
    If that fails — e.g. because Fontconfig is not configured on Windows
    (``Fontconfig error: Cannot load default config file``) — falls back to
    plain SMPTE colour bars without any drawtext filter.

    Returns
    -------
    Path to the rendered MP4, or ``None`` if both attempts fail.
    """
    # Stage 1: with drawtext overlay
    result = _render_testcard_with_text(duration, tmp_dir, channel_name=channel_name, encoder=encoder)
    if result is not None:
        return result

    # Stage 2: plain SMPTE bars — no Fontconfig / drawtext required.
    # This always works on Windows even without a fontconfig installation.
    logger.warning("Testcard with text failed (Fontconfig missing?) — falling back to plain SMPTE colour bars")
    return _render_testcard_plain(duration, tmp_dir, encoder=encoder)


def _render_testcard_with_text(
    duration: float,
    tmp_dir: Path,
    *,
    channel_name: str = "Haus-TV",
    encoder: str = "libx264",
) -> Path | None:
    """Render SMPTE bars with drawtext overlays.  Returns None if drawtext fails."""
    tmp_dir.mkdir(parents=True, exist_ok=True)

    key = f"testcard|{duration:.0f}|{channel_name}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    out_path = tmp_dir / f"testcard_{digest}.mp4"

    if out_path.exists() and out_path.stat().st_size > 0:
        logger.debug("Testcard (text) already rendered: %s", out_path.name)
        return out_path

    safe_name = channel_name.replace(":", r"\:")
    drawtext_top = f"drawtext=text='{safe_name}':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.28"
    drawtext_mid = "drawtext=text='Sendepause':fontsize=64:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2"
    drawtext_time = "drawtext=text='%{localtime}':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.65"
    vf = f"{drawtext_top},{drawtext_mid},{drawtext_time}"

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"smptebars=s={TARGET_WIDTH}x{TARGET_HEIGHT}:d={duration:.1f}:r={TARGET_FPS}",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={TARGET_AUDIO_RATE}:cl=stereo:d={duration:.1f}",
        "-vf",
        vf,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        encoder,
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        TARGET_AUDIO_BITRATE,
        "-ac",
        str(TARGET_AUDIO_CHANNELS),
        "-ar",
        str(TARGET_AUDIO_RATE),
        "-t",
        f"{duration:.1f}",
        "-movflags",
        "+faststart",
        "-v",
        "warning",
        str(out_path),
    ]

    logger.info("Rendering test card (with text): %.0fs → %s", duration, out_path.name)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=max(duration * 2, 60),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            # Non-fatal — caller will try plain fallback
            logger.warning(
                "Testcard with text failed (exit %d): %s",
                proc.returncode,
                (proc.stderr or "")[:200],
            )
            _safe_unlink(out_path)
            return None
    except FileNotFoundError:
        logger.error("ffmpeg not found — cannot render test card")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Testcard (text) render timed out (%.0fs)", duration)
        _safe_unlink(out_path)
        return None
    except Exception:
        logger.error("Testcard (text) render error", exc_info=True)
        _safe_unlink(out_path)
        return None

    if not out_path.exists() or out_path.stat().st_size == 0:
        _safe_unlink(out_path)
        return None

    logger.info("Testcard (text) ready: %s (%.1f MB)", out_path.name, out_path.stat().st_size / 1e6)
    return out_path


def _render_testcard_plain(
    duration: float,
    tmp_dir: Path,
    *,
    encoder: str = "libx264",
) -> Path | None:
    """Render plain SMPTE colour bars without any drawtext filter.

    This fallback does not require Fontconfig and works on Windows even
    without a fontconfig installation.  No text overlay — just colour bars
    with a silent audio track.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)

    key = f"testcard_plain|{duration:.0f}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    out_path = tmp_dir / f"testcard_plain_{digest}.mp4"

    if out_path.exists() and out_path.stat().st_size > 0:
        logger.debug("Testcard (plain) already rendered: %s", out_path.name)
        return out_path

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"smptebars=s={TARGET_WIDTH}x{TARGET_HEIGHT}:d={duration:.1f}:r={TARGET_FPS}",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={TARGET_AUDIO_RATE}:cl=stereo:d={duration:.1f}",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        encoder,
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        TARGET_AUDIO_BITRATE,
        "-ac",
        str(TARGET_AUDIO_CHANNELS),
        "-ar",
        str(TARGET_AUDIO_RATE),
        "-t",
        f"{duration:.1f}",
        "-movflags",
        "+faststart",
        "-v",
        "warning",
        str(out_path),
    ]

    logger.info("Rendering plain test card (no drawtext): %.0fs → %s", duration, out_path.name)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=max(duration * 2, 60),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            logger.error(
                "Plain testcard render failed (exit %d): %s",
                proc.returncode,
                (proc.stderr or "")[:300],
            )
            _safe_unlink(out_path)
            return None
    except FileNotFoundError:
        logger.error("ffmpeg not found — cannot render plain test card")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Plain testcard render timed out (%.0fs)", duration)
        _safe_unlink(out_path)
        return None
    except Exception:
        logger.error("Plain testcard render error", exc_info=True)
        _safe_unlink(out_path)
        return None

    if not out_path.exists() or out_path.stat().st_size == 0:
        logger.error("Plain testcard render produced empty file")
        _safe_unlink(out_path)
        return None

    logger.info("Plain testcard ready: %s (%.1f MB)", out_path.name, out_path.stat().st_size / 1e6)
    return out_path


def build_concat_file(videos: list[Path], output: Path) -> Path:
    """Write a concat-demuxer list file.

    Format::

        ffconcat version 1.0
        file '/absolute/path/to/video1.mp4'
        file '/absolute/path/to/video2.mp4'

    Parameters
    ----------
    videos:
        Ordered list of pre-transcoded MP4 files.
    output:
        Path where the concat list file will be written.

    Returns the *output* path.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["ffconcat version 1.0"]
    for v in videos:
        # Use forward slashes and escape single quotes for ffmpeg
        safe_path = str(v.resolve()).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.debug("Concat file written: %s (%d entries)", output.name, len(videos))
    return output


def cleanup_prepared(*paths: Path) -> int:
    """Delete temporary pre-transcoded files.

    Returns the number of files successfully deleted.
    """
    removed = 0
    for p in paths:
        if _safe_unlink(p):
            removed += 1
    return removed


def cleanup_tmp_dir(tmp_dir: Path) -> int:
    """Remove all files in the temp directory.  Returns count of deleted files."""
    if not tmp_dir.is_dir():
        return 0
    removed = 0
    for p in tmp_dir.iterdir():
        if p.is_file() and _safe_unlink(p):
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_unlink(path: Path) -> bool:
    """Delete a file, returning True on success.  Never raises."""
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        logger.debug("Failed to delete %s", path, exc_info=True)
    return False
