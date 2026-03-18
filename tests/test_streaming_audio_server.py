"""Tests for HTML rendering and path safety in the audio streaming server."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hometools.streaming.audio.server import create_app, render_audio_index_html, resolve_audio_path
from hometools.streaming.core.models import MediaItem
from hometools.streaming.core.thumbnailer import get_thumbnail_path


def test_render_audio_index_html_contains_filter_controls(tmp_path):
    tracks = [
        MediaItem(
            relative_path="Artist/Song.mp3",
            title="Song",
            artist="Artist",
            stream_url="/audio/stream?path=Artist%2FSong.mp3",
            media_type="audio",
        )
    ]

    html = render_audio_index_html(tracks)

    assert 'id="search-input"' in html
    assert 'id="sort-field"' in html
    assert "<audio" in html


def test_resolve_audio_path_rejects_directory_escape(tmp_path):
    safe_file = tmp_path / "ok.mp3"
    safe_file.write_text("audio")

    with pytest.raises(ValueError, match="escapes"):
        resolve_audio_path(tmp_path, "..%2Foutside.mp3")


def test_resolve_audio_path_rejects_non_audio_file(tmp_path):
    text_file = tmp_path / "note.txt"
    text_file.write_text("not audio")

    with pytest.raises(ValueError, match="Unsupported"):
        resolve_audio_path(tmp_path, "note.txt")


def test_audio_metadata_endpoint_falls_back_when_metadata_reader_breaks(tmp_path):
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"")

    client = TestClient(create_app(tmp_path))

    with patch(
        "hometools.audio.metadata.audiofile_assume_artist_title",
        side_effect=UnicodeDecodeError("cp1252", b"\x81", 0, 1, "boom"),
    ):
        response = client.get("/api/audio/metadata", params={"path": "Artist - Song.mp3"})

    assert response.status_code == 200
    assert response.json() == {"title": "Song", "artist": "Artist", "rating": 0.0}


def test_audio_metadata_endpoint_returns_embedded_values_and_rating(tmp_path):
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"")

    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.audio.metadata.audiofile_assume_artist_title", return_value=("Meta Artist", "Meta Title")),
        patch("hometools.audio.metadata.get_popm_rating", return_value=255),
    ):
        response = client.get("/api/audio/metadata", params={"path": "Artist - Song.mp3"})

    assert response.status_code == 200
    assert response.json() == {"title": "Meta Title", "artist": "Meta Artist", "rating": 5.0}


def test_audio_metadata_endpoint_returns_404_for_missing_file(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/audio/metadata", params={"path": "Missing - Song.mp3"})

    assert response.status_code == 404
    assert "Media file not found" in response.json()["detail"]


def test_audio_metadata_endpoint_returns_404_for_path_traversal(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/api/audio/metadata", params={"path": "../outside.mp3"})

    assert response.status_code == 404
    assert "escapes" in response.json()["detail"]


def test_audio_stream_returns_404_for_missing_file(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/audio/stream", params={"path": "Missing - Song.mp3"})

    assert response.status_code == 404
    assert "Media file not found" in response.json()["detail"]


def test_audio_stream_returns_400_for_non_audio_file(tmp_path):
    text_file = tmp_path / "note.txt"
    text_file.write_text("not audio")

    client = TestClient(create_app(tmp_path))

    response = client.get("/audio/stream", params={"path": "note.txt"})

    assert response.status_code == 400
    assert "Unsupported suffix" in response.json()["detail"]


def test_audio_home_renders_error_page_when_library_unavailable(tmp_path):
    client = TestClient(create_app(tmp_path))

    with patch("hometools.streaming.audio.server.check_library_accessible", return_value=(False, "NAS offline")):
        response = client.get("/")

    assert response.status_code == 200
    assert "NAS offline" in response.text
    assert "Server läuft weiter" in response.text


def test_audio_home_renders_shell_without_building_index(tmp_path):
    client = TestClient(create_app(tmp_path))

    with patch("hometools.streaming.audio.server.build_audio_index", side_effect=AssertionError("must not run during shell render")):
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="initial-data"' in response.text
    assert "Loading library" in response.text


def test_audio_tracks_returns_loading_state_while_index_builds(tmp_path):
    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.streaming.audio.server.check_library_accessible", return_value=(True, "ok")),
        patch("hometools.streaming.audio.server._audio_index_cache.ensure_background_refresh", return_value=True),
        patch("hometools.streaming.audio.server._audio_index_cache.get_cached", return_value=[]),
        patch("hometools.streaming.audio.server._audio_index_cache.is_building", return_value=True),
    ):
        response = client.get("/api/audio/tracks")

    assert response.status_code == 200
    assert response.json()["loading"] is True
    assert response.json()["items"] == []


def test_audio_status_endpoint_returns_cache_diagnostics(tmp_path):
    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.streaming.audio.server._audio_index_cache.status", return_value={"building": True, "cached_count": 0}),
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
        response = client.get("/api/audio/status")

    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert "cache" in data
    assert "issues" in data
    assert "todos" in data
    assert data["cache"]["building"] is True


def test_audio_home_safe_mode_omits_service_worker_registration(tmp_path):
    client = TestClient(create_app(tmp_path, safe_mode=True))

    response = client.get("/")

    assert response.status_code == 200
    assert "serviceWorker.register('/sw.js')" not in response.text
    assert 'id="offline-btn"' not in response.text
    assert "Safe Mode" in response.text


def test_audio_tracks_safe_mode_reports_flag(tmp_path):
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"")
    client = TestClient(create_app(tmp_path, safe_mode=True))

    response = client.get("/api/audio/tracks")

    assert response.status_code == 200
    assert response.json()["safe_mode"] is True


def test_thumb_returns_404_when_thumbnail_is_missing(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/thumb", params={"path": "Artist/Song.mp3"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Thumbnail not found"}


def test_thumb_serves_cached_thumbnail_from_shadow_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    thumb_path = get_thumbnail_path(cache_dir, "audio", "Artist/Song.mp3")
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.write_bytes(b"fake-jpeg")

    with patch.dict(os.environ, {"HOMETOOLS_CACHE_DIR": str(cache_dir)}):
        client = TestClient(create_app(tmp_path))
        response = client.get("/thumb", params={"path": "Artist/Song.mp3"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content == b"fake-jpeg"
