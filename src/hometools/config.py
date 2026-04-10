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

    This directory is fully disposable — ``make clean`` deletes everything
    in it.  Permanent data (audit log) lives in :func:`get_audit_dir`.
    """
    _repo_root = Path(__file__).resolve().parent.parent.parent
    return _get_path_from_env(
        "HOMETOOLS_CACHE_DIR",
        _repo_root / ".hometools-cache",
    )


# ---------------------------------------------------------------------------
# Audit log directory
# ---------------------------------------------------------------------------


def get_audit_dir() -> Path:
    """Return the directory for the append-only audit log (``audit.jsonl``).

    The audit log is **not** re-generatable cache data — it records
    permanent user actions (rating writes, tag edits, renames).
    It therefore lives outside the shadow cache so ``make clean`` cannot
    accidentally destroy it.

    Set ``HOMETOOLS_AUDIT_DIR`` to override.

    Default: ``.hometools-audit/`` in the repository root (next to ``src/``).
    """
    _repo_root = Path(__file__).resolve().parent.parent.parent
    return _get_path_from_env(
        "HOMETOOLS_AUDIT_DIR",
        _repo_root / ".hometools-audit",
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
# Playlist behaviour
# ---------------------------------------------------------------------------


def get_playlist_insert_position() -> str:
    """Return where new items are inserted into a playlist: ``'bottom'`` or ``'top'``.

    ``bottom`` (default, consistent with Spotify) — appends new items at the end.
    ``top`` — inserts new items at index 0.
    Set ``HOMETOOLS_PLAYLIST_INSERT_POSITION`` to override.
    """
    raw = os.environ.get("HOMETOOLS_PLAYLIST_INSERT_POSITION", "bottom").strip().lower()
    if raw not in ("top", "bottom"):
        return "bottom"
    return raw


def get_playlist_sync_interval() -> int:
    """Return the playlist sync polling interval in seconds.

    Clients poll ``GET /api/<media>/playlists/version`` at this interval
    to detect cross-device changes.  Minimum 5 seconds to prevent flooding.
    Set ``HOMETOOLS_PLAYLIST_SYNC_INTERVAL`` to override.  Default: 30.
    """
    val = _get_int_from_env("HOMETOOLS_PLAYLIST_SYNC_INTERVAL", 30)
    return max(5, val)


# ---------------------------------------------------------------------------
# Rating threshold
# ---------------------------------------------------------------------------


def get_min_rating() -> int:
    """Return the minimum star rating for tracks to be visible.

    Tracks that **have been rated** but whose rating is **at or below**
    this threshold are hidden from the UI.  Unrated tracks (``rating == 0``)
    are always shown regardless of this setting.

    Value range: 0–5.  Default ``0`` means no tracks are hidden.
    Set ``HOMETOOLS_MIN_RATING`` to override (e.g. ``2`` hides 1★ and 2★ tracks).
    """
    val = _get_int_from_env("HOMETOOLS_MIN_RATING", 0)
    return max(0, min(val, 5))


def get_debug_filter() -> bool:
    """Return whether filtered items should be shown greyed-out with reason.

    When ``True``, items that are hidden by ``MIN_RATING`` or Quick-Filters
    are **not** removed from the track list.  Instead, they appear dimmed
    with a short text explaining why they would normally be hidden.

    Useful for debugging rating issues and understanding filter behaviour.
    Set ``HOMETOOLS_DEBUG_FILTER=true`` in ``.env`` to enable.
    """
    return _get_bool_from_env("HOMETOOLS_DEBUG_FILTER", False)


# ---------------------------------------------------------------------------
# Recently played
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Crossfade
# ---------------------------------------------------------------------------


def get_crossfade_duration() -> int:
    """Return the crossfade duration in seconds.

    ``0`` means crossfade is disabled (hard cut between tracks).
    Typical values: 3–5 seconds.
    Set ``HOMETOOLS_CROSSFADE_DURATION`` to override.  Default: 0.
    """
    val = _get_int_from_env("HOMETOOLS_CROSSFADE_DURATION", 0)
    return max(0, min(val, 12))


# ---------------------------------------------------------------------------
# Channel (TV) server
# ---------------------------------------------------------------------------


def get_channel_port() -> int:
    """Return the port for the channel (TV) streaming server.

    Default: one above the video port (8012).
    Set ``HOMETOOLS_CHANNEL_PORT`` to override.
    """
    return _get_int_from_env("HOMETOOLS_CHANNEL_PORT", get_video_port() + 1)


def get_channel_schedule_file() -> Path:
    """Return the path to the channel schedule YAML file.

    Default: ``channel_schedule.yaml`` in the repository root.
    """
    _repo_root = Path(__file__).resolve().parent.parent.parent
    return _get_path_from_env("HOMETOOLS_CHANNEL_SCHEDULE", _repo_root / "channel_schedule.yaml")


def get_channel_filler_dir() -> Path:
    """Return the directory containing filler clips / music for gaps.

    Default: ``filler/`` inside the video library directory.
    """
    return _get_path_from_env("HOMETOOLS_CHANNEL_FILLER_DIR", get_video_library_dir() / "filler")


def get_channel_hls_dir() -> Path:
    """Return the directory for HLS segments generated by the channel mixer.

    Default: ``.hometools-cache/channel/hls/`` in the repository root.
    """
    return get_cache_dir() / "channel" / "hls"


def get_channel_tmp_dir() -> Path:
    """Return the directory for pre-transcoded temporary video files.

    Videos are converted to a uniform H.264/AAC MP4 format before being
    fed into the concat-demuxer based HLS pipeline.  Temporary files are
    deleted after playback.

    Default: ``.hometools-cache/channel/tmp/`` in the repository root.
    """
    return get_cache_dir() / "channel" / "tmp"


def get_channel_state_dir() -> Path:
    """Return the directory for persistent channel state (episode tracking).

    Default: ``.hometools-cache/channel/`` in the repository root.
    """
    return get_cache_dir() / "channel"


def get_channel_encoder() -> str:
    """Return the video encoder to use for the channel stream.

    ``libx264`` (default, software), ``h264_nvenc`` (NVIDIA), ``h264_qsv`` (Intel).
    Set ``HOMETOOLS_CHANNEL_ENCODER`` to override.
    """
    raw = os.environ.get("HOMETOOLS_CHANNEL_ENCODER", "libx264").strip().lower()
    return raw if raw else "libx264"


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
