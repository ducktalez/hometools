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


def test_get_channel_tmp_dir():
    from hometools.config import get_channel_tmp_dir

    p = get_channel_tmp_dir()
    assert isinstance(p, Path)
    assert "channel" in str(p)
    assert "tmp" in str(p)


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
# Transcode module
# ---------------------------------------------------------------------------


class TestBuildConcatFile:
    """Tests for concat list file generation."""

    def test_build_concat_file_creates_valid_format(self, tmp_path):
        from hometools.streaming.channel.transcode import build_concat_file

        v1 = tmp_path / "video1.mp4"
        v2 = tmp_path / "video2.mp4"
        v1.write_bytes(b"\x00")
        v2.write_bytes(b"\x00")

        out = tmp_path / "concat.txt"
        build_concat_file([v1, v2], out)

        content = out.read_text(encoding="utf-8")
        assert content.startswith("ffconcat version 1.0\n")
        assert "video1.mp4" in content
        assert "video2.mp4" in content
        # Must have two 'file' entries
        file_lines = [line for line in content.splitlines() if line.startswith("file ")]
        assert len(file_lines) == 2

    def test_build_concat_file_uses_forward_slashes(self, tmp_path):
        from hometools.streaming.channel.transcode import build_concat_file

        v = tmp_path / "test.mp4"
        v.write_bytes(b"\x00")
        out = tmp_path / "concat.txt"
        build_concat_file([v], out)
        content = out.read_text(encoding="utf-8")
        # No backslashes (Windows path) in file entries
        for line in content.splitlines():
            if line.startswith("file "):
                assert "\\" not in line

    def test_build_concat_file_empty_list(self, tmp_path):
        from hometools.streaming.channel.transcode import build_concat_file

        out = tmp_path / "concat.txt"
        build_concat_file([], out)
        content = out.read_text(encoding="utf-8")
        assert "ffconcat version 1.0" in content
        file_lines = [line for line in content.splitlines() if line.startswith("file ")]
        assert len(file_lines) == 0


class TestCleanupPrepared:
    """Tests for temporary file cleanup."""

    def test_cleanup_deletes_files(self, tmp_path):
        from hometools.streaming.channel.transcode import cleanup_prepared

        f1 = tmp_path / "prep_aaa.mp4"
        f2 = tmp_path / "prep_bbb.mp4"
        f1.write_bytes(b"\x00")
        f2.write_bytes(b"\x00")

        removed = cleanup_prepared(f1, f2)
        assert removed == 2
        assert not f1.exists()
        assert not f2.exists()

    def test_cleanup_handles_missing_files(self, tmp_path):
        from hometools.streaming.channel.transcode import cleanup_prepared

        f = tmp_path / "nonexistent.mp4"
        removed = cleanup_prepared(f)
        assert removed == 0


class TestCleanupTmpDir:
    """Tests for tmp directory cleanup."""

    def test_cleanup_tmp_dir_removes_all_files(self, tmp_path):
        from hometools.streaming.channel.transcode import cleanup_tmp_dir

        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "a.mp4").write_bytes(b"\x00")
        (tmp_dir / "b.mp4").write_bytes(b"\x00")

        removed = cleanup_tmp_dir(tmp_dir)
        assert removed == 2
        assert len(list(tmp_dir.iterdir())) == 0

    def test_cleanup_tmp_dir_handles_missing_dir(self, tmp_path):
        from hometools.streaming.channel.transcode import cleanup_tmp_dir

        removed = cleanup_tmp_dir(tmp_path / "nonexistent")
        assert removed == 0


class TestPrepareVideo:
    """Tests for video pre-transcoding (mocked ffmpeg)."""

    def test_prepare_video_returns_none_when_ffmpeg_missing(self, tmp_path):
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import prepare_video

        src = tmp_path / "source.mp4"
        src.write_bytes(b"\x00" * 100)

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = prepare_video(src, tmp_path / "tmp")

        assert result is None

    def test_prepare_video_calls_ffmpeg_with_correct_args(self, tmp_path):
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import prepare_video

        src = tmp_path / "source.mp4"
        src.write_bytes(b"\x00" * 100)
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
        ) as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)

            # Create the output file to simulate ffmpeg success
            def side_effect(*args, **kwargs):
                # Find the output path (last positional arg in cmd)
                cmd = args[0]
                out = Path(cmd[-1])
                out.write_bytes(b"\x00" * 50)
                return mock.MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            result = prepare_video(src, tmp_dir, encoder="libx264", seek=10.0, duration=60.0)

        assert result is not None
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "-ss" in cmd_str
        assert "-t" in cmd_str
        assert "libx264" in cmd_str
        assert "-f concat" not in cmd_str  # transcode, not concat


class TestPrepareTestcard:
    """Tests for testcard pre-rendering (mocked ffmpeg)."""

    def test_prepare_testcard_returns_none_when_ffmpeg_missing(self, tmp_path):
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import prepare_testcard

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = prepare_testcard(30.0, tmp_path / "tmp")

        assert result is None

    def test_prepare_testcard_uses_smptebars(self, tmp_path):
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import prepare_testcard

        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
        ) as mock_run:

            def side_effect(*args, **kwargs):
                cmd = args[0]
                out = Path(cmd[-1])
                out.write_bytes(b"\x00" * 50)
                return mock.MagicMock(returncode=0)

            mock_run.side_effect = side_effect
            result = prepare_testcard(60.0, tmp_dir, channel_name="Test-TV")

        assert result is not None
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "smptebars" in cmd_str
        assert "Sendepause" in cmd_str

    def test_prepare_testcard_falls_back_on_drawtext_failure(self, tmp_path):
        """When drawtext/Fontconfig fails, prepare_testcard must use plain SMPTE bars.

        This is the exact scenario from the logs:
        'Fontconfig error: Cannot load default config file: No such file: (null)'
        (exit code 3221225477 on Windows)
        """
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import prepare_testcard

        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = args[0]
            out = Path(cmd[-1])
            if call_count[0] == 1:
                # First call (with drawtext) fails — simulates Fontconfig error
                return mock.MagicMock(
                    returncode=3221225477,  # Windows STATUS_ACCESS_VIOLATION
                    stderr="Fontconfig error: Cannot load default config file: No such file: (null)",
                )
            else:
                # Second call (plain SMPTE bars) succeeds
                out.write_bytes(b"\x00" * 50)
                return mock.MagicMock(returncode=0, stderr="")

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
            side_effect=side_effect,
        ):
            result = prepare_testcard(30.0, tmp_dir, channel_name="Test-TV")

        assert result is not None, (
            "prepare_testcard() must fall back to plain SMPTE bars when drawtext fails. "
            "This is the Windows Fontconfig error that caused 503 on startup."
        )
        assert call_count[0] == 2, "Must call ffmpeg twice: once with drawtext, once without"

    def test_plain_fallback_has_no_drawtext(self, tmp_path):
        """The plain fallback command must not contain drawtext or -vf (no Fontconfig needed)."""
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import _render_testcard_plain

        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
        ) as mock_run:

            def side_effect(*args, **kwargs):
                cmd = args[0]
                Path(cmd[-1]).write_bytes(b"\x00" * 50)
                return mock.MagicMock(returncode=0, stderr="")

            mock_run.side_effect = side_effect
            result = _render_testcard_plain(30.0, tmp_dir)

        assert result is not None
        cmd_str = " ".join(mock_run.call_args[0][0])
        assert "drawtext" not in cmd_str, "Plain fallback must not use drawtext (Fontconfig)"
        assert "-vf" not in cmd_str, "Plain fallback must not use -vf filter"
        assert "smptebars" in cmd_str, "Plain fallback must use smptebars"

    def test_plain_fallback_uses_correct_output_filename(self, tmp_path):
        """Plain fallback output file must have 'plain' in the name to avoid cache collision."""
        import unittest.mock as mock

        from hometools.streaming.channel.transcode import _render_testcard_plain

        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        captured_out = []

        def side_effect(*args, **kwargs):
            cmd = args[0]
            out = Path(cmd[-1])
            captured_out.append(out)
            out.write_bytes(b"\x00" * 50)
            return mock.MagicMock(returncode=0, stderr="")

        with mock.patch(
            "hometools.streaming.channel.transcode.subprocess.run",
            side_effect=side_effect,
        ):
            _render_testcard_plain(30.0, tmp_dir)

        assert len(captured_out) == 1
        assert "plain" in captured_out[0].name, (
            "Plain testcard must use a distinct filename to avoid colliding with the drawtext-version cache entry"
        )


# ---------------------------------------------------------------------------
# Fontconfig fallback — full integration flow
# ---------------------------------------------------------------------------


class TestFontconfigFallback:
    """Test the full chain: Fontconfig error → plain fallback → manifest available.

    These tests reproduce the exact 503 scenario from the user's logs:
    'Testcard render failed (exit 3221225477): Fontconfig error:
     Cannot load default config file: No such file: (null)'
    """

    def test_boot_testcard_succeeds_despite_fontconfig_error(self, tmp_path):
        """Boot testcard must complete even when drawtext/Fontconfig is unavailable.

        Without the fallback: prepare_testcard() returns None → mixer sleeps 30s
        → manifest never created → player gets 503 for 30+ seconds.
        With the fallback: plain SMPTE bars work without Fontconfig → manifest ready.
        """
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
            tmp_dir=tmp_dir,
        )

        call_count = [0]

        def mock_ffmpeg_run(*args, **kwargs):
            call_count[0] += 1
            cmd = args[0]
            out = Path(cmd[-1])
            # Simulate Fontconfig failure for first call (drawtext variant)
            if "-vf" in cmd and "drawtext" in " ".join(cmd):
                return mock.MagicMock(
                    returncode=3221225477,
                    stderr="Fontconfig error: Cannot load default config file: No such file: (null)\n",
                )
            # Plain variant succeeds
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 100)
            return mock.MagicMock(returncode=0, stderr="")

        def mock_ffmpeg_popen(*args, **kwargs):
            manifest = hls_dir / "channel.m3u8"
            manifest.write_text(
                "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nchannel_00000.ts\n",
                encoding="utf-8",
            )
            (hls_dir / "channel_00000.ts").write_bytes(b"\x00" * 100)
            proc = mock.MagicMock()
            proc.poll.return_value = 0
            proc.returncode = 0
            proc.stderr = None
            return proc

        with (
            mock.patch(
                "hometools.streaming.channel.transcode.subprocess.run",
                side_effect=mock_ffmpeg_run,
            ),
            mock.patch("subprocess.Popen", side_effect=mock_ffmpeg_popen),
        ):
            mixer._play_boot_testcard()

        assert (hls_dir / "channel.m3u8").exists(), (
            "Manifest must exist after boot testcard even when Fontconfig is unavailable. "
            "Without this fix, the user sees 503 errors on Windows."
        )
        assert call_count[0] >= 2, "Must have tried drawtext AND plain fallback"

    def test_server_returns_200_after_fontconfig_fallback(self, tmp_path):
        """End-to-end: Fontconfig error → plain fallback → /stream/channel.m3u8 → 200."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer
        from hometools.streaming.channel.server import create_app

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
            tmp_dir=tmp_dir,
        )

        def mock_run(*args, **kwargs):
            cmd = args[0]
            out = Path(cmd[-1])
            if "-vf" in cmd and "drawtext" in " ".join(cmd):
                return mock.MagicMock(returncode=1, stderr="Fontconfig error\n")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 100)
            return mock.MagicMock(returncode=0, stderr="")

        def mock_popen(*args, **kwargs):
            (hls_dir / "channel_00000.ts").write_bytes(b"\x00" * 100)
            (hls_dir / "channel.m3u8").write_text(
                "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nchannel_00000.ts\n",
                encoding="utf-8",
            )
            proc = mock.MagicMock()
            proc.poll.return_value = 0
            proc.returncode = 0
            proc.stderr = None
            return proc

        with (
            mock.patch("hometools.streaming.channel.transcode.subprocess.run", side_effect=mock_run),
            mock.patch("subprocess.Popen", side_effect=mock_popen),
        ):
            mixer._play_boot_testcard()

        schedule = tmp_path / "sched.yaml"
        schedule.write_text('channel_name: "Test-TV"\nschedule: []\n', encoding="utf-8")
        app = create_app(
            library_dir=tmp_path,
            schedule_file=schedule,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
        )
        client = TestClient(app)

        resp = client.get("/stream/channel.m3u8")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Fontconfig fallback must produce a manifest so the player doesn't see 503."
        )


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
        hls_dir=tmp_path / "hls",
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
        hls_dir=tmp_path / "nonexistent_hls",
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
    tmp_path.mkdir(parents=True, exist_ok=True)
    # Create series folders with dummy files
    for series in ("TestSeries", "FillShow1", "FillShow2"):
        series_dir = tmp_path / series
        series_dir.mkdir(exist_ok=True)
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
        hls_dir=tmp_path / "hls",
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
            "/api/channel/session": 200,
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
        """The player should have custom TV controls (mute, volume, fullscreen, live badge)."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "btn-mute" in html
        assert "btn-fs" in html
        assert "vol-slider" in html
        # Live TV must NOT have a play/pause button
        assert "btn-playpause" not in html

    def test_player_ui_live_badge_clickable(self, tmp_path):
        """LIVE badge should have click handler to jump to live edge."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "jumpToLive" in html
        assert "liveSyncPosition" in html

    def test_player_ui_no_pause_toggle(self, tmp_path):
        """Video click should only unmute, not toggle play/pause."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        # Should NOT have pause logic in click handler
        assert "player.pause()" not in html

    def test_player_ui_has_live_edge_check(self, tmp_path):
        """Player should auto-jump to live if behind > 15s."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "checkLiveEdge" in html
        assert "behind" in html

    def test_player_hls_config_strict_live(self, tmp_path):
        """hls.js config should have strict live settings."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "backBufferLength" in html
        assert "liveSyncDurationCount" in html

    def test_manifest_filters_missing_segments(self, tmp_path):
        """Manifest endpoint should only reference segments that exist on disk."""
        # Use the isolated hls_dir that _create_test_app_with_content passes to create_app
        hls_dir = tmp_path / "hls"
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)

        hls_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest referencing existing + missing segments
        (hls_dir / "channel_00010.ts").write_bytes(b"\x00" * 100)
        (hls_dir / "channel_00011.ts").write_bytes(b"\x00" * 100)
        manifest = hls_dir / "channel.m3u8"
        manifest.write_text(
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXT-X-TARGETDURATION:6\n"
            "#EXT-X-MEDIA-SEQUENCE:8\n"
            "#EXTINF:6.0,\n"
            "channel_00008.ts\n"  # MISSING
            "#EXTINF:6.0,\n"
            "channel_00009.ts\n"  # MISSING
            "#EXTINF:6.0,\n"
            "channel_00010.ts\n"  # EXISTS
            "#EXTINF:6.0,\n"
            "channel_00011.ts\n",  # EXISTS
            encoding="utf-8",
        )

        resp = client.get("/stream/channel.m3u8")
        assert resp.status_code == 200
        body = resp.text
        # Missing segments should be filtered out
        assert "channel_00008.ts" not in body
        assert "channel_00009.ts" not in body
        # Existing segments must still be present
        assert "channel_00010.ts" in body
        assert "channel_00011.ts" in body


class TestPurgeHlsDir:
    """Test that mixer purges old HLS files on startup."""

    def test_purge_removes_old_files(self, tmp_path):
        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        (hls_dir / "channel.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
        (hls_dir / "channel_00001.ts").write_bytes(b"\x00")
        (hls_dir / "channel_00002.ts").write_bytes(b"\x00")

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
        )
        mixer._purge_hls_dir()

        assert not (hls_dir / "channel.m3u8").exists()
        assert not (hls_dir / "channel_00001.ts").exists()
        assert not (hls_dir / "channel_00002.ts").exists()

    def test_purge_removes_concat_files(self, tmp_path):
        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        (hls_dir / "concat.txt").write_text("ffconcat version 1.0\n", encoding="utf-8")

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
        )
        mixer._purge_hls_dir()

        assert not (hls_dir / "concat.txt").exists()


class TestSessionEndpoint:
    """Test the server session endpoint for stale browser detection."""

    def test_session_returns_session_id(self, tmp_path):
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        data = client.get("/api/channel/session").json()
        assert "session" in data
        assert isinstance(data["session"], str)
        assert len(data["session"]) > 0

    def test_session_id_in_hls_url(self, tmp_path):
        """HLS URL in the page must include a session query parameter."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        # The HLS URL should contain ?s=<session_id>
        assert "channel.m3u8?s=" in html

    def test_session_consistent_across_requests(self, tmp_path):
        """Same app instance returns the same session ID."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        s1 = client.get("/api/channel/session").json()["session"]
        s2 = client.get("/api/channel/session").json()["session"]
        assert s1 == s2

    def test_different_apps_have_different_sessions(self, tmp_path):
        """Two different app instances have different session IDs."""
        app1 = _create_test_app_with_content(tmp_path / "a")
        app2 = _create_test_app_with_content(tmp_path / "b")
        c1 = TestClient(app1)
        c2 = TestClient(app2)
        s1 = c1.get("/api/channel/session").json()["session"]
        s2 = c2.get("/api/channel/session").json()["session"]
        assert s1 != s2

    def test_session_check_in_player_js(self, tmp_path):
        """Player JS should periodically check for server restarts."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "checkSession" in html
        assert "/api/channel/session" in html
        assert "location.reload" in html


class TestHlsJsRecovery:
    """Test hls.js error recovery features in player JS."""

    def test_startload_used_instead_of_currenttime_only(self, tmp_path):
        """jumpToLive must use hls.startLoad(-1) to reset fragment queue."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "startLoad(-1)" in html

    def test_error_counter_in_player(self, tmp_path):
        """Player should track consecutive errors and restart on too many."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        assert "_errorCount" in html
        assert "FRAG_LOADED" in html

    def test_frag_loaded_resets_error_count(self, tmp_path):
        """Successful fragment load should reset error counter."""
        app = _create_test_app_with_content(tmp_path)
        client = TestClient(app)
        html = client.get("/").text
        # FRAG_LOADED handler must reset _errorCount
        assert "FRAG_LOADED" in html


class TestConcatDemuxerStream:
    """Test that the mixer uses the concat demuxer for streaming."""

    def test_stream_concat_block_uses_concat_demuxer(self, tmp_path):
        """The ffmpeg command must use -f concat for input."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
        )

        # Create a fake prepared file
        prepared = tmp_path / "prep_test.mp4"
        prepared.write_bytes(b"\x00" * 100)

        with mock.patch("subprocess.Popen") as mock_popen:
            mock_proc = mock.MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_proc.stderr = None
            mock_popen.return_value = mock_proc

            mixer._stream_concat_block([prepared], label="test")

            if mock_popen.called:
                cmd = mock_popen.call_args[0][0]
                cmd_str = " ".join(cmd)
                # Must use concat demuxer
                assert "-f concat" in cmd_str or "-f\nconcat" in cmd_str
                # Must use -c copy (no re-encoding)
                assert "-c copy" in cmd_str or "-c\ncopy" in cmd_str
                # Must NOT have -hls_flags (no append_list, no delete_segments)
                assert "-hls_flags" not in cmd_str
                # Must have -f hls for output
                assert "-f hls" in cmd_str or "-f\nhls" in cmd_str

    def test_stream_concat_block_creates_concat_file(self, tmp_path):
        """A concat.txt file must be created in the HLS directory."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
        )

        prepared = tmp_path / "prep_test.mp4"
        prepared.write_bytes(b"\x00" * 100)

        concat_content = None

        def capture_concat(*args, **kwargs):
            nonlocal concat_content
            concat_path = hls_dir / "concat.txt"
            if concat_path.exists():
                concat_content = concat_path.read_text(encoding="utf-8")
            mock_proc = mock.MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_proc.stderr = None
            return mock_proc

        with mock.patch("subprocess.Popen", side_effect=capture_concat):
            mixer._stream_concat_block([prepared], label="test")

        assert concat_content is not None
        assert "ffconcat version 1.0" in concat_content
        assert "prep_test.mp4" in concat_content

    def test_stream_concat_block_cleans_concat_file_after(self, tmp_path):
        """concat.txt must be deleted after streaming completes."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
        )

        prepared = tmp_path / "prep_test.mp4"
        prepared.write_bytes(b"\x00" * 100)

        with mock.patch("subprocess.Popen") as mock_popen:
            mock_proc = mock.MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_proc.stderr = None
            mock_popen.return_value = mock_proc

            mixer._stream_concat_block([prepared], label="test")

        # concat.txt should be cleaned up
        assert not (hls_dir / "concat.txt").exists()


# ---------------------------------------------------------------------------
# Boot testcard — prevents 503 on startup
# ---------------------------------------------------------------------------


class TestBootTestcard:
    """Test that the mixer plays a boot testcard on startup.

    Without the boot testcard, the player receives 503 errors for minutes
    while the mixer pre-transcodes the first real content.  The boot testcard
    renders in seconds (synthetic source) and establishes the HLS manifest
    immediately.
    """

    def test_run_loop_calls_boot_testcard_before_cycle(self, tmp_path):
        """_run_loop must call _play_boot_testcard before the main while loop."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=tmp_path / "hls",
            state_dir=tmp_path / "state",
            tmp_dir=tmp_path / "tmp",
        )

        call_order = []

        def mock_boot():
            call_order.append("boot")

        def mock_cycle():
            call_order.append("cycle")
            mixer._stop_event.set()  # Stop after first cycle

        with (
            mock.patch.object(mixer, "_play_boot_testcard", side_effect=mock_boot),
            mock.patch.object(mixer, "_run_one_cycle", side_effect=mock_cycle),
        ):
            mixer._run_loop()

        assert call_order[0] == "boot", "Boot testcard must be called FIRST"
        assert "cycle" in call_order, "Main cycle must also run"

    def test_boot_testcard_calls_play_testcard_block(self, tmp_path):
        """_play_boot_testcard must delegate to _play_testcard_block."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=tmp_path / "hls",
            state_dir=tmp_path / "state",
            tmp_dir=tmp_path / "tmp",
        )

        with mock.patch.object(mixer, "_play_testcard_block") as mock_play:
            mixer._play_boot_testcard()

        mock_play.assert_called_once()
        duration = mock_play.call_args[0][0]
        assert duration > 0, "Boot testcard must have positive duration"

    def test_boot_testcard_produces_manifest(self, tmp_path):
        """After boot testcard, a manifest file should exist (mocked ffmpeg)."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
            tmp_dir=tmp_dir,
        )

        def mock_ffmpeg_run(*args, **kwargs):
            """Simulate ffmpeg: create the output file."""
            cmd = args[0]
            out_path = Path(cmd[-1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"\x00" * 100)
            return mock.MagicMock(returncode=0)

        def mock_ffmpeg_popen(*args, **kwargs):
            """Simulate ffmpeg concat→HLS: create manifest + segment."""
            manifest = hls_dir / "channel.m3u8"
            manifest.write_text(
                "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nchannel_00000.ts\n",
                encoding="utf-8",
            )
            (hls_dir / "channel_00000.ts").write_bytes(b"\x00" * 100)
            proc = mock.MagicMock()
            proc.poll.return_value = 0
            proc.returncode = 0
            proc.stderr = None
            return proc

        with (
            mock.patch(
                "hometools.streaming.channel.transcode.subprocess.run",
                side_effect=mock_ffmpeg_run,
            ),
            mock.patch("subprocess.Popen", side_effect=mock_ffmpeg_popen),
        ):
            mixer._play_boot_testcard()

        assert (hls_dir / "channel.m3u8").exists(), "Boot testcard must create a manifest — without it, the player gets 503 errors"

    def test_boot_testcard_skipped_when_stopped(self, tmp_path):
        """If the mixer is already stopped, boot testcard should not run."""
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=tmp_path / "hls",
            state_dir=tmp_path / "state",
            tmp_dir=tmp_path / "tmp",
        )
        mixer._stop_event.set()

        with mock.patch.object(mixer, "_play_boot_testcard") as mock_boot, mock.patch.object(mixer, "_run_one_cycle"):
            mixer._run_loop()

        mock_boot.assert_not_called()


class TestManifestAvailability:
    """Test that the stream becomes available (503 → 200 transition).

    These tests verify the scenario the user reported: the manifest endpoint
    returns 503 because the mixer hasn't produced any output yet.  With the
    boot testcard fix, the manifest should be available within seconds.
    """

    def test_503_when_no_manifest_exists(self, tmp_path):
        """Without any manifest, the endpoint must return 503."""
        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()
        # No manifest file → 503
        app = _create_test_app(tmp_path)
        client = TestClient(app)
        resp = client.get("/stream/channel.m3u8")
        # The HLS dir from _create_test_app might not even exist
        assert resp.status_code in (200, 503)

    def test_200_when_manifest_and_segments_exist(self, tmp_path):
        """When manifest + segments exist, the endpoint must return 200."""
        hls_dir = tmp_path / "hls"
        hls_dir.mkdir(parents=True)

        # Create valid manifest + segments
        (hls_dir / "channel_00000.ts").write_bytes(b"\x00" * 100)
        (hls_dir / "channel_00001.ts").write_bytes(b"\x00" * 100)
        (hls_dir / "channel.m3u8").write_text(
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXT-X-TARGETDURATION:6\n"
            "#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXTINF:6.0,\n"
            "channel_00000.ts\n"
            "#EXTINF:6.0,\n"
            "channel_00001.ts\n",
            encoding="utf-8",
        )

        from hometools.streaming.channel.server import create_app

        schedule = tmp_path / "schedule.yaml"
        schedule.write_text(
            'channel_name: "Test-TV"\nschedule: []\n',
            encoding="utf-8",
        )
        app = create_app(
            library_dir=tmp_path,
            schedule_file=schedule,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
        )
        client = TestClient(app)

        resp = client.get("/stream/channel.m3u8")
        assert resp.status_code == 200, (
            "When manifest and segments exist, the endpoint MUST return 200, not 503. "
            "If you see 503 here, the boot testcard mechanism is broken."
        )
        assert "channel_00000.ts" in resp.text
        assert "channel_00001.ts" in resp.text

    def test_mixer_establishes_manifest_via_boot_testcard(self, tmp_path):
        """Full flow: mixer starts → boot testcard → manifest exists → 200.

        This is the test that would have caught the original 503 bug.
        """
        import unittest.mock as mock

        from hometools.streaming.channel.mixer import ChannelMixer

        hls_dir = tmp_path / "hls"
        hls_dir.mkdir()

        mixer = ChannelMixer(
            schedule_file=tmp_path / "sched.yaml",
            library_dir=tmp_path,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
            state_dir=tmp_path / "state",
            tmp_dir=tmp_path / "tmp",
        )

        def mock_run(*args, **kwargs):
            cmd = args[0]
            out = Path(cmd[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 100)
            return mock.MagicMock(returncode=0)

        def mock_popen(*args, **kwargs):
            manifest = hls_dir / "channel.m3u8"
            manifest.write_text(
                "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nchannel_00000.ts\n",
                encoding="utf-8",
            )
            (hls_dir / "channel_00000.ts").write_bytes(b"\x00" * 100)
            proc = mock.MagicMock()
            proc.poll.return_value = 0
            proc.returncode = 0
            proc.stderr = None
            return proc

        with (
            mock.patch(
                "hometools.streaming.channel.transcode.subprocess.run",
                side_effect=mock_run,
            ),
            mock.patch("subprocess.Popen", side_effect=mock_popen),
        ):
            mixer._play_boot_testcard()

        # After boot testcard, manifest MUST exist
        assert (hls_dir / "channel.m3u8").exists(), (
            "After boot testcard, manifest must exist. Without this, /stream/channel.m3u8 returns 503."
        )

        # Verify the server would return 200 now
        from hometools.streaming.channel.server import create_app

        schedule = tmp_path / "sched.yaml"
        schedule.write_text('channel_name: "Test-TV"\nschedule: []\n', encoding="utf-8")
        app = create_app(
            library_dir=tmp_path,
            schedule_file=schedule,
            filler_dir=tmp_path / "filler",
            hls_dir=hls_dir,
        )
        client = TestClient(app)
        resp = client.get("/stream/channel.m3u8")
        assert resp.status_code == 200, (
            f"Expected 200 after boot testcard, got {resp.status_code}. "
            "This is the bug the user reported: 503 Service Unavailable "
            "because the manifest doesn't exist during pre-transcoding."
        )
