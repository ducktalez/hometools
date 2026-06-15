"""Tests for the "Continue Watching" feed (core helper + video endpoint).

Built for the native TV client (10-foot UI) but generic for any consumer.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from hometools.streaming.core.models import MediaItem
from hometools.streaming.core.progress import get_continue_watching, save_progress
from hometools.streaming.video.server import create_app


class TestGetContinueWatching:
    def test_filters_early_finished_and_keeps_unknown_duration(self, tmp_path):
        save_progress(tmp_path, "A.mkv", 120.0, 1200.0)  # in progress -> keep
        save_progress(tmp_path, "B.mkv", 5.0, 1200.0)  # too early -> drop
        save_progress(tmp_path, "C.mkv", 1190.0, 1200.0)  # finished -> drop
        save_progress(tmp_path, "D.mkv", 60.0, 0.0)  # unknown duration -> keep

        result = get_continue_watching(tmp_path, min_position_seconds=30.0, finished_fraction=0.95)
        paths = [e["relative_path"] for e in result]

        assert "A.mkv" in paths
        assert "D.mkv" in paths
        assert "B.mkv" not in paths
        assert "C.mkv" not in paths

    def test_respects_limit(self, tmp_path):
        for i in range(10):
            save_progress(tmp_path, f"file{i}.mkv", 100.0, 1000.0)
        result = get_continue_watching(tmp_path, limit=3)
        assert len(result) == 3

    def test_empty_cache_returns_empty(self, tmp_path):
        assert get_continue_watching(tmp_path) == []


class TestVideoContinueEndpoint:
    def test_joins_progress_with_catalog(self, tmp_path):
        save_progress(tmp_path, "Show/ep1.mkv", 100.0, 1000.0)
        item = MediaItem(
            relative_path="Show/ep1.mkv",
            title="Ep 1",
            artist="Show",
            stream_url="/video/stream?path=Show%2Fep1.mkv",
            media_type="video",
        )
        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

        with patch(
            "hometools.streaming.video.server._video_index_cache.get_cached",
            return_value=[item],
        ):
            response = client.get("/api/video/continue")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        entry = data["items"][0]
        assert entry["relative_path"] == "Show/ep1.mkv"
        assert entry["title"] == "Ep 1"
        assert entry["position_seconds"] == 100.0
        assert entry["resume_duration"] == 1000.0
        assert "last_played" in entry

    def test_skips_progress_for_files_not_in_catalog(self, tmp_path):
        save_progress(tmp_path, "Gone/old.mkv", 100.0, 1000.0)
        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

        with patch(
            "hometools.streaming.video.server._video_index_cache.get_cached",
            return_value=[],
        ):
            response = client.get("/api/video/continue")

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_empty_progress_returns_empty(self, tmp_path):
        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        response = client.get("/api/video/continue")
        assert response.status_code == 200
        assert response.json()["items"] == []
