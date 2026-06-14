"""Tests for the on-the-fly remux / transcode module."""

from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hometools.streaming.core.remux import (
    BROWSER_NATIVE_EXTENSIONS,
    can_copy_codecs,
    ensure_faststart_cache,
    ensure_remux_cache,
    get_faststart_cache_path,
    get_remux_cache_path,
    has_faststart,
    needs_remux,
    probe_codecs,
    remux_stream,
)

# ---------------------------------------------------------------------------
# needs_remux
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ext,expected",
    [
        (".mp4", False),
        (".m4v", False),
        (".webm", False),
        (".ogg", False),
        (".ogv", False),
        (".flv", True),
        (".avi", True),
        (".mkv", True),
        (".wmv", True),
        (".vob", True),
        (".mov", True),
        (".avchd", True),
    ],
)
def test_needs_remux_by_extension(ext: str, expected: bool) -> None:
    assert needs_remux(Path(f"video{ext}")) is expected


def test_needs_remux_case_insensitive() -> None:
    assert needs_remux(Path("video.MP4")) is False
    assert needs_remux(Path("video.FLV")) is True


def test_browser_native_extensions_are_lowercase() -> None:
    for ext in BROWSER_NATIVE_EXTENSIONS:
        assert ext == ext.lower()
        assert ext.startswith(".")


# ---------------------------------------------------------------------------
# probe_codecs — mocked
# ---------------------------------------------------------------------------


def test_probe_codecs_returns_empty_on_missing_ffprobe() -> None:
    with patch("hometools.streaming.core.remux.subprocess.run", side_effect=FileNotFoundError):
        result = probe_codecs(Path("test.flv"))
    assert result == {"video": "", "audio": ""}


def test_probe_codecs_parses_ffprobe_output() -> None:
    video_result = MagicMock()
    video_result.returncode = 0
    video_result.stdout = "h264\n"

    audio_result = MagicMock()
    audio_result.returncode = 0
    audio_result.stdout = "aac\n"

    with patch("hometools.streaming.core.remux.subprocess.run", side_effect=[video_result, audio_result]):
        result = probe_codecs(Path("test.flv"))

    assert result == {"video": "h264", "audio": "aac"}


def test_probe_codecs_handles_ffprobe_failure() -> None:
    failed = MagicMock()
    failed.returncode = 1
    failed.stdout = ""

    with patch("hometools.streaming.core.remux.subprocess.run", return_value=failed):
        result = probe_codecs(Path("test.flv"))

    assert result["video"] == ""


# ---------------------------------------------------------------------------
# can_copy_codecs
# ---------------------------------------------------------------------------


def test_can_copy_codecs_true_for_h264_aac() -> None:
    with patch(
        "hometools.streaming.core.remux.probe_codecs",
        return_value={"video": "h264", "audio": "aac"},
    ):
        assert can_copy_codecs(Path("test.flv")) is True


def test_can_copy_codecs_false_for_mpeg4_xvid() -> None:
    with patch(
        "hometools.streaming.core.remux.probe_codecs",
        return_value={"video": "mpeg4", "audio": "mp3"},
    ):
        assert can_copy_codecs(Path("test.avi")) is False


def test_can_copy_codecs_false_when_probe_fails() -> None:
    with patch(
        "hometools.streaming.core.remux.probe_codecs",
        return_value={"video": "", "audio": ""},
    ):
        assert can_copy_codecs(Path("test.flv")) is False


# ---------------------------------------------------------------------------
# has_faststart
# ---------------------------------------------------------------------------


def _make_mp4_atoms(*atom_types: bytes) -> bytes:
    """Build a minimal MP4-like byte string with the given top-level atoms."""
    data = b""
    for atype in atom_types:
        # Each atom: 8 bytes header (4-byte size + 4-byte type) + 8 bytes body
        body = b"\x00" * 8
        size = struct.pack(">I", 8 + len(body))
        data += size + atype + body
    return data


def test_has_faststart_moov_before_mdat(tmp_path: Path) -> None:
    f = tmp_path / "fast.mp4"
    f.write_bytes(_make_mp4_atoms(b"ftyp", b"moov", b"mdat"))
    assert has_faststart(f) is True


def test_has_faststart_mdat_before_moov(tmp_path: Path) -> None:
    f = tmp_path / "slow.mp4"
    f.write_bytes(_make_mp4_atoms(b"ftyp", b"mdat", b"moov"))
    assert has_faststart(f) is False


def test_has_faststart_no_moov_no_mdat(tmp_path: Path) -> None:
    f = tmp_path / "weird.mp4"
    f.write_bytes(_make_mp4_atoms(b"ftyp", b"free"))
    assert has_faststart(f) is True  # optimistic


def test_has_faststart_non_mp4(tmp_path: Path) -> None:
    f = tmp_path / "video.webm"
    f.write_bytes(b"\x00" * 100)
    assert has_faststart(f) is True  # skip check for non-mp4


def test_has_faststart_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.mp4"
    f.write_bytes(b"")
    assert has_faststart(f) is True  # optimistic fallback


def test_has_faststart_io_error(tmp_path: Path) -> None:
    f = tmp_path / "missing.mp4"
    assert has_faststart(f) is True  # optimistic fallback


def test_has_faststart_m4v_extension(tmp_path: Path) -> None:
    f = tmp_path / "clip.m4v"
    f.write_bytes(_make_mp4_atoms(b"ftyp", b"mdat", b"moov"))
    assert has_faststart(f) is False


# ---------------------------------------------------------------------------
# remux_stream — mocked
# ---------------------------------------------------------------------------


def test_remux_stream_yields_nothing_when_ffmpeg_missing() -> None:
    with patch(
        "hometools.streaming.core.remux.subprocess.Popen",
        side_effect=FileNotFoundError,
    ):
        chunks = list(remux_stream(Path("test.flv"), copy=True))

    assert chunks == []


def test_remux_stream_yields_chunks_from_ffmpeg() -> None:
    mock_proc = MagicMock()
    mock_proc.stdout.read = MagicMock(side_effect=[b"chunk1", b"chunk2", b""])
    mock_proc.wait.return_value = None
    mock_proc.returncode = 0
    mock_proc.stderr = MagicMock()
    mock_proc.poll.return_value = 0

    with patch(
        "hometools.streaming.core.remux.subprocess.Popen",
        return_value=mock_proc,
    ):
        chunks = list(remux_stream(Path("test.flv"), copy=True))

    assert chunks == [b"chunk1", b"chunk2"]


def test_remux_stream_kills_ffmpeg_on_generator_exit() -> None:
    mock_proc = MagicMock()
    # Simulate reading chunks forever
    mock_proc.stdout.read = MagicMock(return_value=b"data")
    mock_proc.poll.return_value = None

    with patch(
        "hometools.streaming.core.remux.subprocess.Popen",
        return_value=mock_proc,
    ):
        gen = remux_stream(Path("test.flv"), copy=False)
        next(gen)  # get first chunk
        gen.close()  # simulate client disconnect

    mock_proc.kill.assert_called()


# ---------------------------------------------------------------------------
# Video stream endpoint integration
# ---------------------------------------------------------------------------


def test_video_stream_remuxes_flv(tmp_path: Path) -> None:
    """The /video/stream endpoint returns a StreamingResponse for .flv files."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    sub = tmp_path / "TestFolder"
    sub.mkdir()
    flv_file = sub / "clip.flv"
    flv_file.write_bytes(b"\x00" * 100)

    client = TestClient(create_app(tmp_path))

    with patch(
        "hometools.streaming.core.remux.remux_stream",
        return_value=iter([b"fakemp4data"]),
    ) as mock_remux:
        response = client.get("/video/stream?path=TestFolder%2Fclip.flv")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    mock_remux.assert_called_once()


def test_video_stream_serves_mp4_directly(tmp_path: Path) -> None:
    """The /video/stream endpoint uses FileResponse for fast-start .mp4 files."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    sub = tmp_path / "TestFolder"
    sub.mkdir()
    mp4_file = sub / "clip.mp4"
    # Write a fake MP4 with moov before mdat (fast-start)
    mp4_file.write_bytes(_make_mp4_atoms(b"ftyp", b"moov", b"mdat"))

    client = TestClient(create_app(tmp_path))

    with patch(
        "hometools.streaming.core.remux.remux_stream",
    ) as mock_remux:
        response = client.get("/video/stream?path=TestFolder%2Fclip.mp4")

    assert response.status_code == 200
    mock_remux.assert_not_called()


def test_video_stream_remuxes_non_faststart_mp4(tmp_path: Path) -> None:
    """The /video/stream endpoint falls back to remux when faststart cache fails
    (e.g. ffmpeg not available in test environment)."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    sub = tmp_path / "TestFolder"
    sub.mkdir()
    mp4_file = sub / "slow.mp4"
    # Write a fake MP4 with mdat before moov (NOT fast-start)
    mp4_file.write_bytes(_make_mp4_atoms(b"ftyp", b"mdat", b"moov"))

    client = TestClient(create_app(tmp_path))

    with (
        patch(
            "hometools.streaming.core.remux.ensure_faststart_cache",
            return_value=None,  # simulate ffmpeg not available
        ),
        patch(
            "hometools.streaming.core.remux.remux_stream",
            return_value=iter([b"fakemp4data"]),
        ) as mock_remux,
    ):
        response = client.get("/video/stream?path=TestFolder%2Fslow.mp4")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    mock_remux.assert_called_once()


def test_video_stream_serves_faststart_cache_for_non_faststart_mp4(tmp_path: Path) -> None:
    """When ensure_faststart_cache succeeds, /video/stream returns the cached file
    via FileResponse (which supports HTTP Range requests — required for iOS Safari)."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    sub = tmp_path / "TestFolder"
    sub.mkdir()
    mp4_file = sub / "slow.mp4"
    mp4_file.write_bytes(_make_mp4_atoms(b"ftyp", b"mdat", b"moov"))

    # Create a fake faststart cache file
    cache_dir = tmp_path / ".hometools-cache"
    cached_file = cache_dir / "video" / "TestFolder" / "slow.mp4.faststart.mp4"
    cached_file.parent.mkdir(parents=True, exist_ok=True)
    cached_file.write_bytes(b"faststart_mp4_data")

    client = TestClient(create_app(tmp_path))

    with patch(
        "hometools.streaming.core.remux.ensure_faststart_cache",
        return_value=cached_file,
    ) as mock_cache:
        response = client.get("/video/stream?path=TestFolder%2Fslow.mp4")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    mock_cache.assert_called_once()


def test_get_faststart_cache_path(tmp_path: Path) -> None:
    """get_faststart_cache_path returns the correct shadow-cache path."""
    result = get_faststart_cache_path(tmp_path, "Series/ep01.mp4")
    assert result == tmp_path / "video" / "Series" / "ep01.mp4.faststart.mp4"


def test_ensure_faststart_cache_no_ffmpeg(tmp_path: Path) -> None:
    """ensure_faststart_cache returns None gracefully when ffmpeg is missing."""
    mp4 = tmp_path / "test.mp4"
    mp4.write_bytes(b"fake")
    with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
        result = ensure_faststart_cache(mp4, tmp_path / "cache", "test.mp4")
    assert result is None


def test_ensure_faststart_cache_hit(tmp_path: Path) -> None:
    """ensure_faststart_cache returns cached path without calling ffmpeg on a cache hit."""
    import time

    mp4 = tmp_path / "test.mp4"
    mp4.write_bytes(b"fake")

    cache_path = get_faststart_cache_path(tmp_path / "cache", "test.mp4")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(b"cached_faststart")
    # Make the cache newer than the source
    time.sleep(0.01)
    future_mtime = mp4.stat().st_mtime + 10
    import os

    os.utime(cache_path, (future_mtime, future_mtime))

    with patch("subprocess.run") as mock_run:
        result = ensure_faststart_cache(mp4, tmp_path / "cache", "test.mp4")

    assert result == cache_path
    mock_run.assert_not_called()  # ffmpeg must NOT be called on cache hit


# ---------------------------------------------------------------------------
# Cached remux / transcode (Range-capable mobile playback for .avi/.mkv)
# ---------------------------------------------------------------------------


class TestRemuxCache:
    def test_cache_path_layout(self):
        p = get_remux_cache_path(Path("/cache"), "Series/ep01.avi")
        assert p == Path("/cache/video/Series/ep01.avi.remux.mp4")

    def test_cache_hit_skips_ffmpeg(self, tmp_path):
        import os
        import time

        src = tmp_path / "ep.avi"
        src.write_bytes(b"avi")
        cache_path = get_remux_cache_path(tmp_path / "cache", "ep.avi")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"mp4")
        time.sleep(0.01)
        future = src.stat().st_mtime + 10
        os.utime(cache_path, (future, future))

        with patch("subprocess.run") as mock_run:
            result = ensure_remux_cache(src, tmp_path / "cache", "ep.avi", copy=True)

        assert result == cache_path
        mock_run.assert_not_called()

    def test_transcode_invoked_on_miss(self, tmp_path):
        src = tmp_path / "ep.avi"
        src.write_bytes(b"avi")

        def fake_run(cmd, **kwargs):
            # Simulate ffmpeg writing the output file then succeeding.
            out = cmd[-1]
            Path(out).write_bytes(b"transcoded")
            return MagicMock(returncode=0, stderr=b"")

        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            result = ensure_remux_cache(src, tmp_path / "cache", "ep.avi", copy=False)

        assert result == get_remux_cache_path(tmp_path / "cache", "ep.avi")
        assert result.exists()
        # transcode args must include libx264 + faststart
        called_cmd = mock_run.call_args[0][0]
        assert "libx264" in called_cmd
        assert "+faststart" in called_cmd

    def test_ffmpeg_failure_returns_none(self, tmp_path):
        src = tmp_path / "ep.avi"
        src.write_bytes(b"avi")
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr=b"boom")):
            result = ensure_remux_cache(src, tmp_path / "cache", "ep.avi", copy=True)
        assert result is None
