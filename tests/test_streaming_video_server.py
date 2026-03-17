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
