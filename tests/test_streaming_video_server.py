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

    with (
        patch("hometools.streaming.video.server._video_index_cache.status", return_value={"building": True, "cached_count": 0}),
        patch(
            "hometools.streaming.core.issue_registry.summarize_issue_and_todos",
            return_value={
                "issues": {
                    "count": 1,
                    "warnings": 1,
                    "errors": 0,
                    "criticals": 0,
                    "items": [],
                    "top_issue": None,
                    "min_severity": "WARNING",
                },
                "todos": {
                    "count": 1,
                    "source_issue_count": 1,
                    "active_count": 1,
                    "acknowledged_count": 0,
                    "snoozed_count": 0,
                    "cooldown_count": 0,
                    "top_todo": None,
                    "min_severity": "WARNING",
                },
            },
        ),
    ):
        response = client.get("/api/video/status")

    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert "cache" in data
    assert "issues" in data
    assert "todos" in data
    assert data["cache"]["building"] is True


def test_video_home_safe_mode_omits_service_worker_registration(tmp_path):
    client = TestClient(create_app(tmp_path, safe_mode=True))

    response = client.get("/")

    assert response.status_code == 200
    assert "serviceWorker.register('/sw.js')" not in response.text
    assert 'id="offline-btn"' not in response.text
    assert "Safe Mode" in response.text


def test_video_items_safe_mode_reports_flag(tmp_path):
    video = tmp_path / "Movie.mp4"
    video.write_bytes(b"")
    client = TestClient(create_app(tmp_path, safe_mode=True))

    response = client.get("/api/video/items")

    assert response.status_code == 200
    assert response.json()["safe_mode"] is True
