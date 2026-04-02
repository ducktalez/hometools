"""Tests for environment-backed configuration helpers."""

from pathlib import Path

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_playlist_insert_position,
    get_playlist_sync_interval,
    get_recent_max_age_days,
    get_recent_max_per_series,
    get_recent_video_limit,
    get_stream_bind,
    get_stream_index_cache_ttl,
    get_stream_port,
    get_stream_safe_mode,
    get_video_library_dir,
    get_video_nas_dir,
)


def test_audio_library_dir_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_AUDIO_LIBRARY_DIR", "C:/Temp/audio-library")
    assert get_audio_library_dir() == Path("C:/Temp/audio-library")


def test_audio_nas_dir_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_AUDIO_NAS_DIR", "Z:/Music")
    assert get_audio_nas_dir() == Path("Z:/Music")


def test_video_library_dir_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_VIDEO_LIBRARY_DIR", "C:/Temp/video-library")
    assert get_video_library_dir() == Path("C:/Temp/video-library")


def test_video_nas_dir_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_VIDEO_NAS_DIR", "Z:/Video")
    assert get_video_nas_dir() == Path("Z:/Video")


def test_stream_port_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_STREAM_PORT", "9001")
    assert get_stream_port() == 9001


def test_stream_bind_uses_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("HOMETOOLS_STREAM_HOST", raising=False)
    monkeypatch.delenv("HOMETOOLS_STREAM_PORT", raising=False)
    assert get_stream_bind() == ("127.0.0.1", 8010)


def test_stream_index_cache_ttl_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_STREAM_INDEX_CACHE_TTL", "42")
    assert get_stream_index_cache_ttl() == 42


def test_stream_safe_mode_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_STREAM_SAFE_MODE", "true")
    assert get_stream_safe_mode() is True


def test_recent_video_limit_default():
    assert get_recent_video_limit() == 3


def test_recent_video_limit_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_RECENT_VIDEO_LIMIT", "5")
    assert get_recent_video_limit() == 5


def test_recent_max_age_days_default():
    assert get_recent_max_age_days() == 14


def test_recent_max_age_days_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_RECENT_MAX_AGE_DAYS", "7")
    assert get_recent_max_age_days() == 7


def test_recent_max_per_series_default():
    assert get_recent_max_per_series() == 1


def test_recent_max_per_series_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_RECENT_MAX_PER_SERIES", "2")
    assert get_recent_max_per_series() == 2


# ---------------------------------------------------------------------------
# Playlist behaviour
# ---------------------------------------------------------------------------


def test_playlist_insert_position_default():
    assert get_playlist_insert_position() == "bottom"


def test_playlist_insert_position_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_PLAYLIST_INSERT_POSITION", "top")
    assert get_playlist_insert_position() == "top"


def test_playlist_insert_position_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_PLAYLIST_INSERT_POSITION", "middle")
    assert get_playlist_insert_position() == "bottom"


def test_playlist_sync_interval_default():
    assert get_playlist_sync_interval() == 30


def test_playlist_sync_interval_from_env(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_PLAYLIST_SYNC_INTERVAL", "60")
    assert get_playlist_sync_interval() == 60


def test_playlist_sync_interval_minimum_clamped(monkeypatch):
    """Values below 5 are clamped to 5 to prevent server flooding."""
    monkeypatch.setenv("HOMETOOLS_PLAYLIST_SYNC_INTERVAL", "1")
    assert get_playlist_sync_interval() == 5
