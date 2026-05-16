"""Shadow-cache waveform peak extraction for audio files.

256 normalised peak values (0.0–1.0) per channel are extracted via ffmpeg at
1 kHz stereo and cached as JSON in
<cache_dir>/audio/<relative_path>.waveform.json.

Stereo format:
  {"peaks_l": [...256 floats], "peaks_r": [...256 floats], "segments": 256}

Legacy mono caches (only "peaks" key) are still served as-is; the JS renderer
falls back to mono display when "peaks_r" is absent.

Key rules (shadow_cache.instructions.md):
- **Never modify original media files.**
- **MTime-based invalidation**: regenerate when source is newer than cache.
- **Exception safety**: every public function never raises.
- **Background-only extraction**: the heavy work runs in a daemon thread via
  ``start_background_waveform_generation()``.  The server exposes
  ``/api/audio/waveform`` for on-demand generation when the cache is cold.
"""

from __future__ import annotations

import json
import logging
import struct
import subprocess
import threading
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

WAVEFORM_SUFFIX = ".waveform.json"
WAVEFORM_SEGMENTS = 256

_wf_bg_lock = threading.Lock()
_wf_bg_running = False


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def get_waveform_path(cache_dir: Path, media_type: str, relative_path: str) -> Path:
    """Return the expected waveform JSON path inside the shadow cache.

    >>> get_waveform_path(Path("/cache"), "audio", "Artist/Song.mp3")
    PosixPath('/cache/audio/Artist/Song.mp3.waveform.json')
    """
    return cache_dir / media_type / (relative_path + WAVEFORM_SUFFIX)


def _source_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_waveform_peaks(
    media_path: Path,
    segments: int = WAVEFORM_SEGMENTS,
) -> tuple[list[float], list[float]] | None:
    """Decode audio via ffmpeg at 1 kHz stereo, compute peak per segment per channel.

    Returns a ``(peaks_l, peaks_r)`` tuple of normalised float lists in
    [0.0, 1.0], both of length *segments*.  Both channels are normalised
    jointly so their relative loudness is preserved.

    Mono source files are up-mixed to stereo by ffmpeg (both channels will be
    identical).

    Returns ``None`` on failure (ffmpeg missing, timeout, corrupt file, …).
    Never raises.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(media_path),
                "-f",
                "f32le",
                "-ac",
                "2",  # stereo — ffmpeg up-mixes mono automatically
                "-ar",
                "1000",
                "-vn",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        raw = result.stdout
        if not raw:
            logger.debug("ffmpeg produced no PCM output for waveform: %s", media_path.name)
            return None

        # Stereo interleaved: [L0, R0, L1, R1, …]
        n_total = len(raw) // 4  # total float32 values
        n_frames = n_total // 2  # frames (L+R pairs)

        if n_frames < segments:
            logger.debug(
                "Too few frames (%d) for waveform in %s — need at least %d",
                n_frames,
                media_path.name,
                segments,
            )
            return None

        all_samples = struct.unpack(f"<{n_total}f", raw)
        samples_l = all_samples[0::2]
        samples_r = all_samples[1::2]

        block_size = n_frames // segments

        peaks_l: list[float] = []
        peaks_r: list[float] = []
        for i in range(segments):
            start = i * block_size
            end = start + block_size
            block_l = samples_l[start:end]
            block_r = samples_r[start:end]
            peaks_l.append(max(abs(s) for s in block_l) if block_l else 0.0)
            peaks_r.append(max(abs(s) for s in block_r) if block_r else 0.0)

        # Joint normalisation: both channels share the same scale
        max_peak = max(max(peaks_l, default=0.0), max(peaks_r, default=0.0))
        if max_peak > 0:
            peaks_l = [p / max_peak for p in peaks_l]
            peaks_r = [p / max_peak for p in peaks_r]

        return peaks_l, peaks_r

    except FileNotFoundError:
        logger.debug("ffmpeg not found — skipping waveform extraction for %s", media_path.name)
        return None
    except subprocess.TimeoutExpired:
        logger.debug("ffmpeg waveform timed out for %s", media_path.name)
        return None
    except Exception:
        logger.debug("Waveform extraction failed for %s", media_path.name, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def check_waveform_cached(
    cache_dir: Path,
    media_type: str,
    relative_path: str,
) -> Path | None:
    """Return the waveform path only if it already exists on disk.  Never raises."""
    try:
        p = get_waveform_path(cache_dir, media_type, relative_path)
        return p if p.exists() else None
    except Exception:
        return None


def ensure_waveform(
    media_path: Path,
    cache_dir: Path,
    media_type: str,
    relative_path: str,
) -> Path | None:
    """Generate and cache stereo waveform JSON when needed.

    Skips generation when a fresh cached copy already exists (MTime check).
    Returns the waveform path on success, ``None`` on failure.  Never raises.

    Cache format:
      {"peaks_l": [...256], "peaks_r": [...256], "segments": 256}
    """
    try:
        waveform_path = get_waveform_path(cache_dir, media_type, relative_path)

        # MTime invalidation: skip if cached copy is at least as new as source
        if waveform_path.exists() and _source_mtime(media_path) <= waveform_path.stat().st_mtime:
            return waveform_path

        result = extract_waveform_peaks(media_path)
        if result is None:
            return None
        peaks_l, peaks_r = result

        waveform_path.parent.mkdir(parents=True, exist_ok=True)
        waveform_path.write_text(
            json.dumps({"peaks_l": peaks_l, "peaks_r": peaks_r, "segments": len(peaks_l)}),
            encoding="utf-8",
        )
        logger.debug("Waveform cached for %s (%d segments, stereo)", relative_path, len(peaks_l))
        return waveform_path

    except Exception:
        logger.debug("ensure_waveform failed for %s", relative_path, exc_info=True)
        return None


def load_waveform(waveform_path: Path) -> dict | None:
    """Read waveform JSON from disk.  Returns ``None`` on any failure."""
    try:
        return json.loads(waveform_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Background generation
# ---------------------------------------------------------------------------


def _generate_waveforms_worker(
    items: list[tuple[Path, Path, str, str]],
) -> None:
    """Worker: generates missing/stale waveform caches sequentially in a daemon thread."""
    global _wf_bg_running
    generated = 0
    skipped = 0
    errors = 0

    try:
        for media_path, cache_dir, media_type, relative_path in items:
            try:
                wf_path = get_waveform_path(cache_dir, media_type, relative_path)
                if wf_path.exists() and _source_mtime(media_path) <= wf_path.stat().st_mtime:
                    skipped += 1
                    continue

                result = ensure_waveform(media_path, cache_dir, media_type, relative_path)
                if result:
                    generated += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
                logger.debug("Background waveform failed for %s", relative_path, exc_info=True)
    finally:
        with _wf_bg_lock:
            _wf_bg_running = False
        logger.info(
            "Background waveform generation finished: %d generated, %d skipped, %d errors",
            generated,
            skipped,
            errors,
        )


def start_background_waveform_generation(
    items: Iterable[tuple[Path, Path, str, str]],
) -> bool:
    """Spawn a daemon thread that pre-generates missing waveform caches.

    *items* is an iterable of ``(media_path, cache_dir, media_type, relative_path)``
    tuples — same format as used by thumbnail work lists.

    Returns ``True`` if a new thread was started, ``False`` if one is already
    running (only one background generation at a time).  Never raises.
    """
    global _wf_bg_running

    try:
        work = list(items)
        if not work:
            return False

        with _wf_bg_lock:
            if _wf_bg_running:
                logger.debug("Background waveform generation already in progress — skipping")
                return False
            _wf_bg_running = True

        logger.info("Starting background waveform generation for %d items", len(work))
        thread = threading.Thread(
            target=_generate_waveforms_worker,
            args=(work,),
            daemon=True,
            name="waveform-bg",
        )
        thread.start()
        return True

    except Exception:
        with _wf_bg_lock:
            _wf_bg_running = False
        logger.debug("Failed to start background waveform generation", exc_info=True)
        return False
