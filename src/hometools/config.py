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
    """
    return _get_path_from_env(
        "HOMETOOLS_CACHE_DIR",
        Path.home() / "hometools-cache",
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
    """Return the video PWA display mode: ``'standalone'`` or ``'minimal-ui'``.

    ``standalone`` — app-like experience with native controls blocked.
                     Best for: Fullscreen button visible, clean interface.
                     Drawback: Background playback & PiP blocked by iOS.
    ``minimal-ui`` — minimal browser chrome, all APIs available.
                     Best for: Background audio playback, PiP, fullscreen APIs.
                     Drawback: "Add to Home Screen" creates web link, not PWA.

    Set via environment variable ``HOMETOOLS_VIDEO_PWA_DISPLAY`` (default: "minimal-ui").
    """
    raw = os.environ.get("HOMETOOLS_VIDEO_PWA_DISPLAY", "minimal-ui").strip().lower()
    if raw not in ("standalone", "minimal-ui"):
        return "minimal-ui"
    return raw
