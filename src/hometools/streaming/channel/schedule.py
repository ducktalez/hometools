"""Channel schedule — parse YAML program plans, resolve time slots.

A schedule defines which series episode plays at which time.  Gaps between
scheduled slots are filled with filler content (music / short clips).

Schedule YAML format::

    channel_name: "Haus-TV"
    default_filler: "music"

    schedule:
      - weekday: "daily"
        slots:
          - time: "20:00"
            series: "Breaking Bad"
            strategy: "sequential"
          - time: "21:00"
            series: "Die Simpsons"
            strategy: "random"

      - weekday: "saturday"
        slots:
          - time: "19:00"
            series: "Malcolm Mittendrin"
            strategy: "sequential"
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduleSlot:
    """A single time slot in the channel program."""

    start_time: time
    series_folder: str
    strategy: str = "sequential"  # "sequential" or "random"


@dataclass(frozen=True)
class ResolvedSlot:
    """A slot resolved to a concrete file + timing for the current moment."""

    video_path: Path
    start_dt: datetime
    end_dt: datetime
    series_folder: str
    episode_title: str
    is_filler: bool = False


# ---------------------------------------------------------------------------
# Episode state tracking
# ---------------------------------------------------------------------------


def _episode_state_path(state_dir: Path) -> Path:
    """Return the path to the episode state JSON file."""
    return state_dir / "episode_state.json"


def load_episode_state(state_dir: Path) -> dict[str, int]:
    """Load the per-series episode index (which episode is next).

    Returns ``{series_folder: next_episode_index}``.
    """
    p = _episode_state_path(state_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to load episode state from %s", p, exc_info=True)
        return {}


def save_episode_state(state_dir: Path, state: dict[str, int]) -> bool:
    """Persist the per-series episode index."""
    p = _episode_state_path(state_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        logger.error("Failed to save episode state to %s", p, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Episode resolution
# ---------------------------------------------------------------------------


def list_episodes(library_dir: Path, series_folder: str) -> list[Path]:
    """Return sorted list of video files in a series folder.

    Only includes files with known video extensions.  Sorted alphabetically
    so that ``S01E01`` comes before ``S01E02`` naturally.
    """
    from hometools.constants import VIDEO_SUFFIX

    folder = library_dir / series_folder
    if not folder.is_dir():
        logger.warning("Series folder does not exist: %s", folder)
        return []

    episodes = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIX)
    return episodes


def resolve_next_episode(
    library_dir: Path,
    series_folder: str,
    state_dir: Path,
    strategy: str = "sequential",
) -> Path | None:
    """Determine the next episode to play for a series.

    For ``sequential``: advances through episodes in order, wrapping around.
    For ``random``: picks a random episode.

    Updates the episode state on disk after resolution.
    """
    episodes = list_episodes(library_dir, series_folder)
    if not episodes:
        logger.warning("No episodes found for series %r", series_folder)
        return None

    state = load_episode_state(state_dir)

    if strategy == "random":
        chosen = random.choice(episodes)
    else:
        idx = state.get(series_folder, 0)
        if idx >= len(episodes):
            idx = 0
        chosen = episodes[idx]
        state[series_folder] = idx + 1
        save_episode_state(state_dir, state)

    logger.info("Resolved episode for %r: %s (strategy=%s)", series_folder, chosen.name, strategy)
    return chosen


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------


def parse_schedule_file(schedule_path: Path) -> dict[str, Any]:
    """Parse a channel schedule YAML file.

    Returns the raw parsed dict.  Returns an empty dict on failure.
    """
    try:
        import yaml
    except ImportError:
        logger.error("PyYAML is required for channel schedule parsing (pip install pyyaml)")
        return {}

    if not schedule_path.exists():
        logger.warning("Schedule file not found: %s", schedule_path)
        return {}

    try:
        text = schedule_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        return data
    except Exception:
        logger.error("Failed to parse schedule file %s", schedule_path, exc_info=True)
        return {}


def _parse_time(time_str: str) -> time:
    """Parse a ``HH:MM`` time string."""
    parts = time_str.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def get_slots_for_date(schedule_data: dict[str, Any], dt: datetime) -> list[ScheduleSlot]:
    """Return the schedule slots applicable for a given date.

    More specific weekday rules override ``daily``.
    """
    weekday_num = dt.weekday()
    schedule_list = schedule_data.get("schedule", [])

    daily_slots: list[ScheduleSlot] = []
    specific_slots: list[ScheduleSlot] = []

    for entry in schedule_list:
        weekday_str = str(entry.get("weekday", "")).strip().lower()
        raw_slots = entry.get("slots", [])

        parsed: list[ScheduleSlot] = []
        for s in raw_slots:
            parsed.append(
                ScheduleSlot(
                    start_time=_parse_time(str(s.get("time", "00:00"))),
                    series_folder=str(s.get("series", "")),
                    strategy=str(s.get("strategy", "sequential")),
                )
            )

        if weekday_str == "daily":
            daily_slots.extend(parsed)
        elif _WEEKDAY_MAP.get(weekday_str) == weekday_num:
            specific_slots.extend(parsed)

    # Specific weekday slots override daily slots if present
    result = specific_slots if specific_slots else daily_slots
    result.sort(key=lambda s: s.start_time)
    return result


def get_video_duration(video_path: Path) -> float:
    """Return the duration of a video file in seconds via ffprobe.

    Returns 0.0 on failure.
    """
    import subprocess

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        logger.debug("ffprobe duration failed for %s: %s", video_path.name, exc)
    return 0.0


def resolve_schedule(
    schedule_data: dict[str, Any],
    library_dir: Path,
    state_dir: Path,
    now: datetime | None = None,
    lookahead_hours: int = 6,
) -> list[ResolvedSlot]:
    """Resolve the schedule into concrete file paths and timings.

    Returns a list of :class:`ResolvedSlot` entries covering from *now*
    through the next *lookahead_hours*.

    .. important:: Episode state is only advanced for slots that fall within
        the lookahead window.  Slots outside the window are skipped entirely
        so that the episode counter is not burned through.
    """
    if now is None:
        now = datetime.now()

    slots = get_slots_for_date(schedule_data, now)
    if not slots:
        return []

    today = now.date()
    cutoff = now + timedelta(hours=lookahead_hours)
    resolved: list[ResolvedSlot] = []

    for slot in slots:
        start_dt = datetime.combine(today, slot.start_time)
        if start_dt < now - timedelta(hours=12):
            # Slot is far in the past, skip
            continue

        if start_dt >= cutoff:
            # Slot is outside the lookahead window — do NOT resolve the
            # episode (that would advance the episode counter wastefully).
            continue

        episode = resolve_next_episode(library_dir, slot.series_folder, state_dir, slot.strategy)
        if episode is None:
            continue

        duration = get_video_duration(episode)
        if duration <= 0:
            duration = 1800.0  # fallback: 30 minutes

        end_dt = start_dt + timedelta(seconds=duration)

        if end_dt < now:
            # Slot already finished
            continue

        resolved.append(
            ResolvedSlot(
                video_path=episode,
                start_dt=start_dt,
                end_dt=end_dt,
                series_folder=slot.series_folder,
                episode_title=episode.stem,
            )
        )

    resolved.sort(key=lambda r: r.start_dt)
    return resolved


def get_display_schedule(
    schedule_data: dict[str, Any],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return today's full program for EPG display.

    Unlike :func:`resolve_schedule`, this function does **not** resolve
    episodes or advance any state.  It returns lightweight dicts suitable
    for the ``/api/channel/epg`` endpoint.
    """
    if now is None:
        now = datetime.now()

    slots = get_slots_for_date(schedule_data, now)
    if not slots:
        return []

    today = now.date()
    result: list[dict[str, Any]] = []

    for slot in slots:
        start_dt = datetime.combine(today, slot.start_time)
        result.append(
            {
                "series": slot.series_folder,
                "episode": "",
                "start": start_dt.isoformat(),
                "end": "",
                "is_filler": False,
            }
        )

    result.sort(key=lambda r: r["start"])
    return result


def get_fill_series(schedule_data: dict[str, Any]) -> list[str]:
    """Return the list of series folder names for fill programming.

    ``fill_series`` in the schedule YAML defines which series are used
    to generate continuous content when no scheduled slot is active.
    Episodes are picked at random from these series.

    Returns an empty list if not configured (falls back to test card).
    """
    raw = schedule_data.get("fill_series", [])
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if str(s).strip()]
    return []
