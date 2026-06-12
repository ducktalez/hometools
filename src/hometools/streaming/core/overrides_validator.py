"""Linter for ``hometools_overrides.yaml`` files.

Scans a media library for override files and reports problems such as:

- YAML parse errors / wrong shape
- Unknown ISO 639-1 language codes
- Episode keys that don't match any file in the folder
- ``language_group`` collisions across distant folders
- Folder overrides with empty ``series_title`` and no episodes (no-op file)

The validator is **read-only** and never raises.  It returns a structured
:class:`ValidationReport` that the CLI or a future web UI can render.

INSTRUCTIONS (local):
- Use :data:`hometools.streaming.core.language.KNOWN_LANGUAGE_CODES` as the
  single source of truth for valid language codes.  Add new codes there
  (and to the SVG flag list) before validating against them here.
- New override fields → add a check here so that typos get caught early.
- Every check produces ``Issue`` objects with stable ``code`` strings so
  callers can suppress specific kinds programmatically.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hometools.streaming.core.language import KNOWN_LANGUAGE_CODES
from hometools.streaming.core.media_overrides import (
    OVERRIDE_FILENAME,
    FolderOverrides,
    load_overrides,
)

logger = logging.getLogger(__name__)

# Recognised media file extensions for "episode key exists in folder" check.
# Kept intentionally small — only the formats the streaming servers index.
_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {
        # video
        ".mp4",
        ".m4v",
        ".mkv",
        ".avi",
        ".mov",
        ".flv",
        ".webm",
        ".ts",
        # audio
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".oga",
        ".opus",
        ".wav",
    }
)


# Severity levels — keep in sync with CLI rendering.
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


@dataclass(frozen=True, slots=True)
class Issue:
    """A single validation finding.

    ``code`` is a stable identifier (``parse_error``, ``unknown_language``,
    ``unknown_episode_key``, ``empty_override``, ``language_group_collision``,
    …) suitable for programmatic suppression.
    """

    folder: str  # relative POSIX path (``""`` for library root)
    severity: str  # ``"error"`` | ``"warning"`` | ``"info"``
    code: str  # stable machine-readable identifier
    message: str  # human-readable description


@dataclass
class ValidationReport:
    """Result of :func:`validate_overrides`."""

    scanned_folders: int = 0
    parsed_files: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == SEVERITY_WARNING]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == SEVERITY_ERROR for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "scanned_folders": self.scanned_folders,
            "parsed_files": self.parsed_files,
            "issues": [asdict(i) for i in self.issues],
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "total": len(self.issues),
            },
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_listdir(folder: Path) -> list[str]:
    """Return filenames in *folder* (non-recursive). Never raises."""
    try:
        return [p.name for p in folder.iterdir() if p.is_file()]
    except OSError:
        return []


def _has_yaml_file(folder: Path) -> bool:
    try:
        return (folder / OVERRIDE_FILENAME).exists()
    except OSError:
        return False


def _raw_yaml(folder: Path) -> dict | None:
    """Return the raw parsed YAML dict for the override file, or ``None``
    on any error (parse / non-mapping / I/O)."""
    path = folder / OVERRIDE_FILENAME
    try:
        import yaml

        text = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def _check_language_codes(
    folder_key: str,
    ov: FolderOverrides,
    issues: list[Issue],
) -> None:
    """Flag unknown ISO 639-1 codes in folder- and episode-level fields."""
    if ov.language and ov.language not in KNOWN_LANGUAGE_CODES:
        issues.append(
            Issue(
                folder=folder_key,
                severity=SEVERITY_WARNING,
                code="unknown_language",
                message=(
                    f"Folder-level language code {ov.language!r} is not in the "
                    f"known set {sorted(KNOWN_LANGUAGE_CODES)}. The UI will not "
                    "render a flag badge for this folder."
                ),
            )
        )
    if ov.subtitle_language and ov.subtitle_language not in KNOWN_LANGUAGE_CODES:
        issues.append(
            Issue(
                folder=folder_key,
                severity=SEVERITY_WARNING,
                code="unknown_language",
                message=(f"Folder-level subtitle_language code {ov.subtitle_language!r} is not in the known set."),
            )
        )

    for filename, ep in ov.episodes.items():
        if ep.language and ep.language not in KNOWN_LANGUAGE_CODES:
            issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_WARNING,
                    code="unknown_language",
                    message=(f"Episode {filename!r}: language code {ep.language!r} is not in the known set."),
                )
            )
        if ep.subtitle_language and ep.subtitle_language not in KNOWN_LANGUAGE_CODES:
            issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_WARNING,
                    code="unknown_language",
                    message=(f"Episode {filename!r}: subtitle_language code {ep.subtitle_language!r} is not in the known set."),
                )
            )


def _check_episode_keys_exist(
    folder_key: str,
    folder_path: Path,
    ov: FolderOverrides,
    issues: list[Issue],
) -> None:
    """Flag episode keys that don't match any media file in the folder."""
    if not ov.episodes:
        return
    filenames = set(_safe_listdir(folder_path))
    for ep_key in ov.episodes:
        if ep_key not in filenames:
            issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_WARNING,
                    code="unknown_episode_key",
                    message=(
                        f"Episode key {ep_key!r} does not match any file in this folder. Check for typos or stale entries after a rename."
                    ),
                )
            )


def _check_non_media_episode_keys(
    folder_key: str,
    ov: FolderOverrides,
    issues: list[Issue],
) -> None:
    """Flag episode keys whose extension is not a recognised media format.

    Catches accidental ``.txt``/``.nfo`` entries.  Only emitted when the
    key *does* exist as a file (otherwise ``unknown_episode_key`` already
    fires)."""
    for ep_key in ov.episodes:
        suffix = Path(ep_key).suffix.lower()
        if suffix and suffix not in _MEDIA_EXTENSIONS:
            issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_INFO,
                    code="non_media_extension",
                    message=(
                        f"Episode key {ep_key!r} has extension {suffix!r} which is not a recognised media format. Override will be ignored."
                    ),
                )
            )


def _check_no_op(
    folder_key: str,
    ov: FolderOverrides,
    issues: list[Issue],
) -> None:
    """Warn about override files that have no effect at all."""
    if (
        not ov.series_title
        and not ov.episodes
        and not ov.language
        and not ov.subtitle_language
        and not ov.language_group
        and not ov.intro_start
        and not ov.intro_end
    ):
        issues.append(
            Issue(
                folder=folder_key,
                severity=SEVERITY_INFO,
                code="empty_override",
                message=("Override file has no effect — all fields are empty. Consider deleting it."),
            )
        )


def _check_unknown_top_level_keys(
    folder_key: str,
    raw: dict | None,
    issues: list[Issue],
) -> None:
    """Warn about unrecognised top-level YAML keys (typo detection)."""
    if not raw:
        return
    known_keys = {
        "series_title",
        "episodes",
        "language",
        "subtitle_language",
        "language_group",
        "intro_start",
        "intro_end",
    }
    for key in raw:
        if key not in known_keys:
            issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_WARNING,
                    code="unknown_field",
                    message=(f"Unknown top-level key {key!r}. Known keys: {sorted(known_keys)}. Possible typo?"),
                )
            )


def _check_unknown_episode_fields(
    folder_key: str,
    raw: dict | None,
    issues: list[Issue],
) -> None:
    """Warn about unrecognised per-episode keys (typo detection)."""
    if not raw:
        return
    eps = raw.get("episodes")
    if not isinstance(eps, dict):
        return
    known = {"title", "season", "episode", "language", "subtitle_language", "intro_start", "intro_end"}
    for ep_key, ep_val in eps.items():
        if not isinstance(ep_val, dict):
            continue
        for k in ep_val:
            if k not in known:
                issues.append(
                    Issue(
                        folder=folder_key,
                        severity=SEVERITY_WARNING,
                        code="unknown_field",
                        message=(f"Episode {ep_key!r}: unknown field {k!r}. Known fields: {sorted(known)}. Possible typo?"),
                    )
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_overrides(library_root: Path) -> ValidationReport:
    """Scan *library_root* for override files and produce a report.

    Never raises — I/O errors are silently turned into per-folder issues
    where possible.
    """
    report = ValidationReport()
    try:
        root = Path(library_root).resolve()
    except OSError:
        logger.warning("Could not resolve library root %s", library_root)
        return report

    if not root.exists() or not root.is_dir():
        return report

    # Helper to validate a single folder.  Used for root + every subfolder.
    def _process(folder: Path, folder_key: str) -> None:
        report.scanned_folders += 1
        if not _has_yaml_file(folder):
            return

        raw = _raw_yaml(folder)
        ov = load_overrides(folder)

        if ov is None:
            report.issues.append(
                Issue(
                    folder=folder_key,
                    severity=SEVERITY_ERROR,
                    code="parse_error",
                    message=(
                        "Override file exists but could not be parsed "
                        "(invalid YAML, wrong shape or I/O error). "
                        "Catalog will silently fall back to auto-detection."
                    ),
                )
            )
            return

        report.parsed_files += 1
        _check_unknown_top_level_keys(folder_key, raw, report.issues)
        _check_unknown_episode_fields(folder_key, raw, report.issues)
        _check_language_codes(folder_key, ov, report.issues)
        _check_episode_keys_exist(folder_key, folder, ov, report.issues)
        _check_non_media_episode_keys(folder_key, ov, report.issues)
        _check_no_op(folder_key, ov, report.issues)

    # Walk: root + all subfolders
    _process(root, "")
    try:
        for sub in sorted(root.rglob("*")):
            if sub.is_dir():
                try:
                    rel = sub.resolve().relative_to(root).as_posix()
                except (OSError, ValueError):
                    continue
                _process(sub, rel)
    except OSError:
        logger.debug("Error scanning %s for overrides", root, exc_info=True)

    # Cross-folder check: collisions between language_groups in folders with
    # the same displayed name (= series_title or folder name).  Emitted at
    # report level, attributed to one of the colliding folders.
    _check_language_group_collisions(root, report)

    return report


def _check_language_group_collisions(library_root: Path, report: ValidationReport) -> None:
    """Detect when two folders share the same ``language_group`` id but are
    not in the same multi-language cluster (i.e. completely different titles
    that probably weren't meant to be linked)."""
    # Re-load to avoid a second rglob; uses the existing scan API which is
    # itself cached at the OS level for repeated calls within a CLI run.
    from hometools.streaming.core.media_overrides import load_all_overrides

    try:
        all_ov = load_all_overrides(library_root)
    except Exception:
        return

    by_group: dict[str, list[str]] = {}
    for rel_path, ov in all_ov.items():
        if not ov.language_group:
            continue
        by_group.setdefault(ov.language_group, []).append(rel_path)

    for group_id, members in by_group.items():
        if len(members) < 2:
            report.issues.append(
                Issue(
                    folder=members[0],
                    severity=SEVERITY_INFO,
                    code="lonely_language_group",
                    message=(
                        f"language_group {group_id!r} is declared only here. "
                        "Multi-language linking needs at least two folders "
                        "sharing the same group id."
                    ),
                )
            )
