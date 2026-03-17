"""Tests for Windows-safe subprocess decoding in hometools.audio.silence."""

import subprocess
from unittest.mock import patch

import pytest

pytest.importorskip("numpy")

from hometools.audio.silence import get_audio_length


def test_get_audio_length_uses_utf8_safe_subprocess(tmp_path):
    audio_file = tmp_path / "track.mp3"
    audio_file.write_bytes(b"")

    expected = subprocess.CompletedProcess(args=[], returncode=0, stdout="12.5\n", stderr="")

    with patch("hometools.audio.silence.run_text_subprocess", return_value=expected) as mocked_run:
        length = get_audio_length(audio_file)

    assert length == 12.5
    _args, kwargs = mocked_run.call_args
    assert kwargs["capture_output"] is True
