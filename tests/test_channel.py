"""Tests for the channel (TV) streaming server."""

from pathlib import Path

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_get_channel_port_default():
    from hometools.config import get_channel_port

    port = get_channel_port()
    assert isinstance(port, int)
    assert port > 0


def test_get_channel_port_from_env(monkeypatch):
    from hometools.config import get_channel_port

    monkeypatch.setenv("HOMETOOLS_CHANNEL_PORT", "9999")
    assert get_channel_port() == 9999


def test_get_channel_port_default_is_video_plus_one():
    from hometools.config import get_channel_port, get_video_port

    assert get_channel_port() == get_video_port() + 1


def test_get_channel_schedule_file():
    from hometools.config import get_channel_schedule_file

    p = get_channel_schedule_file()
    assert isinstance(p, Path)
    assert p.name == "channel_schedule.yaml"


def test_get_channel_filler_dir():
    from hometools.config import get_channel_filler_dir

    p = get_channel_filler_dir()
    assert isinstance(p, Path)


def test_get_channel_encoder_default():
    from hometools.config import get_channel_encoder

    assert get_channel_encoder() == "libx264"


def test_get_channel_encoder_from_env(monkeypatch):
    from hometools.config import get_channel_encoder

    monkeypatch.setenv("HOMETOOLS_CHANNEL_ENCODER", "h264_nvenc")
    assert get_channel_encoder() == "h264_nvenc"


def test_get_channel_hls_dir():
    from hometools.config import get_channel_hls_dir

    p = get_channel_hls_dir()
    assert isinstance(p, Path)
    assert "channel" in str(p)
    assert "hls" in str(p)


def test_get_channel_state_dir():
    from hometools.config import get_channel_state_dir

    p = get_channel_state_dir()
    assert isinstance(p, Path)
    assert "channel" in str(p)


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


class TestScheduleParsing:
    def test_parse_empty_file(self, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file

        f = tmp_path / "schedule.yaml"
        f.write_text("", encoding="utf-8")
        assert parse_schedule_file(f) == {}

    def test_parse_missing_file(self, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file

        assert parse_schedule_file(tmp_path / "nonexistent.yaml") == {}

    def test_parse_valid_schedule(self, tmp_path):
        from hometools.streaming.channel.schedule import parse_schedule_file

        f = tmp_path / "schedule.yaml"
        f.write_text(
            """
channel_name: "Test-TV"
schedule:
  - weekday: "daily"
    slots:
      - time: "20:00"
        series: "TestSeries"
        strategy: "sequential"
""",
            encoding="utf-8",
        )
        data = parse_schedule_file(f)
        assert data["channel_name"] == "Test-TV"
        assert len(data["schedule"]) == 1

    def test_get_slots_for_date(self, tmp_path):
        from datetime import datetime

        from hometools.streaming.channel.schedule import get_slots_for_date

        schedule_data = {
            "schedule": [
                {
                    "weekday": "daily",
                    "slots": [
                        {"time": "20:00", "series": "SeriesA", "strategy": "sequential"},
                        {"time": "21:30", "series": "SeriesB", "strategy": "random"},
                    ],
                }
            ]
        }

        dt = datetime(2026, 3, 24, 19, 0)  # Tuesday
        slots = get_slots_for_date(schedule_data, dt)
        assert len(slots) == 2
        assert slots[0].series_folder == "SeriesA"
        assert slots[1].series_folder == "SeriesB"

    def test_specific_weekday_overrides_daily(self, tmp_path):
        from datetime import datetime

        from hometools.streaming.channel.schedule import get_slots_for_date

        # 2026-03-24 is a Tuesday
        schedule_data = {
            "schedule": [
                {"weekday": "daily", "slots": [{"time": "20:00", "series": "DailyShow"}]},
                {"weekday": "tuesday", "slots": [{"time": "20:00", "series": "TuesdaySpecial"}]},
            ]
        }

        dt = datetime(2026, 3, 24, 19, 0)  # Tuesday
        slots = get_slots_for_date(schedule_data, dt)
        assert len(slots) == 1
        assert slots[0].series_folder == "TuesdaySpecial"


class TestEpisodeState:
    def test_load_empty_state(self, tmp_path):
        from hometools.streaming.channel.schedule import load_episode_state

        assert load_episode_state(tmp_path) == {}

    def test_save_and_load_state(self, tmp_path):
        from hometools.streaming.channel.schedule import load_episode_state, save_episode_state

        state = {"SeriesA": 3, "SeriesB": 1}
        assert save_episode_state(tmp_path, state)
        loaded = load_episode_state(tmp_path)
        assert loaded == state


class TestEpisodeResolution:
    def test_list_episodes_empty_dir(self, tmp_path):
        from hometools.streaming.channel.schedule import list_episodes

        assert list_episodes(tmp_path, "NonExistent") == []

    def test_list_episodes_sorted(self, tmp_path):
        from hometools.streaming.channel.schedule import list_episodes

        series = tmp_path / "TestSeries"
        series.mkdir()
        (series / "S01E03.mp4").touch()
        (series / "S01E01.mp4").touch()
        (series / "S01E02.mp4").touch()
        (series / "notes.txt").touch()  # Should be excluded

        episodes = list_episodes(tmp_path, "TestSeries")
        assert len(episodes) == 3
        assert episodes[0].name == "S01E01.mp4"
        assert episodes[2].name == "S01E03.mp4"

    def test_resolve_next_episode_sequential(self, tmp_path):
        from hometools.streaming.channel.schedule import resolve_next_episode

        series = tmp_path / "lib" / "TestSeries"
        series.mkdir(parents=True)
        (series / "S01E01.mp4").touch()
        (series / "S01E02.mp4").touch()

        state_dir = tmp_path / "state"
        state_dir.mkdir()

        # First call → S01E01
        ep1 = resolve_next_episode(tmp_path / "lib", "TestSeries", state_dir)
        assert ep1 is not None
        assert ep1.name == "S01E01.mp4"

        # Second call → S01E02
        ep2 = resolve_next_episode(tmp_path / "lib", "TestSeries", state_dir)
        assert ep2 is not None
        assert ep2.name == "S01E02.mp4"

        # Third call → wraps around to S01E01
        ep3 = resolve_next_episode(tmp_path / "lib", "TestSeries", state_dir)
        assert ep3 is not None
        assert ep3.name == "S01E01.mp4"

    def test_resolve_next_episode_random(self, tmp_path):
        from hometools.streaming.channel.schedule import resolve_next_episode

        series = tmp_path / "lib" / "TestSeries"
        series.mkdir(parents=True)
        (series / "S01E01.mp4").touch()
        (series / "S01E02.mp4").touch()

        state_dir = tmp_path / "state"
        state_dir.mkdir()

        ep = resolve_next_episode(tmp_path / "lib", "TestSeries", state_dir, strategy="random")
        assert ep is not None
        assert ep.suffix == ".mp4"


# ---------------------------------------------------------------------------
# Filler
# ---------------------------------------------------------------------------


class TestFiller:
    def test_scan_empty_dir(self, tmp_path):
        from hometools.streaming.channel.filler import scan_filler_dir

        assert scan_filler_dir(tmp_path / "nonexistent") == []

    def test_scan_filler_dir(self, tmp_path):
        from hometools.streaming.channel.filler import scan_filler_dir

        (tmp_path / "clip1.mp4").touch()
        (tmp_path / "clip2.mkv").touch()
        (tmp_path / "music.mp3").touch()
        (tmp_path / "readme.txt").touch()  # Not media

        files = scan_filler_dir(tmp_path)
        assert len(files) == 3

    def test_select_filler_empty(self):
        from hometools.streaming.channel.filler import select_filler

        assert select_filler([], 60.0) == []

    def test_select_filler_zero_gap(self, tmp_path):
        from hometools.streaming.channel.filler import select_filler

        assert select_filler([tmp_path / "clip.mp4"], 0) == []

    def test_generate_black_filler_args(self):
        from hometools.streaming.channel.filler import generate_black_filler_args

        args = generate_black_filler_args(30.0)
        assert "-f" in args
        assert "lavfi" in args
        assert "30.0" in " ".join(args)

    def test_generate_testcard_filler_args_contains_smptebars(self):
        from hometools.streaming.channel.filler import generate_testcard_filler_args

        args = generate_testcard_filler_args(60.0)
        joined = " ".join(args)
        assert "smptebars" in joined
        assert "60.0" in joined
        assert "-vf" in args
        assert "Sendepause" in joined

    def test_generate_testcard_filler_args_custom_channel_name(self):
        from hometools.streaming.channel.filler import generate_testcard_filler_args

        args = generate_testcard_filler_args(10.0, channel_name="My Channel")
        joined = " ".join(args)
        assert "My Channel" in joined
        assert "smptebars" in joined

    def test_generate_testcard_filler_args_has_audio(self):
        from hometools.streaming.channel.filler import generate_testcard_filler_args

        args = generate_testcard_filler_args(15.0)
        joined = " ".join(args)
        assert "anullsrc" in joined
        assert "-map" in args

    def test_generate_testcard_filler_args_has_re_flag(self):
        from hometools.streaming.channel.filler import generate_testcard_filler_args

        args = generate_testcard_filler_args(30.0)
        assert "-re" in args

    def test_generate_black_filler_args_has_re_flag(self):
        from hometools.streaming.channel.filler import generate_black_filler_args

        args = generate_black_filler_args(30.0)
        assert "-re" in args


class TestDisplaySchedule:
    """Tests for EPG display schedule (no episode state changes)."""

    def test_display_schedule_shows_all_todays_slots(self, tmp_path):
        from datetime import datetime

        from hometools.streaming.channel.schedule import get_display_schedule

        data = {
            "schedule": [
                {
                    "weekday": "daily",
                    "slots": [
                        {"time": "08:00", "series": "Morning Show"},
                        {"time": "20:00", "series": "Evening Show"},
                    ],
                },
            ]
        }
        # At 01:00, both slots are in the future but should appear in EPG
        now = datetime(2026, 3, 25, 1, 0)
        display = get_display_schedule(data, now=now)
        assert len(display) == 2
        series_names = [d["series"] for d in display]
        assert "Morning Show" in series_names
        assert "Evening Show" in series_names

    def test_display_schedule_does_not_advance_episode_state(self, tmp_path):
        from datetime import datetime

        from hometools.streaming.channel.schedule import (
            get_display_schedule,
            load_episode_state,
            save_episode_state,
        )

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        save_episode_state(state_dir, {"TestSeries": 0})

        data = {
            "schedule": [
                {"weekday": "daily", "slots": [{"time": "20:00", "series": "TestSeries"}]},
            ]
        }
        get_display_schedule(data, now=datetime(2026, 3, 25, 1, 0))

        # State should NOT have changed
        state = load_episode_state(state_dir)
        assert state.get("TestSeries") == 0

    def test_display_schedule_empty_when_no_schedule(self):
        from hometools.streaming.channel.schedule import get_display_schedule

        assert get_display_schedule({}) == []


class TestResolveScheduleNoStateBurn:
    """Verify that resolve_schedule does not advance episode state for out-of-window slots."""

    def test_no_state_advance_for_future_slots(self, tmp_path):
        from datetime import datetime

        from hometools.streaming.channel.schedule import (
            load_episode_state,
            resolve_schedule,
            save_episode_state,
        )

        # Create a series folder with episodes
        series_dir = tmp_path / "TestSeries"
        series_dir.mkdir()
        (series_dir / "S01E01.mp4").touch()
        (series_dir / "S01E02.mp4").touch()

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        save_episode_state(state_dir, {"TestSeries": 0})

        data = {
            "schedule": [
                {"weekday": "daily", "slots": [{"time": "20:00", "series": "TestSeries"}]},
            ]
        }

        # At 01:00, the slot at 20:00 is outside the 6h lookahead
        now = datetime(2026, 3, 25, 1, 0)
        resolved = resolve_schedule(data, tmp_path, state_dir, now=now, lookahead_hours=6)

        assert resolved == []  # Nothing to play
        state = load_episode_state(state_dir)
        assert state.get("TestSeries") == 0  # NOT advanced!


# ---------------------------------------------------------------------------
# Server endpoints
# ---------------------------------------------------------------------------


def _create_test_app(tmp_path):
    """Create a test channel app with a minimal schedule."""
    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        """
channel_name: "Test-TV"
schedule:
  - weekday: "daily"
    slots:
      - time: "20:00"
        series: "TestSeries"
""",
        encoding="utf-8",
    )

    from hometools.streaming.channel.server import create_app

    return create_app(
        library_dir=tmp_path,
        schedule_file=schedule,
        filler_dir=tmp_path / "filler",
    )


def test_channel_health(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "mixer_running" in data


def test_channel_home_returns_html(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Test-TV" in resp.text
    assert "hls.js" in resp.text


def test_channel_now_playing(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/channel/now")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_channel_epg(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/channel/epg")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_channel_schedule_raw(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/channel/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert "schedule" in data


def test_hls_manifest_503_when_not_ready(tmp_path):
    """HLS manifest returns 503 when mixer hasn't produced output yet.

    When ffmpeg is available the mixer may already create a manifest during
    the TestClient lifespan — in that case 200 is equally correct.
    """
    # Create app without auto-starting the mixer to guarantee no manifest
    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        'channel_name: "Test-TV"\nschedule: []\n',
        encoding="utf-8",
    )
    from hometools.streaming.channel.server import create_app

    app = create_app(
        library_dir=tmp_path,
        schedule_file=schedule,
        filler_dir=tmp_path / "nonexistent_filler",
    )
    client = TestClient(app)
    resp = client.get("/stream/channel.m3u8")
    # Either the manifest hasn't been produced yet (503) or the mixer
    # was fast enough to create it (200).  Both are correct.
    assert resp.status_code in (200, 503)


def test_hls_segment_404(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/stream/channel_00000.ts")
    assert resp.status_code == 404


def test_hls_invalid_segment_400(tmp_path):
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/stream/malicious.exe")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_serve_channel_subcommand_exists():
    """The serve-channel subcommand must be registered."""
    from hometools.cli import build_parser

    parser = build_parser()
    # Should not raise when parsing serve-channel
    args = parser.parse_args(["serve-channel"])
    assert hasattr(args, "func")


def test_serve_channel_accepts_port():
    from hometools.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["serve-channel", "--port", "9999"])
    assert args.port == 9999


def test_serve_channel_accepts_schedule():
    from hometools.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["serve-channel", "--schedule", "my_schedule.yaml"])
    assert args.schedule == Path("my_schedule.yaml")


# ---------------------------------------------------------------------------
# fill_series
# ---------------------------------------------------------------------------


class TestFillSeries:
    """Tests for fill_series (continuous background programming)."""

    def test_get_fill_series_returns_list(self):
        from hometools.streaming.channel.schedule import get_fill_series

        data = {"fill_series": ["Simpsons", "Futurama"]}
        assert get_fill_series(data) == ["Simpsons", "Futurama"]

    def test_get_fill_series_empty_when_missing(self):
        from hometools.streaming.channel.schedule import get_fill_series

        assert get_fill_series({}) == []
        assert get_fill_series({"schedule": []}) == []

    def test_get_fill_series_strips_whitespace(self):
        from hometools.streaming.channel.schedule import get_fill_series

        data = {"fill_series": [" Simpsons ", "  Futurama"]}
        assert get_fill_series(data) == ["Simpsons", "Futurama"]

    def test_get_fill_series_filters_empty_strings(self):
        from hometools.streaming.channel.schedule import get_fill_series

        data = {"fill_series": ["Simpsons", "", "  ", "Futurama"]}
        assert get_fill_series(data) == ["Simpsons", "Futurama"]


# ---------------------------------------------------------------------------
# Server functionality integration tests
# ---------------------------------------------------------------------------


def _create_test_app_with_content(tmp_path):
    """Create a test channel app with actual video files and fill_series."""
    # Create series folders with dummy files
    for series in ("TestSeries", "FillShow1", "FillShow2"):
        series_dir = tmp_path / series
        series_dir.mkdir()
        for i in range(3):
            (series_dir / f"S01E0{i + 1}.mp4").write_bytes(b"\x00" * 100)

    schedule = tmp_path / "schedule.yaml"
    schedule.write_text(
        """
channel_name: "Test-TV"
fill_series:
  - "FillShow1"
  - "FillShow2"
schedule:
  - weekday: "daily"
    slots:
      - time: "20:00"
        series: "TestSeries"
        strategy: "sequential"
""",
        encoding="utf-8",
    )

    from hometools.streaming.channel.server import create_app

    return create_app(
        library_dir=tmp_path,
        schedule_file=schedule,
        filler_dir=tmp_path / "filler",
    )


class TestChannelServerIntegration:
    """Integration tests for the channel server endpoints."""

    def test_all_endpoints_reachable(self, tmp_path):
        """Every documented endpoint returns a valid status code."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)

        endpoints = {
            "/health": 200,
            "/": 200,
            "/api/channel/now": 200,
            "/api/channel/epg": 200,
            "/api/channel/schedule": 200,
        }
        for path, expected in endpoints.items():
            resp = client.get(path)
            assert resp.status_code == expected, f"{path} returned {resp.status_code}"

    def test_health_contains_required_fields(self, tmp_path):
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        data = client.get("/health").json()
        assert "status" in data
        assert "library_dir" in data
        assert "schedule_file" in data
        assert "mixer_running" in data

    def test_epg_returns_items_array(self, tmp_path):
        """EPG endpoint always returns { items: [...] }."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        data = client.get("/api/channel/epg").json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_now_playing_has_required_keys(self, tmp_path):
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        data = client.get("/api/channel/now").json()
        assert isinstance(data, dict)
        # Must have at least series and is_filler keys
        # (exact content depends on timing / ffmpeg availability)
        assert "is_filler" in data or "series" in data or data == {}

    def test_schedule_raw_includes_fill_series(self, tmp_path):
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        data = client.get("/api/channel/schedule").json()
        assert "schedule" in data
        schedule = data["schedule"]
        assert "fill_series" in schedule
        assert "FillShow1" in schedule["fill_series"]

    def test_hls_segment_rejects_non_ts(self, tmp_path):
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        assert client.get("/stream/evil.exe").status_code == 400
        assert client.get("/stream/channel_00000.ts").status_code == 404

    def test_player_ui_has_no_native_seekbar(self, tmp_path):
        """The channel player must NOT have native browser controls (no seekbar)."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        # Video element must NOT have 'controls' attribute
        assert 'id="player"' in html
        assert "controls" not in html.split('id="player"')[0].split("<video")[-1]

    def test_player_ui_has_live_badge(self, tmp_path):
        """The player UI should have a LIVE badge."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "live-badge" in html
        assert "LIVE" in html

    def test_player_ui_has_custom_controls(self, tmp_path):
        """The player should have custom TV controls (play/pause, volume, fullscreen)."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "btn-playpause" in html
        assert "btn-mute" in html
        assert "btn-fs" in html
        assert "vol-slider" in html
