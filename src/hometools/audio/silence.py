"""Audio silence detection and removal using pydub + ffmpeg."""

import logging
import subprocess
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------


def get_audio_length(p: Path) -> float:
    """Return audio length in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-i",
        str(p),
        "-show_entries",
        "format=duration",
        "-v",
        "quiet",
        "-of",
        "csv=p=0",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logger.error(f"Could not determine length of {p.name}")
        return 0.0


def plot_waveform(p: Path, trimmed_p: Path):
    """Show waveform comparison between original and trimmed audio (requires matplotlib)."""
    import matplotlib.pyplot as plt

    original = AudioSegment.from_file(p)
    trimmed = AudioSegment.from_file(trimmed_p)

    original_samples = np.array(original.get_array_of_samples())
    trimmed_samples = np.array(trimmed.get_array_of_samples())

    zoom = 5000

    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(original_samples[:zoom], color="blue", label="Original")
    plt.plot(trimmed_samples[:zoom], color="red", label="Trimmed", alpha=0.7)
    plt.title("Waveform (start)")
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(original_samples[-zoom:], color="blue", label="Original")
    plt.plot(trimmed_samples[-zoom:], color="red", label="Trimmed", alpha=0.7)
    plt.title("Waveform (end)")
    plt.legend()

    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# BPM analysis
# ---------------------------------------------------------------------------


def analyze_bpm(p: Path):
    """Analyse BPM and store in metadata (requires librosa)."""
    import librosa
    import librosa.beat

    from hometools.audio.metadata import _open_audio

    y, sr = librosa.load(p, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = round(tempo[0])

    try:
        audio = _open_audio(p)
        audio["bpm"] = str(bpm)
        audio.save()
        logger.info(f"BPM ({bpm}) saved for {p.name}")
    except Exception:
        logger.warning(f"Unsupported format for BPM storage: {p}")


# ---------------------------------------------------------------------------
# Trimming
# ---------------------------------------------------------------------------


def trim_audio_fixed_duration(
    p: Path,
    start_trim_ms: int = 0,
    end_trim_ms: int = 0,
    overwrite: bool = False,
):
    """Trim fixed milliseconds from start/end using ffmpeg (lossless copy)."""
    start_sec = start_trim_ms / 1000
    length_sec = get_audio_length(p)
    end_sec = max(0.0, length_sec - (end_trim_ms / 1000))

    if start_sec >= end_sec:
        logger.warning(f"Trim values too large for {p.name} – skipping.")
        return

    new_path = p if overwrite else p.with_stem(p.stem + "-ffmpeg")
    cmd = [
        "ffmpeg",
        "-i",
        str(p),
        "-c:a",
        "copy",
        "-ss",
        str(start_sec),
        "-to",
        str(end_sec),
        str(new_path),
        "-y" if overwrite else "-n",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "Output file is empty" in result.stderr:
        logger.warning(f"No changes for {p.name}.")
        return
    logger.info(f"Trimmed (fixed) → {new_path}")


def split_mp3_lossless(p: Path, start_sec: float, end_sec: float, overwrite: bool = False):
    """Losslessly split an MP3 using mp3splt (frame-boundary cutting)."""
    if p.suffix.lower() != ".mp3":
        logger.error(f"Only MP3 files supported, not {p.suffix}")
        return

    output = p if overwrite else p.with_stem(p.stem + "-split")

    def _fmt(sec):
        minutes = int(sec // 60)
        seconds = sec % 60
        return f"{minutes}.{seconds:06.3f}"

    cmd = [
        "mp3splt",
        "-f",
        "-o",
        output.stem,
        "-d",
        str(output.parent),
        str(p),
        _fmt(start_sec),
        _fmt(end_sec),
    ]
    logger.info(f"Splitting {p.name}: {_fmt(start_sec)} – {_fmt(end_sec)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"mp3splt error: {result.stderr}")
    else:
        logger.info(f"Success: {output.with_suffix('.mp3')}")


def remove_silence_with_ffmpeg(
    p: Path,
    overwrite: bool = False,
    save_difference: bool = False,
    silence_thresh: int = -75,
):
    """Detect silence with pydub, cut with ffmpeg (no re-encoding)."""
    if "-ffmpeg" in p.stem or "-removed" in p.stem:
        logger.info(f"Skipping already-processed file: {p.name}")
        return

    audio = AudioSegment.from_file(p)
    nonsilent = detect_nonsilent(audio, silence_thresh=silence_thresh, seek_step=10)

    if not nonsilent:
        logger.info(f"No non-silent parts in {p.name} – skipping.")
        return

    start_trim = max(0, nonsilent[0][0] - 200)
    end_trim = min(len(audio), nonsilent[-1][1] + 1500)

    if start_trim == 0 and end_trim == len(audio):
        logger.info(f"No silence to remove in {p.name}.")
        return

    if overwrite:
        p_source = p.rename(p.with_stem(p.stem + "-ffmpeg-original"))
        p_new = p
    else:
        p_source = p
        p_new = p.with_stem(p.stem + "-ffmpeg")

    cmd = [
        "ffmpeg",
        "-i",
        str(p_source),
        "-c:a",
        "copy",
        "-map_metadata",
        "0",
        "-ss",
        str(start_trim / 1000),
        "-to",
        str(end_trim / 1000 + 0.5),
        str(p_new),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "Output file is empty" in result.stderr:
        logger.info(f"No changes for {p.name}.")
        return
    logger.info(f"Silence removed → {p_new}")

    if save_difference:
        removed_audio = audio[:start_trim] + audio[end_trim:]
        removed_path = p.with_stem(p.stem + "-ffmpeg-removed")
        fmt = "mp4" if p.suffix.lower() == ".m4a" else p.suffix[1:]
        params = ["-c:a", "aac"] if fmt == "mp4" else []
        removed_audio.export(removed_path, format=fmt, parameters=params)
        logger.info(f"Removed silence saved → {removed_path}")


def process_audio_folder(
    folder: Path,
    overwrite: bool = False,
    save_difference: bool = False,
    silence_thresh: int = -75,
):
    """Process all audio files in *folder*, removing leading/trailing silence."""
    supported = {".mp3", ".flac", ".m4a", ".wav"}
    for f in folder.glob("*.*"):
        if f.suffix.lower() in supported and "-ffmpeg" not in f.stem and "-removed" not in f.stem:
            remove_silence_with_ffmpeg(
                f,
                overwrite=overwrite,
                save_difference=save_difference,
                silence_thresh=silence_thresh,
            )
