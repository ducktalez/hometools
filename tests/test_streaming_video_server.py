"""Tests for HTML rendering and shell loading in the video streaming server."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from hometools.streaming.core.issue_registry import record_issue
from hometools.streaming.video.server import create_app


def test_video_home_renders_shell_without_building_index(tmp_path):
    client = TestClient(create_app(tmp_path))

    with patch("hometools.streaming.video.server.build_video_index", side_effect=AssertionError("must not run during shell render")):
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="initial-data"' in response.text
    assert "Loading library" in response.text


def test_video_items_returns_refreshing_state_with_quick_scan_while_index_builds(tmp_path):
    # Create a test video file so quick scan finds it
    sub = tmp_path / "TestFolder"
    sub.mkdir()
    (sub / "clip.mp4").write_bytes(b"")

    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.streaming.video.server._video_index_cache.ensure_background_refresh", return_value=True),
        patch("hometools.streaming.video.server._video_index_cache.get_cached", return_value=[]),
        patch("hometools.streaming.video.server._video_index_cache.is_building", return_value=True),
        patch("hometools.streaming.video.server.check_library_accessible", return_value=(True, "ok")),
    ):
        response = client.get("/api/video/items")

    assert response.status_code == 200
    data = response.json()
    assert data["refreshing"] is True
    assert len(data["items"]) >= 1
    assert "loading" not in data


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
                    "items": [{"todo_key": "todo::1", "state": "active", "message": "test"}],
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


def test_video_todo_state_endpoint_snoozes_and_returns_updated_todos(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    client = TestClient(create_app(tmp_path))

    todo_key = client.get("/api/video/status").json()["todos"]["items"][0]["todo_key"]
    response = client.post(
        "/api/video/todos/state",
        json={"todo_key": todo_key, "action": "snooze", "seconds": 120, "reason": "later"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["result"]["state"] == "snoozed"
    assert data["todos"]["snoozed_count"] == 1


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


# ---------------------------------------------------------------------------
# Playback progress endpoints
# ---------------------------------------------------------------------------


def test_video_progress_save_and_load(tmp_path):
    """POST progress and GET it back."""
    client = TestClient(create_app(tmp_path))

    resp = client.post(
        "/api/video/progress",
        json={"relative_path": "Folder/Movie.mp4", "position_seconds": 123.4, "duration": 5400.0},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.get("/api/video/progress", params={"path": "Folder/Movie.mp4"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["position_seconds"] == 123.4


def test_video_progress_empty_path_rejected(tmp_path):
    """POST with empty relative_path returns 400."""
    client = TestClient(create_app(tmp_path))

    resp = client.post(
        "/api/video/progress",
        json={"relative_path": "", "position_seconds": 10.0},
    )
    assert resp.status_code == 400


def test_video_progress_not_found(tmp_path):
    """GET progress for unknown track returns empty items."""
    client = TestClient(create_app(tmp_path))

    resp = client.get("/api/video/progress", params={"path": "unknown.mp4"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# Sprite sheet endpoints
# ---------------------------------------------------------------------------


def test_video_sprites_returns_404_when_not_generated(tmp_path):
    """GET /api/video/sprites returns 404 when sprite sheet is not generated yet."""
    client = TestClient(create_app(tmp_path))
    resp = client.get("/api/video/sprites", params={"path": "nonexistent.mp4"})
    assert resp.status_code == 404


def test_video_sprites_returns_metadata_when_available(tmp_path, monkeypatch):
    """GET /api/video/sprites returns metadata JSON when sprite is generated."""
    import json

    from hometools.streaming.core.thumbnailer import get_sprite_meta_path

    cache = tmp_path / "cache"
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(cache))

    meta_path = get_sprite_meta_path(cache, "Series/ep01.mp4")
    meta_path.parent.mkdir(parents=True)
    meta_data = {"cols": 10, "rows": 4, "frame_w": 160, "frame_h": 90, "interval": 1.5, "count": 40, "duration": 60.0}
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    client = TestClient(create_app(tmp_path))
    resp = client.get("/api/video/sprites", params={"path": "Series/ep01.mp4"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cols"] == 10
    assert data["rows"] == 4
    assert data["ok"] is True


def test_video_thumb_sprite_returns_404_when_missing(tmp_path):
    """GET /thumb?size=sprite returns 404 when sprite image not generated."""
    client = TestClient(create_app(tmp_path))
    resp = client.get("/thumb", params={"path": "nonexistent.mp4", "size": "sprite"})
    assert resp.status_code == 404


def test_video_thumb_sprite_serves_image(tmp_path, monkeypatch):
    """GET /thumb?size=sprite serves the sprite sheet JPEG."""
    from hometools.streaming.core.thumbnailer import get_sprite_path

    cache = tmp_path / "cache"
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(cache))

    sprite_path = get_sprite_path(cache, "clip.mp4")
    sprite_path.parent.mkdir(parents=True)
    sprite_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake JPEG

    client = TestClient(create_app(tmp_path))
    resp = client.get("/thumb", params={"path": "clip.mp4", "size": "sprite"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
