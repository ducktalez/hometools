"""Library structure analysis for hometools.

A read-only examination of a media library that reports actionable hints
about folder organisation, episode naming, and language tagging.

Public API
----------
``scan_video_library(library_dir, overrides=None) -> ScanReport``
``scan_audio_library(library_dir) -> ScanReport``

Each report contains a list of :class:`ScanIssue` entries with a stable
``check`` code so callers can filter by category.

Available checks (video)
------------------------
- ``episode_naming``   — Series folders where most files lack S/E numbering.
- ``oversized_folder`` — Folders with many direct files but no sub-structure.
- ``untagged_language``— Top-level folders with no language hint and no override.

Available checks (audio)
------------------------
- ``oversized_folder`` — Same oversized-folder check, tuned for audio.

Design rules
------------
- No I/O side effects; never modify the library.
- All public functions return sane defaults on any exception.
- No subprocess / ffprobe calls; pure filesystem scanning.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hometools.constants import AUDIO_SUFFIX, VIDEO_SUFFIX

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (tuneable for testing via keyword arguments)
# ---------------------------------------------------------------------------

_VIDEO_OVERSIZED_THRESHOLD = 30  # direct video files → organisational concern
_AUDIO_OVERSIZED_THRESHOLD = 100  # direct audio files
_EPISODE_NAMING_MIN_FILES = 4  # minimum files to trigger naming check
_EPISODE_NAMING_MIN_RATIO = 0.5  # fraction of files that must be parseable

# S01E01 / 1x01 / 01x01 patterns (same as parse_season_episode in catalog)
_SE_PATTERN = re.compile(
    r"(?:s\d{1,2}e\d{1,2}|\d{1,2}x\d{2})",
    re.IGNORECASE,
)

# Language tag pattern — (de), (engl), (english), etc.
_LANG_TAG_PATTERN = re.compile(
    r"\((?:de|en|eng|engl|english|german|fr|es|it|ja|ko|zh|pt|ru|"
    r"deutsch|french|spanish|italian|japanese|korean|chinese|portuguese|russian)"
    r"(?:[^)]*\))|\(",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScanIssue:
    """A single finding from a library scan."""

    check: str  # stable check code
    severity: str  # "warning" | "info"
    folder: str  # relative POSIX path of the affected folder
    message: str  # human-readable description
    hint: str  # actionable suggestion (CLI command or YAML snippet)


@dataclass
class ScanReport:
    """Aggregated results of a library scan."""

    library_dir: Path
    media_type: str  # "video" | "audio"
    issues: list[ScanIssue] = field(default_factory=list)
    scanned_folders: int = 0
    checked_files: int = 0

    @property
    def warnings(self) -> list[ScanIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[ScanIssue]:
        return [i for i in self.issues if i.severity == "info"]

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "library_dir": str(self.library_dir),
            "media_type": self.media_type,
            "scanned_folders": self.scanned_folders,
            "checked_files": self.checked_files,
            "issue_count": len(self.issues),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "check": i.check,
                    "severity": i.severity,
                    "folder": i.folder,
                    "message": i.message,
                    "hint": i.hint,
                }
                for i in self.issues
            ],
        }


# ---------------------------------------------------------------------------
# Individual check helpers
# ---------------------------------------------------------------------------


def _has_lang_tag(folder_name: str) -> bool:
    """Return True if *folder_name* contains a language tag like ``(engl)``."""
    # Simple keyword check — more lenient than the full language.py parser
    lower = folder_name.lower()
    tokens = (
        "(de)",
        "(en)",
        "(eng)",
        "(engl)",
        "(english)",
        "(german)",
        "(deutsch)",
        "(fr)",
        "(french)",
        "(es)",
        "(spanish)",
        "(it)",
        "(italian)",
        "(ja)",
        "(japanese)",
        "(ko)",
        "(korean)",
        "(zh)",
        "(chinese)",
        "(pt)",
        "(portuguese)",
        "(ru)",
        "(russian)",
    )
    return any(t in lower for t in tokens)


def _check_episode_naming(
    folder_rel: str,
    video_files: list[Path],
    *,
    min_files: int = _EPISODE_NAMING_MIN_FILES,
    min_ratio: float = _EPISODE_NAMING_MIN_RATIO,
) -> ScanIssue | None:
    """Return an issue if too few files in *video_files* have S/E numbering."""
    if len(video_files) < min_files:
        return None
    parseable = sum(1 for f in video_files if _SE_PATTERN.search(f.stem))
    ratio = parseable / len(video_files)
    if ratio >= min_ratio:
        return None
    return ScanIssue(
        check="episode_naming",
        severity="warning",
        folder=folder_rel,
        message=(
            f"{len(video_files)} Videodatei(en) — nur {parseable} ({int(ratio * 100)} %) "
            f"enthalten eine erkennbare Staffel-/Episodennummer (S##E##)."
        ),
        hint=(f"hometools generate-overrides \"{folder_rel}\"  # oder manuell 'season'/'episode' in hometools_overrides.yaml eintragen"),
    )


def _check_oversized_flat(
    folder_rel: str,
    direct_files: list[Path],
    *,
    threshold: int,
    media_label: str,
) -> ScanIssue | None:
    """Return an issue if *direct_files* exceeds *threshold* without sub-folders."""
    if len(direct_files) <= threshold:
        return None
    return ScanIssue(
        check="oversized_folder",
        severity="info",
        folder=folder_rel,
        message=(f"{len(direct_files)} {media_label}-Dateien direkt im Ordner ohne Unterordner-Struktur."),
        hint="Staffeln in Unterordner aufteilen (z.B. Staffel 1/, Staffel 2/) für bessere Navigation.",
    )


def _check_untagged_language(
    folder_rel: str,
    folder_name: str,
    has_override_language: bool,
    has_override_group: bool,
) -> ScanIssue | None:
    """Return an issue if the folder has no language hint at all."""
    if _has_lang_tag(folder_name):
        return None  # tag in folder name — auto-detection will work
    if has_override_language or has_override_group:
        return None  # YAML override covers it
    return ScanIssue(
        check="untagged_language",
        severity="info",
        folder=folder_rel,
        message=("Kein Sprach-Tag im Ordnernamen erkannt und kein Override vorhanden. Sprache unbekannt."),
        hint=('hometools_overrides.yaml im Ordner anlegen mit: language: "de"  # oder "en", "fr", …'),
    )


# ---------------------------------------------------------------------------
# Main scan functions
# ---------------------------------------------------------------------------


def scan_video_library(
    library_dir: Path,
    overrides: dict | None = None,
    *,
    oversized_threshold: int = _VIDEO_OVERSIZED_THRESHOLD,
    episode_naming_min_files: int = _EPISODE_NAMING_MIN_FILES,
    episode_naming_min_ratio: float = _EPISODE_NAMING_MIN_RATIO,
) -> ScanReport:
    """Scan *library_dir* for video library structure issues.

    Parameters
    ----------
    library_dir:
        Root of the video library.
    overrides:
        Pre-loaded overrides dict (``{folder_rel: FolderOverrides}``).
        If ``None``, loaded automatically via ``load_all_overrides``.
    oversized_threshold:
        Number of direct video files that triggers an ``oversized_folder`` issue.

    Returns
    -------
    :class:`ScanReport` — never raises.
    """
    report = ScanReport(library_dir=library_dir, media_type="video")
    try:
        return _do_scan_video(
            library_dir,
            overrides,
            report,
            oversized_threshold=oversized_threshold,
            episode_naming_min_files=episode_naming_min_files,
            episode_naming_min_ratio=episode_naming_min_ratio,
        )
    except Exception:
        logger.warning("scan_video_library failed for %s", library_dir, exc_info=True)
        return report


def scan_audio_library(
    library_dir: Path,
    *,
    oversized_threshold: int = _AUDIO_OVERSIZED_THRESHOLD,
) -> ScanReport:
    """Scan *library_dir* for audio library structure issues.

    Returns
    -------
    :class:`ScanReport` — never raises.
    """
    report = ScanReport(library_dir=library_dir, media_type="audio")
    try:
        return _do_scan_audio(library_dir, report, oversized_threshold=oversized_threshold)
    except Exception:
        logger.warning("scan_audio_library failed for %s", library_dir, exc_info=True)
        return report


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _do_scan_video(
    library_dir: Path,
    overrides: dict | None,
    report: ScanReport,
    *,
    oversized_threshold: int,
    episode_naming_min_files: int,
    episode_naming_min_ratio: float,
) -> ScanReport:
    from hometools.streaming.core.server_utils import safe_resolve

    root = safe_resolve(library_dir)
    if not root.is_dir():
        return report

    # Load overrides once (may be expensive on NAS)
    if overrides is None:
        try:
            from hometools.streaming.core.media_overrides import load_all_overrides

            overrides = load_all_overrides(root)
        except Exception:
            overrides = {}

    video_suffix_set = {s.lower() for s in VIDEO_SUFFIX}

    # Walk top-level subdirectories (direct children of library root)
    try:
        top_level_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    except OSError:
        return report

    for folder in top_level_dirs:
        folder_name = folder.name
        folder_rel = folder_name  # top-level only for language check

        try:
            entries = list(folder.iterdir())
        except OSError:
            continue

        sub_dirs = [e for e in entries if e.is_dir()]
        video_files = [e for e in entries if e.is_file() and e.suffix.lower() in video_suffix_set]

        report.scanned_folders += 1
        report.checked_files += len(video_files)

        # ── Check 1: Oversized flat folder ──────────────────────────────────
        if not sub_dirs:
            issue = _check_oversized_flat(
                folder_rel,
                video_files,
                threshold=oversized_threshold,
                media_label="Video",
            )
            if issue:
                report.issues.append(issue)

        # ── Check 2: Episode naming ──────────────────────────────────────────
        # Only direct video files (not in sub-folders)
        ep_issue = _check_episode_naming(
            folder_rel,
            video_files,
            min_files=episode_naming_min_files,
            min_ratio=episode_naming_min_ratio,
        )
        if ep_issue:
            report.issues.append(ep_issue)

        # ── Check 3: Untagged language (top-level only) ──────────────────────
        ov = overrides.get(folder_rel)
        has_lang_ov = bool(ov and ov.language)
        has_group_ov = bool(ov and ov.language_group)
        lang_issue = _check_untagged_language(folder_rel, folder_name, has_lang_ov, has_group_ov)
        if lang_issue:
            report.issues.append(lang_issue)

        # ── Recurse into sub-dirs for episode naming only ──────────────────
        for sub in sub_dirs:
            sub_rel = f"{folder_rel}/{sub.name}"
            try:
                sub_videos = [e for e in sub.iterdir() if e.is_file() and e.suffix.lower() in video_suffix_set]
            except OSError:
                continue

            report.scanned_folders += 1
            report.checked_files += len(sub_videos)

            ep_issue = _check_episode_naming(
                sub_rel,
                sub_videos,
                min_files=episode_naming_min_files,
                min_ratio=episode_naming_min_ratio,
            )
            if ep_issue:
                report.issues.append(ep_issue)

    return report


def _do_scan_audio(
    library_dir: Path,
    report: ScanReport,
    *,
    oversized_threshold: int,
) -> ScanReport:
    from hometools.streaming.core.server_utils import safe_resolve

    root = safe_resolve(library_dir)
    if not root.is_dir():
        return report

    audio_suffix_set = {s.lower() for s in AUDIO_SUFFIX}

    try:
        top_level_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    except OSError:
        return report

    for folder in top_level_dirs:
        folder_rel = folder.name
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue

        sub_dirs = [e for e in entries if e.is_dir()]
        audio_files = [e for e in entries if e.is_file() and e.suffix.lower() in audio_suffix_set]

        report.scanned_folders += 1
        report.checked_files += len(audio_files)

        if not sub_dirs:
            issue = _check_oversized_flat(
                folder_rel,
                audio_files,
                threshold=oversized_threshold,
                media_label="Audio",
            )
            if issue:
                report.issues.append(issue)

    return report
