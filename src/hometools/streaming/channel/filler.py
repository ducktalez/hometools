"""Filler content management — fill gaps between scheduled programs.

Scans a configurable filler directory for short video clips and music
files that can be used to bridge gaps between scheduled series episodes.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from hometools.constants import AUDIO_SUFFIX, VIDEO_SUFFIX

logger = logging.getLogger(__name__)


def scan_filler_dir(filler_dir: Path) -> list[Path]:
    """Return all usable filler files from the filler directory.

    Includes both video and audio files.  Returns an empty list if the
    directory does not exist or contains no media files.
    """
    if not filler_dir.is_dir():
        logger.debug("Filler directory does not exist: %s", filler_dir)
        return []

    all_suffixes = set(VIDEO_SUFFIX + AUDIO_SUFFIX)
    files = sorted(p for p in filler_dir.rglob("*") if p.is_file() and p.suffix.lower() in all_suffixes)
    logger.info("Found %d filler files in %s", len(files), filler_dir)
    return files


def select_filler(
    filler_files: list[Path],
    gap_seconds: float,
    *,
    max_clips: int = 20,
) -> list[Path]:
    """Select filler clips to fill a gap of *gap_seconds*.

    Returns a shuffled selection of filler files.  Does not attempt
    exact duration matching — the mixer will cut the last clip short
    when the next program starts.

    If no filler files are available, returns an empty list (the mixer
    will generate a test card as fallback).
    """
    if not filler_files or gap_seconds <= 0:
        return []

    # Shuffle and return enough clips to cover the gap
    # The mixer handles duration enforcement via -t flag
    pool = list(filler_files)
    random.shuffle(pool)

    # Return at most max_clips files
    return pool[:max_clips]


def generate_testcard_filler_args(
    duration: float,
    *,
    channel_name: str = "Haus-TV",
) -> list[str]:
    """Return ffmpeg args that generate a TV test card (Testbild) for *duration* seconds.

    Produces SMPTE colour bars with a "Sendepause" / channel-name text
    overlay and a silent audio track — much more recognisable than a plain
    black screen and immediately tells the viewer that the channel is alive
    but has no scheduled content.
    """
    # Build drawtext filter chain.  The font is optional — ffmpeg falls
    # back to a built-in sans font when fontfile is not found.
    # Escape colons in the text for the drawtext filter.
    safe_name = channel_name.replace(":", r"\:")
    drawtext_top = f"drawtext=text='{safe_name}':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.28"
    drawtext_mid = "drawtext=text='Sendepause':fontsize=64:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2"
    drawtext_time = "drawtext=text='%{localtime}':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.65"
    vf = f"{drawtext_top},{drawtext_mid},{drawtext_time}"

    return [
        "-re",
        "-f",
        "lavfi",
        "-i",
        f"smptebars=s=1280x720:d={duration:.1f}:r=25",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=44100:cl=stereo:d={duration:.1f}",
        "-vf",
        vf,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-t",
        f"{duration:.1f}",
    ]


def generate_black_filler_args(duration: float) -> list[str]:
    """Return ffmpeg args that generate a black screen + silence for *duration* seconds.

    .. deprecated:: Use :func:`generate_testcard_filler_args` instead.
        Kept for backward compatibility.
    """
    return [
        "-re",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s=1280x720:d={duration:.1f}:r=25",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=44100:cl=stereo:d={duration:.1f}",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-t",
        f"{duration:.1f}",
    ]
