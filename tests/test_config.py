"""Tests for environment-backed configuration helpers."""

from pathlib import Path

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_stream_bind,
    get_stream_port,
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
    assert get_stream_bind() == ("127.0.0.1", 8000)
