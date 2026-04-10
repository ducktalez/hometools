"""Tests for HTML rendering and path safety in the audio streaming server."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hometools.streaming.audio.server import create_app, render_audio_index_html, resolve_audio_path
from hometools.streaming.core.issue_registry import record_issue
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


def test_audio_tracks_returns_refreshing_state_with_quick_scan_while_index_builds(tmp_path):
    # Create a test audio file so quick scan finds it
    sub = tmp_path / "TestArtist"
    sub.mkdir()
    (sub / "song.mp3").write_bytes(b"")

    client = TestClient(create_app(tmp_path))

    with (
        patch("hometools.streaming.audio.server._audio_index_cache.ensure_background_refresh", return_value=True),
        patch("hometools.streaming.audio.server._audio_index_cache.get_cached", return_value=[]),
        patch("hometools.streaming.audio.server._audio_index_cache.is_building", return_value=True),
        patch("hometools.streaming.audio.server.check_library_accessible", return_value=(True, "ok")),
    ):
        response = client.get("/api/audio/tracks")

    assert response.status_code == 200
    data = response.json()
    assert data["refreshing"] is True
    assert len(data["items"]) >= 1
    assert "loading" not in data


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
                    "items": [{"todo_key": "todo::1", "state": "active", "message": "test"}],
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


def test_audio_todo_state_endpoint_acknowledges_and_returns_updated_todos(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    client = TestClient(create_app(tmp_path))

    todo_key = client.get("/api/audio/status").json()["todos"]["items"][0]["todo_key"]
    response = client.post(
        "/api/audio/todos/state",
        json={"todo_key": todo_key, "action": "acknowledge", "reason": "known"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["result"]["state"] == "acknowledged"
    assert data["todos"]["acknowledged_count"] == 1


def test_audio_home_safe_mode_omits_service_worker_registration(tmp_path):
    client = TestClient(create_app(tmp_path, safe_mode=True))

    response = client.get("/")

    assert response.status_code == 200
    assert "serviceWorker.register('/sw.js')" not in response.text
    assert 'id="downloaded-pill"' in response.text
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


# ---------------------------------------------------------------------------
# Playback progress endpoints
# ---------------------------------------------------------------------------


def test_audio_progress_save_and_load(tmp_path):
    """POST progress and GET it back."""
    client = TestClient(create_app(tmp_path))

    resp = client.post(
        "/api/audio/progress",
        json={"relative_path": "Artist/Song.mp3", "position_seconds": 42.5, "duration": 180.0},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.get("/api/audio/progress", params={"path": "Artist/Song.mp3"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["position_seconds"] == 42.5


def test_audio_progress_empty_path_rejected(tmp_path):
    """POST with empty relative_path returns 400."""
    client = TestClient(create_app(tmp_path))

    resp = client.post(
        "/api/audio/progress",
        json={"relative_path": "", "position_seconds": 10.0},
    )
    assert resp.status_code == 400


def test_audio_progress_not_found(tmp_path):
    """GET progress for unknown track returns empty items."""
    client = TestClient(create_app(tmp_path))

    resp = client.get("/api/audio/progress", params={"path": "unknown.mp3"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# metadata edit endpoint
# ---------------------------------------------------------------------------


def test_metadata_edit_missing_path_returns_400(tmp_path):
    """POST /api/audio/metadata/edit without path → 400."""
    client = TestClient(create_app(tmp_path))
    resp = client.post("/api/audio/metadata/edit", json={"title": "T"})
    assert resp.status_code == 400


def test_metadata_edit_nonexistent_file_returns_404(tmp_path):
    """POST /api/audio/metadata/edit for a missing file → 404."""
    client = TestClient(create_app(tmp_path))
    resp = client.post("/api/audio/metadata/edit", json={"path": "ghost.mp3", "title": "T"})
    assert resp.status_code == 404


def test_metadata_edit_writes_tags(tmp_path):
    """POST /api/audio/metadata/edit calls write_track_tags and returns ok=True."""
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 32)

    from unittest.mock import patch

    with (
        patch("hometools.audio.metadata.write_track_tags", return_value=True) as mock_write,
        patch("hometools.audio.metadata.audiofile_assume_artist_title", return_value=("Artist", "Song")),
    ):
        client = TestClient(create_app(tmp_path))
        resp = client.post(
            "/api/audio/metadata/edit",
            json={"path": "Artist - Song.mp3", "title": "New Title", "artist": "New Artist"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    mock_write.assert_called_once()


def test_metadata_edit_render_includes_edit_button(tmp_path):
    """The rendered audio page must contain the edit modal markup."""
    from hometools.streaming.audio.server import render_audio_index_html

    html = render_audio_index_html([])
    assert "edit-modal-backdrop" in html
    assert "edit-modal-title-input" in html
    assert "METADATA_EDIT_ENABLED" in html


def test_audio_recent_always_returns_empty(tmp_path):
    """Audio recent endpoint always returns empty — no 'recently played' section for audio.
    Audiobooks resume via loadAndSeekProgress on every playItem call instead.
    """
    from fastapi.testclient import TestClient

    client = TestClient(create_app(tmp_path))
    resp = client.get("/api/audio/recent")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# Lazy per-item rating refresh endpoint
# ---------------------------------------------------------------------------


def test_refresh_ratings_endpoint_returns_updated_ratings(tmp_path):
    """POST /api/audio/refresh-ratings re-reads POPM from files."""
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 32)

    from unittest.mock import patch

    with (
        patch("hometools.audio.metadata.get_popm_rating", return_value=128),
        patch("hometools.audio.metadata.popm_raw_to_stars", return_value=3.0),
    ):
        client = TestClient(create_app(tmp_path))
        resp = client.post(
            "/api/audio/refresh-ratings",
            json={"paths": ["Artist - Song.mp3"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ratings"]["Artist - Song.mp3"] == 3.0


def test_refresh_ratings_requires_paths(tmp_path):
    """POST /api/audio/refresh-ratings rejects empty paths."""
    client = TestClient(create_app(tmp_path))
    resp = client.post("/api/audio/refresh-ratings", json={"paths": []})
    assert resp.status_code == 400


def test_refresh_ratings_skips_unresolvable(tmp_path):
    """Unresolvable paths are silently skipped, not errors."""
    client = TestClient(create_app(tmp_path))
    resp = client.post(
        "/api/audio/refresh-ratings",
        json={"paths": ["nonexistent/file.mp3"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ratings"] == {}
    assert data["changed"] == 0


def test_refresh_ratings_patches_index_cache(tmp_path):
    """The endpoint must patch the in-memory index cache with new ratings."""
    audio = tmp_path / "Song.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 32)

    from unittest.mock import patch

    with (
        patch("hometools.audio.metadata.get_popm_rating", return_value=255),
        patch("hometools.audio.metadata.popm_raw_to_stars", return_value=5.0),
    ):
        client = TestClient(create_app(tmp_path))
        resp = client.post(
            "/api/audio/refresh-ratings",
            json={"paths": ["Song.mp3"]},
        )

    assert resp.status_code == 200
    assert resp.json()["ratings"]["Song.mp3"] == 5.0


# ---------------------------------------------------------------------------
# Debug filter mode
# ---------------------------------------------------------------------------


def test_debug_filter_js_variable_injected(tmp_path, monkeypatch):
    """When HOMETOOLS_DEBUG_FILTER=true, the rendered page contains DEBUG_FILTER = true."""
    monkeypatch.setenv("HOMETOOLS_DEBUG_FILTER", "true")
    html = render_audio_index_html([])
    assert "DEBUG_FILTER = true" in html


def test_debug_filter_default_is_false(tmp_path, monkeypatch):
    """By default, DEBUG_FILTER should be false."""
    monkeypatch.delenv("HOMETOOLS_DEBUG_FILTER", raising=False)
    html = render_audio_index_html([])
    assert "DEBUG_FILTER = false" in html


def test_debug_filter_css_present(tmp_path, monkeypatch):
    """Debug-filtered CSS class must be present in the rendered page."""
    monkeypatch.setenv("HOMETOOLS_DEBUG_FILTER", "true")
    html = render_audio_index_html([])
    assert ".debug-filtered" in html
    assert ".debug-reason" in html


# ---------------------------------------------------------------------------
# Refresh log
# ---------------------------------------------------------------------------


def test_refresh_ratings_returns_last_refresh_timestamp(tmp_path):
    """POST /api/audio/refresh-ratings includes last_refresh in response."""
    audio = tmp_path / "Song.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 32)

    with (
        patch("hometools.audio.metadata.get_popm_rating", return_value=128),
        patch("hometools.audio.metadata.popm_raw_to_stars", return_value=3.0),
    ):
        client = TestClient(create_app(tmp_path))
        resp = client.post(
            "/api/audio/refresh-ratings",
            json={"paths": ["Song.mp3"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "last_refresh" in data
    assert data["last_refresh"]  # non-empty timestamp
    assert "folder" in data


def test_refresh_log_endpoint_returns_persisted_data(tmp_path):
    """GET /api/audio/refresh-log returns data written by refresh-ratings."""
    audio = tmp_path / "Funsongs" / "Song.mp3"
    audio.parent.mkdir()
    audio.write_bytes(b"ID3" + b"\x00" * 32)

    with (
        patch("hometools.audio.metadata.get_popm_rating", return_value=255),
        patch("hometools.audio.metadata.popm_raw_to_stars", return_value=5.0),
    ):
        client = TestClient(create_app(tmp_path))
        # First refresh to create the log entry
        client.post(
            "/api/audio/refresh-ratings",
            json={"paths": ["Funsongs/Song.mp3"]},
        )
        # Now read the log
        resp = client.get("/api/audio/refresh-log")

    assert resp.status_code == 200
    data = resp.json()
    assert "Funsongs" in data
    assert "last_refresh" in data["Funsongs"]
    assert data["Funsongs"]["total"] == 1


def test_refresh_log_endpoint_returns_empty_when_no_log(tmp_path):
    """GET /api/audio/refresh-log returns {} when no log exists."""
    cache_dir = tmp_path / "clean-cache"
    cache_dir.mkdir()
    client = TestClient(create_app(tmp_path, cache_dir=cache_dir))
    resp = client.get("/api/audio/refresh-log")
    assert resp.status_code == 200
    assert resp.json() == {}


def test_refresh_info_element_present_in_html(tmp_path):
    """The HTML must contain the refresh-info span element."""
    html = render_audio_index_html([])
    assert 'id="refresh-info"' in html
