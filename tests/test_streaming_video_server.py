"""Tests for HTML rendering and shell loading in the video streaming server."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from hometools.streaming.video.server import create_app


def test_video_home_renders_shell_without_building_index(tmp_path):
    client = TestClient(create_app(tmp_path))

    with patch("hometools.streaming.video.server.build_video_index", side_effect=AssertionError("must not run during shell render")):
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="initial-data"' in response.text
    assert "Loading library" in response.text


def test_video_items_returns_loading_state_while_index_builds(tmp_path):
    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.streaming.video.server.check_library_accessible", return_value=(True, "ok")),
        patch("hometools.streaming.video.server._video_index_cache.ensure_background_refresh", return_value=True),
        patch("hometools.streaming.video.server._video_index_cache.get_cached", return_value=[]),
        patch("hometools.streaming.video.server._video_index_cache.is_building", return_value=True),
    ):
        response = client.get("/api/video/items")

    assert response.status_code == 200
    assert response.json()["loading"] is True
    assert response.json()["items"] == []


def test_video_status_endpoint_returns_cache_diagnostics(tmp_path):
    client = TestClient(create_app(tmp_path))

    with patch("hometools.streaming.video.server._video_index_cache.status", return_value={"building": True, "cached_count": 0}):
        response = client.get("/api/video/status")

    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert "cache" in data
    assert data["cache"]["building"] is True
