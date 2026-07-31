"""BPM octave-correction hint storage.

Beat-tracking algorithms (librosa's ``beat_track``) sometimes lock onto
half or double the true tempo (an "octave error") — e.g. a 170 BPM track
gets reported as 85 BPM. When a user corrects this via the "Langsamer"/
"Schneller" BPM-adjust actions in the streaming UI (see
``streaming/audio/server.py``'s ``/api/audio/bpm/adjust`` endpoint and
``player_js/_track_render.py``'s ``_openBpmAdjustMenu``), the correction
*factor* is persisted per-track here so that a **later** "neu berechnen"
(recalculate, ``/api/audio/bpm/calculate``) applies the same octave
correction to the fresh raw estimate instead of reproducing the same
mistake.

Storage layout mirrors ``intro_markers.py``::

    <cache_dir>/bpm_hints/<server>.json
    {"hints": {"Artist/Track.mp3": 2.0, ...}}

Thread-safe (module-level lock), atomic writes, every public function is
exception-safe (returns sensible defaults, never raises).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_HINT_DIR = "bpm_hints"
_MAX_HINTS = 50000
# A single slower/faster click halves/doubles the multiplier, so a handful
# of clicks in one direction already spans multiple octaves. Clamping keeps
# a runaway multiplier (e.g. from repeated accidental clicks) from biasing
# future recalculations towards an absurd value.
_MIN_MULTIPLIER = 0.0625  # 1/16x
_MAX_MULTIPLIER = 16.0

_lock = threading.Lock()


def _hints_path(cache_dir: Path, server: str) -> Path:
    """Return the on-disk path for the hint store of *server*."""
    return cache_dir / _HINT_DIR / f"{server}.json"


def _read_raw(path: Path) -> dict[str, Any]:
    """Read the hint store from disk (caller must hold ``_lock``)."""
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        hints = data.get("hints")
        return hints if isinstance(hints, dict) else {}
    except Exception:
        logger.debug("Failed to read bpm hints from %s", path, exc_info=True)
        return {}


def _write_raw(path: Path, hints: dict[str, Any]) -> None:
    """Atomically write the hint store to disk (caller must hold ``_lock``)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            suffix=".json",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump({"hints": hints}, tmp, ensure_ascii=False, indent=2)
            tmp_path_obj = Path(tmp.name)
        tmp_path_obj.replace(path)
    except Exception:
        logger.debug("Failed to write bpm hints to %s", path, exc_info=True)


def get_octave_multiplier(cache_dir: Path, server: str, relative_path: str) -> float:
    """Return the persisted octave-correction multiplier for *relative_path*.

    ``1.0`` (no correction) if none is stored or on any failure.
    """
    rp = (relative_path or "").strip()
    if not rp:
        return 1.0
    with _lock:
        hints = _read_raw(_hints_path(cache_dir, server))
        try:
            return float(hints.get(rp, 1.0))
        except (TypeError, ValueError):
            return 1.0


def adjust_octave_multiplier(cache_dir: Path, server: str, relative_path: str, factor: float) -> float:
    """Multiply the stored octave-correction hint for *relative_path* by *factor*.

    Called from the "Langsamer" (``factor=0.5``) / "Schneller"
    (``factor=2.0``) BPM-adjust actions. Returns the new, clamped
    multiplier (see module docstring), or ``1.0`` on failure / empty key /
    non-positive factor — never raises.
    """
    rp = (relative_path or "").strip()
    if not rp or factor <= 0:
        return 1.0
    with _lock:
        path = _hints_path(cache_dir, server)
        hints = _read_raw(path)
        try:
            current = float(hints.get(rp, 1.0))
        except (TypeError, ValueError):
            current = 1.0
        new_val = max(_MIN_MULTIPLIER, min(_MAX_MULTIPLIER, current * factor))
        if len(hints) >= _MAX_HINTS and rp not in hints:
            return new_val
        hints[rp] = new_val
        _write_raw(path, hints)
        return new_val


def reset_octave_multiplier(cache_dir: Path, server: str, relative_path: str) -> bool:
    """Remove any stored octave-correction hint for *relative_path*.

    Returns ``True`` if a hint was removed, ``False`` otherwise (including
    on any failure — never raises).
    """
    rp = (relative_path or "").strip()
    if not rp:
        return False
    with _lock:
        path = _hints_path(cache_dir, server)
        hints = _read_raw(path)
        if rp in hints:
            hints.pop(rp, None)
            _write_raw(path, hints)
            return True
    return False
