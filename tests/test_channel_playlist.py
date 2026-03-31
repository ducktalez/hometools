"""Tests for the playlist-based channel (TV) server."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture()
def channel_library(tmp_path):
    """Create a minimal video library with series folders for channel testing."""
    # Scheduled series
    bb = tmp_path / "Breaking Bad"
    bb.mkdir()
    (bb / "S01E01 Pilot.mp4").write_bytes(b"\x00" * 64)
    (bb / "S01E02 Cat.mp4").write_bytes(b"\x00" * 64)

    simpsons = tmp_path / "Simpsons"
    simpsons.mkdir()
    (simpsons / "S05E01 Homer.mp4").write_bytes(b"\x00" * 64)
    (simpsons / "S05E02 Bart.mp4").write_bytes(b"\x00" * 64)

    # Fill series
    futurama = tmp_path / "Futurama"
    futurama.mkdir()
    (futurama / "S01E01 Space Pilot.mp4").write_bytes(b"\x00" * 64)

    malcolm = tmp_path / "Malcolm Mittendrin"
    malcolm.mkdir()
    (malcolm / "S01E01 Pilot.mp4").write_bytes(b"\x00" * 64)

    return tmp_path


@pytest.fixture()
def channel_schedule(tmp_path):
    """Create a minimal channel schedule YAML."""
    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        """\
channel_name: "Test-TV"
default_filler: "both"

fill_series:
  - "Futurama"
  - "Malcolm Mittendrin"

schedule:
  - weekday: "daily"
    slots:
      - time: "20:00"
        series: "Breaking Bad"
        strategy: "sequential"
      - time: "21:00"
        series: "Simpsons"
        strategy: "random"
""",
        encoding="utf-8",
    )
    return schedule


# ---------------------------------------------------------------------------
# Unit tests for playlist building
# ---------------------------------------------------------------------------


class TestBuildChannelPlaylist:
    """Test the playlist builder logic."""

    def test_builds_nonempty_playlist(self, channel_library, channel_schedule, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file
        from hometools.streaming.channel.server_playlist import build_channel_playlist

        data = parse_schedule_file(channel_schedule)
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        playlist = build_channel_playlist(data, channel_library, state_dir)
        assert len(playlist) > 0

    def test_playlist_contains_scheduled_series(self, channel_library, channel_schedule, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file
        from hometools.streaming.channel.server_playlist import build_channel_playlist

        data = parse_schedule_file(channel_schedule)
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        playlist = build_channel_playlist(data, channel_library, state_dir)
        artists = {item.artist for item in playlist}
        assert "Breaking Bad" in artists
        assert "Simpsons" in artists

    def test_playlist_contains_fill_items(self, channel_library, channel_schedule, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file
        from hometools.streaming.channel.server_playlist import build_channel_playlist

        data = parse_schedule_file(channel_schedule)
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        playlist = build_channel_playlist(data, channel_library, state_dir)
        artists = {item.artist for item in playlist}
        # At least one fill series should be present
        assert artists & {"Futurama", "Malcolm Mittendrin"}

    def test_all_items_are_media_items(self, channel_library, channel_schedule, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file
        from hometools.streaming.channel.server_playlist import build_channel_playlist
        from hometools.streaming.core.models import MediaItem

        data = parse_schedule_file(channel_schedule)
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        playlist = build_channel_playlist(data, channel_library, state_dir)
        for item in playlist:
            assert isinstance(item, MediaItem)
            assert item.media_type == "video"
            assert item.stream_url.startswith("/video/stream?path=")

    def test_empty_library_returns_empty_playlist(self, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file
        from hometools.streaming.channel.server_playlist import build_channel_playlist

        # Empty library
        empty_lib = tmp_path / "empty_lib"
        empty_lib.mkdir()
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        schedule = tmp_path / "schedule.yaml"
        schedule.write_text(
            'channel_name: "Test"\nschedule:\n  - weekday: "daily"\n    slots:\n      - time: "20:00"\n        series: "NoSuchSeries"\n',
            encoding="utf-8",
        )
        data = parse_schedule_file(schedule)
        playlist = build_channel_playlist(data, empty_lib, state_dir)
        assert playlist == []


# ---------------------------------------------------------------------------
# Integration tests for the FastAPI app
# ---------------------------------------------------------------------------


class TestChannelPlaylistApp:
    """Test the channel server FastAPI endpoints."""

    @pytest.fixture()
    def client(self, channel_library, channel_schedule, tmp_path):
        """Create a test client for the channel server."""
        from fastapi.testclient import TestClient

        from hometools.streaming.channel.server_playlist import create_app

        with (
            patch("hometools.streaming.channel.server_playlist.get_cache_dir", return_value=tmp_path / "cache"),
            patch("hometools.streaming.channel.server_playlist.get_channel_state_dir", return_value=tmp_path / "state"),
        ):
            (tmp_path / "cache").mkdir(exist_ok=True)
            (tmp_path / "state").mkdir(exist_ok=True)

            app = create_app(channel_library, schedule_file=channel_schedule)
            with TestClient(app) as c:
                yield c

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_home_page_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Test-TV" in resp.text

    def test_items_api_returns_items_key(self, client):
        resp = client.get("/api/channel/items")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "count" in data
        assert isinstance(data["items"], list)

    def test_epg_endpoint(self, client):
        resp = client.get("/api/channel/epg")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_now_endpoint(self, client):
        resp = client.get("/api/channel/now")
        assert resp.status_code == 200
        data = resp.json()
        assert "series" in data

    def test_schedule_raw_endpoint(self, client):
        resp = client.get("/api/channel/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert "schedule" in data

    def test_manifest_json(self, client):
        resp = client.get("/manifest.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "Test-TV" in data.get("name", "")

    def test_service_worker(self, client):
        resp = client.get("/sw.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]
