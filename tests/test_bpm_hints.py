"""Tests for BPM octave-correction hint storage (streaming/core/bpm_hints.py)."""

from __future__ import annotations

from hometools.streaming.core.bpm_hints import (
    adjust_octave_multiplier,
    get_octave_multiplier,
    reset_octave_multiplier,
)


def test_get_octave_multiplier_defaults_to_1(tmp_path):
    assert get_octave_multiplier(tmp_path, "audio", "Artist/Song.mp3") == 1.0


def test_get_octave_multiplier_empty_path_returns_1(tmp_path):
    assert get_octave_multiplier(tmp_path, "audio", "") == 1.0


def test_adjust_octave_multiplier_doubles_and_persists(tmp_path):
    rp = "Artist/Song.mp3"
    result = adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    assert result == 2.0
    assert get_octave_multiplier(tmp_path, "audio", rp) == 2.0


def test_adjust_octave_multiplier_accumulates(tmp_path):
    rp = "Artist/Song.mp3"
    adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    result = adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    assert result == 4.0


def test_adjust_octave_multiplier_halves(tmp_path):
    rp = "Artist/Song.mp3"
    adjust_octave_multiplier(tmp_path, "audio", rp, 0.5)
    assert get_octave_multiplier(tmp_path, "audio", rp) == 0.5


def test_adjust_octave_multiplier_clamped_to_max(tmp_path):
    rp = "Artist/Song.mp3"
    for _ in range(10):  # 2**10 = 1024x, far beyond the 16x clamp
        adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    assert get_octave_multiplier(tmp_path, "audio", rp) == 16.0


def test_adjust_octave_multiplier_clamped_to_min(tmp_path):
    rp = "Artist/Song.mp3"
    for _ in range(10):
        adjust_octave_multiplier(tmp_path, "audio", rp, 0.5)
    assert get_octave_multiplier(tmp_path, "audio", rp) == 0.0625


def test_adjust_octave_multiplier_rejects_non_positive_factor(tmp_path):
    assert adjust_octave_multiplier(tmp_path, "audio", "Artist/Song.mp3", 0) == 1.0
    assert adjust_octave_multiplier(tmp_path, "audio", "Artist/Song.mp3", -1) == 1.0


def test_adjust_octave_multiplier_empty_path_is_noop(tmp_path):
    assert adjust_octave_multiplier(tmp_path, "audio", "", 2.0) == 1.0


def test_hints_are_scoped_per_server(tmp_path):
    rp = "Artist/Song.mp3"
    adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    assert get_octave_multiplier(tmp_path, "video", rp) == 1.0


def test_hints_are_scoped_per_path(tmp_path):
    adjust_octave_multiplier(tmp_path, "audio", "Artist/A.mp3", 2.0)
    assert get_octave_multiplier(tmp_path, "audio", "Artist/B.mp3") == 1.0


def test_reset_octave_multiplier_removes_hint(tmp_path):
    rp = "Artist/Song.mp3"
    adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    assert reset_octave_multiplier(tmp_path, "audio", rp) is True
    assert get_octave_multiplier(tmp_path, "audio", rp) == 1.0


def test_reset_octave_multiplier_returns_false_when_absent(tmp_path):
    assert reset_octave_multiplier(tmp_path, "audio", "no/such.mp3") is False


def test_reset_octave_multiplier_empty_path_returns_false(tmp_path):
    assert reset_octave_multiplier(tmp_path, "audio", "") is False


def test_hints_survive_reload_from_disk(tmp_path):
    rp = "Artist/Song.mp3"
    adjust_octave_multiplier(tmp_path, "audio", rp, 2.0)
    # New "process" would just call get_octave_multiplier again — no
    # in-memory cache to reset, so this mostly documents the on-disk
    # round-trip via the same public API.
    assert get_octave_multiplier(tmp_path, "audio", rp) == 2.0
    hint_file = tmp_path / "bpm_hints" / "audio.json"
    assert hint_file.exists()


def test_read_raw_returns_empty_on_malformed_json(tmp_path):
    hint_dir = tmp_path / "bpm_hints"
    hint_dir.mkdir(parents=True)
    (hint_dir / "audio.json").write_text("not json", encoding="utf-8")
    assert get_octave_multiplier(tmp_path, "audio", "Artist/Song.mp3") == 1.0
