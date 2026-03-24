"""Configuration management for hometools.

Loads settings from environment variables / .env file.
Never commit secrets to source control – use .env instead.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set externally


def _get_path_from_env(name: str, default: Path) -> Path:
    """Return a filesystem path from the environment or a default value."""
    raw = os.environ.get(name)
    return Path(raw).expanduser() if raw else default.expanduser()


def _get_int_from_env(name: str, default: int) -> int:
    """Return an integer environment variable, raising a clear error on invalid input."""
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {raw!r}") from exc


def _get_bool_from_env(name: str, default: bool = False) -> bool:
    """Return a boolean environment variable with a permissive parser."""
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_tmdb_api_key() -> str:
    """Return the TMDB API key from the environment."""
    key = os.environ.get("TMDB_API_KEY", "")
    if not key:
        raise RuntimeError(
            "TMDB_API_KEY is not set. Create a .env file with TMDB_API_KEY=your_key or export it as an environment variable."
        )
    return key


def get_delete_dir() -> Path:
    """Return the soft-delete directory from the environment, with a sensible default."""
    return Path(os.environ.get("HOMETOOLS_DELETE_DIR", Path.home() / "Music" / "DELETE_ME"))


# ---------------------------------------------------------------------------
# Audio streaming
# ---------------------------------------------------------------------------


def get_audio_library_dir() -> Path:
    """Return the local audio library used by the streaming prototype."""
    return _get_path_from_env(
        "HOMETOOLS_AUDIO_LIBRARY_DIR",
        Path.home() / "Music/hometools/audio-library",
    )


def get_audio_nas_dir() -> Path:
    """Return the mounted NAS source directory for manual audio syncs."""
    return _get_path_from_env(
        "HOMETOOLS_AUDIO_NAS_DIR",
        Path.home() / "Music" / "hometools" / "audio-nas",
    )


# ---------------------------------------------------------------------------
# Video streaming
# ---------------------------------------------------------------------------


def get_video_library_dir() -> Path:
    """Return the local video library used by the streaming prototype."""
    return _get_path_from_env(
        "HOMETOOLS_VIDEO_LIBRARY_DIR",
        Path.home() / "Videos/clips",
    )


def get_video_nas_dir() -> Path:
    """Return the mounted NAS source directory for manual video syncs."""
    return _get_path_from_env(
        "HOMETOOLS_VIDEO_NAS_DIR",
        Path.home() / "Videos/clips",
    )


# ---------------------------------------------------------------------------
# Streaming bind
# ---------------------------------------------------------------------------


def get_stream_host() -> str:
    """Return the bind host for the local streaming web server."""
    return os.environ.get("HOMETOOLS_STREAM_HOST", "127.0.0.1")


def get_stream_port() -> int:
    """Return the shared default port (used by single-server commands)."""
    return _get_int_from_env("HOMETOOLS_STREAM_PORT", 8010)


def get_audio_port() -> int:
    """Return the port for the audio streaming server."""
    return _get_int_from_env("HOMETOOLS_AUDIO_PORT", get_stream_port())


def get_video_port() -> int:
    """Return the port for the video streaming server."""
    return _get_int_from_env("HOMETOOLS_VIDEO_PORT", get_stream_port() + 1)


def get_stream_bind() -> tuple[str, int]:
    """Return host and port tuple for the local streaming web server."""
    return get_stream_host(), get_stream_port()


def get_stream_index_cache_ttl() -> int:
    """Return the TTL for cached streaming indexes in seconds.

    A longer TTL avoids expensive full-library rescans on frequent reloads,
    while background refresh keeps stale snapshots up to date.
    """
    return _get_int_from_env("HOMETOOLS_STREAM_INDEX_CACHE_TTL", 900)


def get_stream_safe_mode() -> bool:
    """Return whether streaming servers should run in minimal no-cache safe mode."""
    return _get_bool_from_env("HOMETOOLS_STREAM_SAFE_MODE", False)


# ---------------------------------------------------------------------------
# Shadow cache directory
# ---------------------------------------------------------------------------


def get_cache_dir() -> Path:
    """Return the shadow cache directory for thumbnails and metadata.

    Mirrors the library directory structures but stores only generated
    artefacts (thumbnails, metadata caches).  Original media files are
    never touched.  Set ``HOMETOOLS_CACHE_DIR`` to override.

    Default: ``.hometools-cache/`` in the repository root (next to ``src/``).

    .. note:: **Audit logs** (``audit/audit.jsonl``) currently live inside
        this cache directory for historical reasons.  This is intentionally
        preserved by ``make clean`` (which deletes everything *except*
        ``audit/``).  Long-term, the audit log should move to its own
        directory (e.g. ``HOMETOOLS_AUDIT_DIR``) so it is clearly separated
        from re-generatable cache data and is never accidentally deleted.
    """
    _repo_root = Path(__file__).resolve().parent.parent.parent
    return _get_path_from_env(
        "HOMETOOLS_CACHE_DIR",
        _repo_root / ".hometools-cache",
    )


# ---------------------------------------------------------------------------
# Player bar style
# ---------------------------------------------------------------------------


def get_player_bar_style() -> str:
    """Return the player bar style: ``'classic'`` or ``'waveform'``.

    ``classic``  — simple single-row range input (reliable, lightweight).
    ``waveform`` — two-row layout with audio waveform / video thumbnails.
    """
    raw = os.environ.get("HOMETOOLS_PLAYER_BAR_STYLE", "classic").strip().lower()
    if raw not in ("classic", "waveform"):
        return "classic"
    return raw


# ---------------------------------------------------------------------------
# Video PWA display mode
# ---------------------------------------------------------------------------


def get_video_pwa_display_mode() -> str:
    """Return the video PWA display mode: ``'standalone'`` or ``'minimal-ui'``."""
    raw = os.environ.get("HOMETOOLS_VIDEO_PWA_DISPLAY", "minimal-ui").strip().lower()
    if raw not in ("standalone", "minimal-ui"):
        return "minimal-ui"
    return raw


# ---------------------------------------------------------------------------
# Audiobook detection
# ---------------------------------------------------------------------------


def get_audiobook_dirs() -> list[str]:
    """Return folder-name prefixes that identify audiobook directories.

    Matching is case-insensitive prefix match on the folder name.
    Configure via ``HOMETOOLS_AUDIOBOOK_DIRS`` as a comma-separated list.

    Default prefixes: Hörbuch, Hörspiel, Audiobook, Spoken Word
    (stored as Unicode escapes to avoid Windows source-encoding issues)
    """
    # \u00f6 = ö, \u00fc = ü, \u00e4 = ä — ASCII-safe literals for Windows compatibility
    # "Hörbücher" (plural, ü≠u) must be listed separately from "Hörbuch"
    default = "H\u00f6rbuch,H\u00f6rb\u00fccher,H\u00f6rspiel,Audiobook,Spoken Word"
    raw = os.environ.get("HOMETOOLS_AUDIOBOOK_DIRS", default)
    return [s.strip() for s in raw.split(",") if s.strip()]


def is_audiobook_folder(folder_name: str, audiobook_dirs: list[str] | None = None) -> bool:
    """Return *True* if *folder_name* matches any configured audiobook prefix."""
    if audiobook_dirs is None:
        audiobook_dirs = get_audiobook_dirs()
    name_lower = folder_name.lower()
    return any(name_lower.startswith(d.lower()) for d in audiobook_dirs)


# ---------------------------------------------------------------------------
# Recently played
# ---------------------------------------------------------------------------


def get_recent_video_limit() -> int:
    """Return max number of recently played video items shown on the start screen.

    Default 3 — only the most recently seen episode per series is kept,
    so this is an episode count, not a series count.
    Set ``HOMETOOLS_RECENT_VIDEO_LIMIT`` to override.
    """
    return _get_int_from_env("HOMETOOLS_RECENT_VIDEO_LIMIT", 3)


def get_recent_max_age_days() -> int:
    """Return max age in days for recently played video items.

    Items older than this threshold are excluded from the start-screen
    suggestions.  Set ``HOMETOOLS_RECENT_MAX_AGE_DAYS`` to override.
    """
    return _get_int_from_env("HOMETOOLS_RECENT_MAX_AGE_DAYS", 14)


def get_recent_max_per_series() -> int:
    """Return max number of recently played episodes per series shown.

    Default 1 — only the most-recently-seen episode of each series is kept.
    Set ``HOMETOOLS_RECENT_MAX_PER_SERIES`` to override.
    """
    return _get_int_from_env("HOMETOOLS_RECENT_MAX_PER_SERIES", 1)
