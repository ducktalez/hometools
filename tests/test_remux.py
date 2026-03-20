"""Tests for the on-the-fly remux / transcode module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hometools.streaming.core.remux import (
    BROWSER_NATIVE_EXTENSIONS,
    can_copy_codecs,
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
    """The /video/stream endpoint uses FileResponse for native .mp4 files."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    sub = tmp_path / "TestFolder"
    sub.mkdir()
    mp4_file = sub / "clip.mp4"
    mp4_file.write_bytes(b"\x00" * 100)

    client = TestClient(create_app(tmp_path))

    with patch(
        "hometools.streaming.core.remux.remux_stream",
    ) as mock_remux:
        response = client.get("/video/stream?path=TestFolder%2Fclip.mp4")

    assert response.status_code == 200
    mock_remux.assert_not_called()
