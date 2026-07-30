"""BPM (beats per minute) calculation for audio files.

Analysis requires the optional ``audio-analysis`` extra (``librosa`` +
``numpy``). Import errors are handled gracefully — see
``.github/instructions/tools.instructions.md`` ("I/O-heavy tools ... must
stay behind CLI commands" / never crash the caller) and copilot-instructions
Rule 5. This module never raises: :func:`calculate_bpm` returns ``None`` on
any failure (missing dependency, unreadable file, analysis error).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_bpm(p: Path) -> float | None:
    """Estimate the tempo (beats per minute) of an audio file via librosa.

    Requires the optional ``audio-analysis`` extra (``pip install
    hometools[audio-analysis]``). Returns ``None`` (never raises) when:

    - ``librosa`` is not installed,
    - the file can't be decoded, or
    - beat tracking fails for any other reason.

    This function only *estimates* — it does not write anything to the
    file. See :func:`hometools.audio.metadata.set_bpm` for persisting the
    result, or :func:`analyze_and_save_bpm` to do both in one call.
    """
    try:
        import librosa
        import librosa.beat
    except ImportError:
        logger.warning(
            "calculate_bpm: librosa is not installed — install the 'audio-analysis' extra "
            "(pip install hometools[audio-analysis]) to enable BPM calculation."
        )
        return None

    try:
        y, sr = librosa.load(p, sr=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # librosa returns a numpy scalar/array depending on version; normalize to float.
        bpm = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)
        if bpm <= 0:
            return None
        return bpm
    except Exception:
        logger.warning("calculate_bpm: analysis failed for %s", p, exc_info=True)
        return None


def analyze_and_save_bpm(p: Path) -> float | None:
    """Calculate the BPM of *p* and persist it via :func:`hometools.audio.metadata.set_bpm`.

    Returns the rounded BPM value on success, ``None`` if calculation or
    writing failed (never raises). This is the single entry point used by
    both the CLI and the streaming server's "BPM berechnen" tool.
    """
    from hometools.audio.metadata import set_bpm

    bpm = calculate_bpm(p)
    if bpm is None:
        return None
    if not set_bpm(p, bpm):
        logger.warning("analyze_and_save_bpm: could not save bpm=%.1f for %s", bpm, p)
        return None
    logger.info("analyze_and_save_bpm: saved bpm=%d for %s", round(bpm), p.name)
    return round(bpm)
