"""Per-folder YAML overrides for media item metadata.

Users can place a ``hometools_overrides.yaml`` file in any library subfolder
to override display titles, season/episode numbers and the series name shown
in the UI.  This is especially useful for series with inconsistent filenames
that cannot be fixed by automatic parsing alone.

File format
-----------

.. code-block:: yaml

   # Optional: override the folder display name (shown as "artist" in the UI)
   series_title: "Avatar: Der Herr der Elemente"

   # Optional: audio language override (ISO 639-1) for folders without a
   # recognizable language tag (e.g. "(engl)") in their name.  Only applied
   # when no tag was detected automatically.
   language: "en"

   # Optional: subtitle language override (ISO 639-1).  Only applied when no
   # subtitle hint was detected automatically.
   subtitle_language: "de"

   # Optional: folder-default series intro markers (seconds, or "mm:ss").
   # Enables the Netflix-style "Skip Intro" button for every episode that
   # does not define its own markers.  ``intro_end`` is the position the
   # button seeks to; ``intro_start`` (default 0) is when the button appears.
   intro_start: 0
   intro_end: 90

   # Per-file overrides keyed by filename (not full path)
   episodes:
     "Avatar S01E01 German 2005 DVDRiP REPACK XviD-SiMPTY.avi":
       title: "Der Junge im Eisberg"
     "Avatar S02e08.mp4":
       title: "Die Verfolgungsjagd"
       season: 2
       episode: 8
       # Per-episode intro markers win over the folder default.
       intro_start: 5
       intro_end: "1:35"
     # Per-episode language overrides (win over folder-level language).
     # Useful for folders with mixed-language episodes.
     "Avatar S03E05 English Dub.mp4":
       language: "en"
       subtitle_language: "de"

Any field that is *not* listed in an override keeps its auto-detected value
(from embedded metadata, filename parsing, or folder structure).

Design choices
--------------
- YAML files live **inside the media library** next to the files they
  describe — similar to Jellyfin NFO files or Kodi ``tvshow.nfo``.
- One file per folder keeps overrides localised and easy to maintain.
- Reading YAML is optional: if the file is missing, unreadable, or
  malformed the catalog silently falls back to automatic detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

OVERRIDE_FILENAME = "hometools_overrides.yaml"


@dataclass(frozen=True, slots=True)
class FolderOverrides:
    """Parsed overrides for a single library folder."""

    series_title: str  # empty string → no override
    episodes: dict[str, EpisodeOverride]  # filename → overrides
    language_group: str = ""  # group id for multi-language linking (empty = auto)
    language: str = ""  # ISO 639-1 audio language override (empty = no override)
    subtitle_language: str = ""  # ISO 639-1 subtitle language override (empty = no override)
    intro_start: float = 0.0  # folder-default series intro start in seconds (0.0 = unset)
    intro_end: float = 0.0  # folder-default series intro end in seconds (0.0 = no skippable intro)


@dataclass(frozen=True, slots=True)
class EpisodeOverride:
    """Per-episode override values.  ``None`` means "keep auto-detected"."""

    title: str | None = None
    season: int | None = None
    episode: int | None = None
    language: str | None = None  # ISO 639-1; explicit per-episode override (wins over folder)
    subtitle_language: str | None = None  # ISO 639-1; explicit per-episode override
    intro_start: float | None = None  # seconds; per-episode intro start (wins over folder)
    intro_end: float | None = None  # seconds; per-episode intro end (wins over folder)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _coerce_seconds(value: object) -> float | None:
    """Coerce an intro timestamp into seconds.

    Accepts a plain number (seconds) or a ``"mm:ss"`` / ``"hh:mm:ss"`` string.
    Returns ``None`` when the value is missing or cannot be parsed (so callers
    can distinguish "not set" from ``0``).
    """
    if value is None:
        return None
    if isinstance(value, bool):  # guard: bool is a subclass of int
        return None
    if isinstance(value, int | float):
        return max(0.0, float(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if ":" in text:
                parts = [float(p) for p in text.split(":")]
                total = 0.0
                for p in parts:
                    total = total * 60 + p
                return max(0.0, total)
            return max(0.0, float(text))
        except ValueError:
            return None
    return None


def _parse_overrides(raw: dict) -> FolderOverrides:
    """Turn the raw YAML dict into a typed ``FolderOverrides`` object."""
    series_title = str(raw.get("series_title") or "")
    episodes_raw = raw.get("episodes") or {}
    episodes: dict[str, EpisodeOverride] = {}

    if isinstance(episodes_raw, dict):
        for filename, entry in episodes_raw.items():
            if not isinstance(entry, dict):
                continue
            title = entry.get("title")
            season = entry.get("season")
            episode = entry.get("episode")
            ep_language = entry.get("language")
            ep_sub_language = entry.get("subtitle_language")
            episodes[str(filename)] = EpisodeOverride(
                title=str(title) if title is not None else None,
                season=int(season) if season is not None else None,
                episode=int(episode) if episode is not None else None,
                language=str(ep_language).strip().lower() if ep_language is not None else None,
                subtitle_language=str(ep_sub_language).strip().lower() if ep_sub_language is not None else None,
                intro_start=_coerce_seconds(entry.get("intro_start")),
                intro_end=_coerce_seconds(entry.get("intro_end")),
            )

    language_group = str(raw.get("language_group") or "")
    language = str(raw.get("language") or "").strip().lower()
    subtitle_language = str(raw.get("subtitle_language") or "").strip().lower()

    return FolderOverrides(
        series_title=series_title,
        episodes=episodes,
        language_group=language_group,
        language=language,
        subtitle_language=subtitle_language,
        intro_start=_coerce_seconds(raw.get("intro_start")) or 0.0,
        intro_end=_coerce_seconds(raw.get("intro_end")) or 0.0,
    )


def load_overrides(folder: Path) -> FolderOverrides | None:
    """Load ``hometools_overrides.yaml`` from *folder*.

    Returns ``None`` when no file exists or when parsing fails.
    Never raises.
    """
    path = folder / OVERRIDE_FILENAME
    try:
        if not path.exists():
            return None
    except OSError:
        return None

    try:
        import yaml

        text = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
        if not isinstance(raw, dict):
            logger.warning("Override file %s is not a YAML mapping — ignoring", path)
            return None
        overrides = _parse_overrides(raw)
        logger.debug(
            "Loaded %d episode overrides from %s (series_title=%r)",
            len(overrides.episodes),
            path,
            overrides.series_title,
        )
        return overrides
    except Exception:
        logger.warning("Could not parse override file %s — ignoring", path, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Scanning all library folders at once
# ---------------------------------------------------------------------------


def load_all_overrides(library_root: Path) -> dict[str, FolderOverrides]:
    """Scan *library_root* for override files and return a mapping.

    Keys are the relative folder path (POSIX-style, ``""`` for root).
    Only folders that actually contain an override file are included.
    """
    from hometools.streaming.core.server_utils import safe_resolve

    result: dict[str, FolderOverrides] = {}
    root = safe_resolve(library_root)

    # Check root itself
    root_ov = load_overrides(root)
    if root_ov is not None:
        result[""] = root_ov

    try:
        for sub in sorted(root.rglob("*")):
            if sub.is_dir():
                ov = load_overrides(sub)
                if ov is not None:
                    try:
                        rel = safe_resolve(sub).relative_to(root).as_posix()
                        result[rel] = ov
                    except ValueError:
                        pass
    except OSError:
        logger.debug("Error scanning for override files under %s", library_root, exc_info=True)

    if result:
        total = sum(len(o.episodes) for o in result.values())
        logger.info(
            "Media overrides: %d folder(s) with %d total episode overrides loaded from %s",
            len(result),
            total,
            library_root,
        )

    return result


# ---------------------------------------------------------------------------
# Applying overrides to MediaItems
# ---------------------------------------------------------------------------


def apply_overrides(
    items: list,
    library_root: Path,
    overrides: dict[str, FolderOverrides] | None = None,
) -> list:
    """Apply loaded overrides to a list of ``MediaItem`` instances.

    Since ``MediaItem`` is frozen, new instances are created for any item
    that has an override.  Items without matching overrides pass through
    unchanged.

    Parameters
    ----------
    items:
        The original item list (``list[MediaItem]``).
    library_root:
        Root of the media library (used to resolve relative paths).
    overrides:
        Pre-loaded overrides (from :func:`load_all_overrides`).  If ``None``,
        they are loaded on the fly.
    """
    from hometools.streaming.core.models import MediaItem

    if overrides is None:
        overrides = load_all_overrides(library_root)

    if not overrides:
        return items

    result: list[MediaItem] = []
    applied = 0

    for item in items:
        # Determine which folder this item belongs to
        rel_path = Path(item.relative_path)
        folder_key = rel_path.parent.as_posix() if len(rel_path.parts) > 1 else ""
        filename = rel_path.name

        folder_ov = overrides.get(folder_key)
        if folder_ov is None:
            result.append(item)
            continue

        # Apply series_title as artist override
        new_artist = folder_ov.series_title if folder_ov.series_title else item.artist

        # Apply language overrides only when the item has no auto-detected value
        # (folder override fills the gap for folders without a recognizable tag).
        new_language = folder_ov.language if (folder_ov.language and not item.language) else item.language
        new_subtitle_language = (
            folder_ov.subtitle_language if (folder_ov.subtitle_language and not item.subtitle_language) else item.subtitle_language
        )

        # Apply intro markers: folder-level defaults first (only when set).
        new_intro_start = folder_ov.intro_start if folder_ov.intro_start else item.intro_start
        new_intro_end = folder_ov.intro_end if folder_ov.intro_end else item.intro_end

        # Apply per-episode override
        ep_ov = folder_ov.episodes.get(filename)
        if ep_ov is not None:
            new_title = ep_ov.title if ep_ov.title is not None else item.title
            new_season = ep_ov.season if ep_ov.season is not None else item.season
            new_episode = ep_ov.episode if ep_ov.episode is not None else item.episode
            # Per-episode language explicitly overrides folder + auto-detection.
            if ep_ov.language is not None:
                new_language = ep_ov.language
            if ep_ov.subtitle_language is not None:
                new_subtitle_language = ep_ov.subtitle_language
            # Per-episode intro markers win over folder defaults.
            if ep_ov.intro_start is not None:
                new_intro_start = ep_ov.intro_start
            if ep_ov.intro_end is not None:
                new_intro_end = ep_ov.intro_end
            applied += 1
        else:
            new_title = item.title
            new_season = item.season
            new_episode = item.episode

        # Only create a new instance if something actually changed
        if (
            new_artist == item.artist
            and new_title == item.title
            and new_season == item.season
            and new_episode == item.episode
            and new_language == item.language
            and new_subtitle_language == item.subtitle_language
            and new_intro_start == item.intro_start
            and new_intro_end == item.intro_end
        ):
            result.append(item)
        else:
            result.append(
                MediaItem(
                    relative_path=item.relative_path,
                    title=new_title,
                    artist=new_artist,
                    stream_url=item.stream_url,
                    media_type=item.media_type,
                    thumbnail_url=item.thumbnail_url,
                    rating=item.rating,
                    season=new_season,
                    episode=new_episode,
                    mtime=item.mtime,
                    thumbnail_lg_url=item.thumbnail_lg_url,
                    genre=item.genre,
                    language=new_language,
                    subtitle_language=new_subtitle_language,
                    file_size=item.file_size,
                    duration=item.duration,
                    bitrate=item.bitrate,
                    intro_start=new_intro_start,
                    intro_end=new_intro_end,
                )
            )

    if applied:
        logger.info("Applied %d episode overrides to media items", applied)

    return result


# ---------------------------------------------------------------------------
# Language groups — folder-name → group-id mapping for multi-language linking
# ---------------------------------------------------------------------------


def load_language_groups(library_root: Path) -> dict[str, str]:
    """Scan *library_root* for ``language_group`` overrides.

    Returns a mapping ``{folder_name: group_id}`` for all folders that
    declare a ``language_group`` in their ``hometools_overrides.yaml``.
    Only **top-level** subfolders are considered (direct children of
    *library_root*).

    This allows the JS UI to merge folders like "Malcolm Mittendrin" and
    "Malcolm in the Middle (engl)" into a single display entry when they
    share the same ``language_group`` id.
    """
    result: dict[str, str] = {}
    overrides = load_all_overrides(library_root)
    for rel_path, ov in overrides.items():
        if not ov.language_group:
            continue
        # Only top-level folders (no '/' in path)
        if "/" in rel_path:
            continue
        if rel_path:
            result[rel_path] = ov.language_group
    if result:
        logger.info("Language groups: %d folder(s) linked", len(result))
    return result
