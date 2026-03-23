"""Tests for streaming maintenance helpers and cache reset/prewarm flows."""

from __future__ import annotations

import json
from pathlib import Path

from hometools.streaming.core.maintenance import prewarm_stream, reset_stream_generated


def _write_failure_registry(cache_dir: Path) -> None:
    payload = {
        "audio::Artist/Song.mp3": {"reason": "x"},
        "video::Movie.mp4": {"reason": "y"},
    }
    (cache_dir / "thumbnail_failures.json").write_text(json.dumps(payload), encoding="utf-8")


def test_reset_stream_generated_hard_removes_audio_cache_and_logs(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    log_dir = cache_dir / "logs"
    audio_dir = cache_dir / "audio"
    indexes_dir = cache_dir / "indexes"
    audio_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)
    indexes_dir.mkdir(parents=True)
    (audio_dir / "Artist.mp3.thumb.jpg").write_bytes(b"thumb")
    (indexes_dir / "audio-index.json").write_text("{}", encoding="utf-8")
    (log_dir / "audio-20260318-010101.log").write_text("log", encoding="utf-8")
    _write_failure_registry(cache_dir)

    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("HOMETOOLS_AUDIO_LIBRARY_DIR", str(tmp_path / "lib-audio"))

    result = reset_stream_generated("audio", hard=True)[0]

    assert result.server == "audio"
    assert result.failure_entries_removed == 1
    assert not audio_dir.exists()
    assert not (indexes_dir / "audio-index.json").exists()
    assert not (log_dir / "audio-20260318-010101.log").exists()
    remaining = json.loads((cache_dir / "thumbnail_failures.json").read_text(encoding="utf-8"))
    assert list(remaining) == ["video::Movie.mp4"]


def test_prewarm_stream_builds_audio_index_snapshot(monkeypatch, tmp_path):
    lib_dir = tmp_path / "lib-audio"
    lib_dir.mkdir()
    (lib_dir / "Artist - Song.mp3").write_bytes(b"")
    cache_dir = tmp_path / "cache"

    monkeypatch.setenv("HOMETOOLS_AUDIO_LIBRARY_DIR", str(lib_dir))
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(cache_dir))

    result = prewarm_stream("audio", mode="missing", scope="index")

    assert result.server == "audio"
    assert result.index_count == 1
    # Snapshot is saved with a library-dir hash in the filename
    index_files = list((cache_dir / "indexes").glob("audio-index*.json"))
    assert index_files, "No audio index snapshot found"


def test_prewarm_stream_full_resets_video_metadata_cache(monkeypatch, tmp_path):
    lib_dir = tmp_path / "lib-video"
    lib_dir.mkdir()
    (lib_dir / "Movie.mp4").write_bytes(b"")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "video_metadata_cache.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("HOMETOOLS_VIDEO_LIBRARY_DIR", str(lib_dir))
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(cache_dir))

    result = prewarm_stream("video", mode="full", scope="index")

    assert result.server == "video"
    assert result.index_count == 1
    # Snapshot is saved with a library-dir hash in the filename
    index_files = list((cache_dir / "indexes").glob("video-index*.json"))
    assert index_files, "No video index snapshot found"
