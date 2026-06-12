"""Skip-Intro marker storage, auto-detection and application.

A *marker* describes the skippable opening credits of a series episode as a
pair ``(intro_start, intro_end)`` in seconds.  The UI shows a Netflix-style
"Skip Intro" button while playback is inside ``[intro_start, intro_end]`` and
seeks to ``intro_end`` when the user taps it.

Three sources feed the markers, in **descending** precedence:

1. **Manual markers** set live from the player ("set intro end here") — stored
   server-side here in ``<cache_dir>/intro_markers/<server>.json`` so they
   survive a browser clear and sync across devices.  Manual markers win over
   everything (including YAML).
2. **YAML overrides** (``intro_start`` / ``intro_end`` in
   ``hometools_overrides.yaml``) — applied earlier in the catalog pipeline via
   :func:`hometools.streaming.core.media_overrides.apply_overrides`.
3. **Auto-detected markers** from embedded chapter metadata (ffprobe) — only
   fill the gap when no manual / YAML value exists.

Why no "internet data"?  There is **no reliable free public API** for intro
timestamps (TMDB does not provide them).  The robust automatic technique is
cross-episode audio fingerprinting (cf. Jellyfin's *Intro Skipper* plugin),
which is heavy (chromaprint over whole seasons).  Chapter-marker detection is
a cheap, network-free approximation that works for the (many) releases that
ship named "Intro"/"Opening" chapters.  Fingerprinting is tracked as a future
TODO.

Storage layout::

    <cache_dir>/intro_markers/<server>.json
    {
      "markers": {
        "Series/S01E01.mp4": {"start": 0.0, "end": 92.0, "source": "manual"},
        ...
      }
    }

Thread-safe (module-level lock), atomic writes, and every public function is
exception-safe (returns sensible defaults, never raises).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

logger = logging.getLogger(__name__)

_MARKER_DIR = "intro_markers"
_MAX_MARKERS = 50000

# Chapter titles that indicate an intro / opening-credits section.  Matched
# case-insensitively as a substring of the chapter title.
_INTRO_CHAPTER_KEYWORDS = (
    "intro",
    "opening",
    "op credit",
    "opening credit",
    "title sequence",
    "main title",
    "theme",
    "vorspann",
    "recap",
)

# An intro chapter longer than this is almost certainly a mis-tagged content
# chapter — ignore it so we never skip half an episode.
_MAX_INTRO_SECONDS = 300.0

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _marker_path(cache_dir: Path, server: str) -> Path:
    """Return the on-disk path for the marker store of *server*."""
    return cache_dir / _MARKER_DIR / f"{server}.json"


def _read_raw(path: Path) -> dict[str, Any]:
    """Read the marker store from disk (caller must hold ``_lock``)."""
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        markers = data.get("markers")
        return markers if isinstance(markers, dict) else {}
    except Exception:
        logger.debug("Failed to read intro markers from %s", path, exc_info=True)
        return {}


def _write_raw(path: Path, markers: dict[str, Any]) -> None:
    """Atomically write the marker store to disk (caller must hold ``_lock``)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            suffix=".json",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump({"markers": markers}, tmp, ensure_ascii=False, indent=2)
            tmp_path_obj = Path(tmp.name)
        tmp_path_obj.replace(path)
    except Exception:
        logger.debug("Failed to write intro markers to %s", path, exc_info=True)


def _normalize(start: object, end: object) -> tuple[float, float]:
    """Coerce a ``(start, end)`` pair into clamped, ordered seconds."""
    try:
        s = max(0.0, float(start or 0.0))
    except (TypeError, ValueError):
        s = 0.0
    try:
        e = max(0.0, float(end or 0.0))
    except (TypeError, ValueError):
        e = 0.0
    if e and e < s:
        s, e = 0.0, e
    return s, e


def load_markers(cache_dir: Path, server: str) -> dict[str, dict[str, float]]:
    """Return ``{relative_path: {"start", "end", "source"}}`` for *server*."""
    with _lock:
        return _read_raw(_marker_path(cache_dir, server))


def get_marker(cache_dir: Path, server: str, relative_path: str) -> dict[str, float] | None:
    """Return the marker for *relative_path*, or ``None`` if none is stored."""
    with _lock:
        markers = _read_raw(_marker_path(cache_dir, server))
        entry = markers.get(relative_path)
        return entry if isinstance(entry, dict) else None


def set_marker(
    cache_dir: Path,
    server: str,
    relative_path: str,
    *,
    start: float,
    end: float,
    source: str = "manual",
) -> dict[str, float] | None:
    """Persist a marker for *relative_path*.

    ``source`` is ``"manual"`` (user set it in the UI / explicit) or ``"auto"``
    (chapter detection).  Manual markers are never overwritten by auto markers.
    Returns the stored entry, or ``None`` on failure / empty key.
    """
    rp = (relative_path or "").strip()
    if not rp:
        return None
    s, e = _normalize(start, end)
    entry = {"start": s, "end": e, "source": "auto" if source == "auto" else "manual"}
    with _lock:
        path = _marker_path(cache_dir, server)
        markers = _read_raw(path)
        # Never let an auto marker clobber a manual one.
        existing = markers.get(rp)
        if entry["source"] == "auto" and isinstance(existing, dict) and existing.get("source") == "manual":
            return existing  # type: ignore[return-value]
        if len(markers) >= _MAX_MARKERS and rp not in markers:
            return None
        markers[rp] = entry
        _write_raw(path, markers)
    return entry


def delete_marker(cache_dir: Path, server: str, relative_path: str) -> bool:
    """Delete the marker for *relative_path*.  Returns ``True`` if removed."""
    rp = (relative_path or "").strip()
    if not rp:
        return False
    with _lock:
        path = _marker_path(cache_dir, server)
        markers = _read_raw(path)
        if rp in markers:
            markers.pop(rp, None)
            _write_raw(path, markers)
            return True
    return False


# ---------------------------------------------------------------------------
# Applying markers to MediaItems
# ---------------------------------------------------------------------------


def apply_intro_markers(items: list, cache_dir: Path, server: str) -> list:
    """Return *items* with stored intro markers merged in.

    ``MediaItem`` is frozen, so changed items are recreated.  Precedence:

    - ``source == "manual"`` markers **override** any existing (YAML) value.
    - ``source == "auto"`` markers only fill items that have no ``intro_end``
      yet (so YAML / manual always win).

    Never raises; on any error the original list is returned unchanged.
    """
    try:
        from dataclasses import replace

        markers = load_markers(cache_dir, server)
        if not markers:
            return items

        result = []
        patched = 0
        for item in items:
            entry = markers.get(getattr(item, "relative_path", ""))
            if not isinstance(entry, dict):
                result.append(item)
                continue
            end = float(entry.get("end") or 0.0)
            start = float(entry.get("start") or 0.0)
            is_manual = entry.get("source") != "auto"
            if not is_manual and getattr(item, "intro_end", 0.0):
                # Auto marker must not override an existing YAML value.
                result.append(item)
                continue
            if end == getattr(item, "intro_end", 0.0) and start == getattr(item, "intro_start", 0.0):
                result.append(item)
                continue
            try:
                result.append(replace(item, intro_start=start, intro_end=end))
                patched += 1
            except Exception:
                result.append(item)
        if patched:
            logger.info("Applied %d stored intro markers (%s)", patched, server)
        return result
    except Exception:
        logger.debug("apply_intro_markers failed for %s", server, exc_info=True)
        return items


# ---------------------------------------------------------------------------
# Auto-detection via embedded chapter metadata (ffprobe)
# ---------------------------------------------------------------------------


def detect_intro_from_chapters(path: Path) -> tuple[float, float] | None:
    """Detect an intro window from embedded chapter markers via ffprobe.

    Returns ``(start_seconds, end_seconds)`` for the first chapter whose title
    looks like an intro / opening-credits section, or ``None`` when ffprobe is
    unavailable, the file has no such chapter, or detection fails.

    Never raises.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_chapters",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        data = json.loads(proc.stdout)
        chapters = data.get("chapters")
        if not isinstance(chapters, list):
            return None
        for chap in chapters:
            if not isinstance(chap, dict):
                continue
            tags = chap.get("tags") or {}
            title = str(tags.get("title") or "").strip().lower()
            if not title:
                continue
            if not any(kw in title for kw in _INTRO_CHAPTER_KEYWORDS):
                continue
            try:
                start = max(0.0, float(chap.get("start_time") or 0.0))
                end = max(0.0, float(chap.get("end_time") or 0.0))
            except (TypeError, ValueError):
                continue
            if end <= start:
                continue
            if (end - start) > _MAX_INTRO_SECONDS:
                continue
            return start, end
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        logger.debug("ffprobe chapter detection failed for %s", path, exc_info=True)
    except Exception:
        logger.debug("Unexpected error during chapter detection for %s", path, exc_info=True)
    return None


def start_background_intro_detection(
    work: list[tuple[Path, str]],
    cache_dir: Path,
    server: str = "video",
) -> bool:
    """Detect intro chapters for *work* in a daemon thread.

    *work* is a list of ``(absolute_path, relative_path)`` tuples.  Files that
    already have a stored marker (manual or auto) are skipped.  Detected
    windows are written to the marker store with ``source="auto"``.

    Returns ``True`` if a worker thread was started, ``False`` otherwise.
    Best-effort and exception-safe — never blocks the caller.
    """
    if not work or not shutil.which("ffprobe"):
        return False

    def _run() -> None:
        try:
            existing = load_markers(cache_dir, server)
            detected = 0
            for abs_path, rel_path in work:
                if rel_path in existing:
                    continue
                try:
                    window = detect_intro_from_chapters(abs_path)
                except Exception:
                    window = None
                if window is None:
                    continue
                set_marker(
                    cache_dir,
                    server,
                    rel_path,
                    start=window[0],
                    end=window[1],
                    source="auto",
                )
                detected += 1
            if detected:
                logger.info("Intro auto-detection: %d chapter-based markers stored (%s)", detected, server)
        except Exception:
            logger.debug("Background intro detection failed", exc_info=True)

    threading.Thread(target=_run, daemon=True, name="intro-detect").start()
    return True
