"""Tests for the BPM streaming-server endpoints (audio only).

Covers `/api/audio/bpm/calculate` (with octave-hint bias), the new
`/api/audio/bpm/adjust` (slower/faster) and `/api/audio/bpm/set` (manual
entry) endpoints — see docs/architecture.md → "Metric Pill Architecture"
and `streaming/core/bpm_hints.py`.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from hometools.streaming.audio.server import create_app
from hometools.streaming.core.bpm_hints import get_octave_multiplier


def _make_client(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    audio_file = lib / "Artist - Song.mp3"
    audio_file.write_bytes(b"\x00" * 128)
    cache_dir = tmp_path / "cache"
    audit_dir = tmp_path / "audit"
    return TestClient(create_app(library_dir=lib, cache_dir=cache_dir, audit_dir=audit_dir)), cache_dir


# ---------------------------------------------------------------------------
# /api/audio/bpm/calculate
# ---------------------------------------------------------------------------


def test_bpm_calculate_returns_404_for_missing_file(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/calculate", json={"path": "ghost.mp3"})
    assert resp.status_code == 404


def test_bpm_calculate_requires_path(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/calculate", json={})
    assert resp.status_code == 400


def test_bpm_calculate_returns_error_when_analysis_unavailable(tmp_path):
    client, _ = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=0.0),
        patch("hometools.audio.bpm.calculate_bpm", return_value=None),
    ):
        resp = client.post("/api/audio/bpm/calculate", json={"path": "Artist - Song.mp3"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "error" in data


def test_bpm_calculate_saves_rounded_estimate(tmp_path):
    client, _ = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=0.0),
        patch("hometools.audio.bpm.calculate_bpm", return_value=127.6),
        patch("hometools.audio.metadata.set_bpm", return_value=True) as mock_set,
    ):
        resp = client.post("/api/audio/bpm/calculate", json={"path": "Artist - Song.mp3"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["bpm"] == 128.0
    assert data["entry_id"]
    mock_set.assert_called_once()


def test_bpm_calculate_applies_stored_octave_hint(tmp_path):
    """A previous 'schneller' adjustment must bias the next recalculation."""
    client, cache_dir = _make_client(tmp_path)
    from hometools.streaming.core.bpm_hints import adjust_octave_multiplier

    adjust_octave_multiplier(cache_dir, "audio", "Artist - Song.mp3", 2.0)

    with (
        patch("hometools.audio.metadata.get_bpm", return_value=0.0),
        patch("hometools.audio.bpm.calculate_bpm", return_value=85.0),
        patch("hometools.audio.metadata.set_bpm", return_value=True) as mock_set,
    ):
        resp = client.post("/api/audio/bpm/calculate", json={"path": "Artist - Song.mp3"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["bpm"] == 170.0  # 85 * 2.0 multiplier
    mock_set.assert_called_once_with(mock_set.call_args[0][0], 170.0)


def test_bpm_calculate_returns_error_when_save_fails(tmp_path):
    client, _ = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=0.0),
        patch("hometools.audio.bpm.calculate_bpm", return_value=127.6),
        patch("hometools.audio.metadata.set_bpm", return_value=False),
    ):
        resp = client.post("/api/audio/bpm/calculate", json={"path": "Artist - Song.mp3"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


# ---------------------------------------------------------------------------
# /api/audio/bpm/adjust
# ---------------------------------------------------------------------------


def test_bpm_adjust_requires_path(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/adjust", json={"factor": 2.0})
    assert resp.status_code == 400


def test_bpm_adjust_rejects_invalid_factor(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 3.0})
    assert resp.status_code == 400


def test_bpm_adjust_returns_404_for_missing_file(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/adjust", json={"path": "ghost.mp3", "factor": 2.0})
    assert resp.status_code == 404


def test_bpm_adjust_errors_when_no_existing_bpm(tmp_path):
    client, _ = _make_client(tmp_path)
    with patch("hometools.audio.metadata.get_bpm", return_value=0.0):
        resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 2.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "error" in data


def test_bpm_adjust_doubles_value_and_stores_hint(tmp_path):
    client, cache_dir = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=85.0),
        patch("hometools.audio.metadata.set_bpm", return_value=True) as mock_set,
    ):
        resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 2.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["bpm"] == 170.0
    mock_set.assert_called_once_with(mock_set.call_args[0][0], 170.0)
    assert get_octave_multiplier(cache_dir, "audio", "Artist - Song.mp3") == 2.0


def test_bpm_adjust_halves_value(tmp_path):
    client, cache_dir = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=170.0),
        patch("hometools.audio.metadata.set_bpm", return_value=True),
    ):
        resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 0.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["bpm"] == 85.0
    assert get_octave_multiplier(cache_dir, "audio", "Artist - Song.mp3") == 0.5


def test_bpm_adjust_rejects_result_outside_sane_range(tmp_path):
    client, _ = _make_client(tmp_path)
    with patch("hometools.audio.metadata.get_bpm", return_value=1.0):
        resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 0.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False


def test_bpm_adjust_returns_error_when_save_fails(tmp_path):
    client, _ = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=85.0),
        patch("hometools.audio.metadata.set_bpm", return_value=False),
    ):
        resp = client.post("/api/audio/bpm/adjust", json={"path": "Artist - Song.mp3", "factor": 2.0})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


# ---------------------------------------------------------------------------
# /api/audio/bpm/set
# ---------------------------------------------------------------------------


def test_bpm_set_requires_path(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/set", json={"bpm": 128})
    assert resp.status_code == 400


def test_bpm_set_returns_404_for_missing_file(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/set", json={"path": "ghost.mp3", "bpm": 128})
    assert resp.status_code == 404


def test_bpm_set_rejects_out_of_range_value(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/set", json={"path": "Artist - Song.mp3", "bpm": 500})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_bpm_set_rejects_zero_or_negative_value(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/audio/bpm/set", json={"path": "Artist - Song.mp3", "bpm": 0})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_bpm_set_saves_manual_value(tmp_path):
    client, cache_dir = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=85.0),
        patch("hometools.audio.metadata.set_bpm", return_value=True) as mock_set,
    ):
        resp = client.post("/api/audio/bpm/set", json={"path": "Artist - Song.mp3", "bpm": 174})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["bpm"] == 174.0
    mock_set.assert_called_once_with(mock_set.call_args[0][0], 174.0)
    # Manual entry must not touch the octave-correction hint.
    assert get_octave_multiplier(cache_dir, "audio", "Artist - Song.mp3") == 1.0


def test_bpm_set_returns_error_when_save_fails(tmp_path):
    client, _ = _make_client(tmp_path)
    with (
        patch("hometools.audio.metadata.get_bpm", return_value=0.0),
        patch("hometools.audio.metadata.set_bpm", return_value=False),
    ):
        resp = client.post("/api/audio/bpm/set", json={"path": "Artist - Song.mp3", "bpm": 128})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
