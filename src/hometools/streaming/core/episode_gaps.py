"""Detect missing individual episodes inside series seasons.

A *gap* is an episode number that is missing **between** the first and last
present episode of a season.  Whole missing seasons are deliberately **not**
reported — only single (or several) episodes that fall inside an existing
season's range.  Example: a folder containing ``S01E01``, ``S01E02`` and
``S01E04`` yields one gap for the missing ``S01E03``.

Design rules (local)
---------------------
- Pure function over ``list[MediaItem]`` — no filesystem access, no I/O.
- Works off the already-built catalog (``season`` / ``episode`` are parsed by
  :func:`hometools.streaming.core.catalog.parse_season_episode`).
- ``find_missing_episodes`` never raises; returns ``[]`` on any failure.
- A season needs at least ``min_present`` distinct episodes before gaps are
  reported — a single episode gives no reliable range to interpolate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from hometools.streaming.core.models import MediaItem

logger = logging.getLogger(__name__)

# A season must contain at least this many distinct episodes before we trust
# its range enough to flag interior gaps.
_DEFAULT_MIN_PRESENT = 2


@dataclass(frozen=True)
class SeasonGap:
    """Missing interior episodes for one (series, season) group."""

    series: str  # display name of the series (top-level folder)
    folder: str  # POSIX relative path of the folder holding the episodes
    season: int
    present_episodes: list[int] = field(default_factory=list)
    missing_episodes: list[int] = field(default_factory=list)
    first_episode: int = 0
    last_episode: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "series": self.series,
            "folder": self.folder,
            "season": self.season,
            "present_episodes": list(self.present_episodes),
            "missing_episodes": list(self.missing_episodes),
            "missing_count": len(self.missing_episodes),
            "first_episode": self.first_episode,
            "last_episode": self.last_episode,
        }


def _group_key(item: MediaItem) -> tuple[str, int]:
    """Return a ``(folder, season)`` grouping key for a series episode.

    Grouping by the *immediate parent folder* (rather than only the top-level
    series name) keeps unrelated shows apart even when they share a generic
    library layout and guarantees that each season's files are interpreted in
    isolation.
    """
    parent = PurePosixPath(item.relative_path).parent.as_posix()
    if parent == ".":
        parent = ""
    return parent, int(item.season)


def find_missing_episodes(
    items: list[MediaItem],
    *,
    min_present: int = _DEFAULT_MIN_PRESENT,
) -> list[SeasonGap]:
    """Return interior episode gaps per (folder, season), sorted for display.

    Parameters
    ----------
    items:
        The media catalog (audio or video).  Only items with ``season > 0``
        and ``episode > 0`` are considered.
    min_present:
        Minimum number of distinct episodes a season must have before its
        interior gaps are reported (default ``2``).

    Returns
    -------
    list[SeasonGap]
        One entry per season that has at least one missing interior episode.
        Never raises — returns ``[]`` on any error.
    """
    try:
        return _do_find(items, min_present=max(int(min_present), 1))
    except Exception:
        logger.warning("find_missing_episodes failed", exc_info=True)
        return []


def _do_find(items: list[MediaItem], *, min_present: int) -> list[SeasonGap]:
    grouped: dict[tuple[str, int], dict[str, Any]] = {}

    for item in items:
        season = int(getattr(item, "season", 0) or 0)
        episode = int(getattr(item, "episode", 0) or 0)
        if season <= 0 or episode <= 0:
            continue
        key = _group_key(item)
        bucket = grouped.setdefault(
            key,
            {"episodes": set(), "series": "", "folder": key[0]},
        )
        bucket["episodes"].add(episode)
        # Prefer a non-empty series/artist label for display.
        if not bucket["series"]:
            top = PurePosixPath(item.relative_path).parts
            bucket["series"] = item.artist or (top[0] if top else "")

    gaps: list[SeasonGap] = []
    for (folder, season), bucket in grouped.items():
        eps: set[int] = bucket["episodes"]
        if len(eps) < min_present:
            continue
        first = min(eps)
        last = max(eps)
        missing = [e for e in range(first, last + 1) if e not in eps]
        if not missing:
            continue
        gaps.append(
            SeasonGap(
                series=str(bucket["series"]) or folder or "(unbekannt)",
                folder=folder,
                season=season,
                present_episodes=sorted(eps),
                missing_episodes=missing,
                first_episode=first,
                last_episode=last,
            )
        )

    gaps.sort(key=lambda g: (g.series.casefold(), g.season, g.folder.casefold()))
    return gaps
