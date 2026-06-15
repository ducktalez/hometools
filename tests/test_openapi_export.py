"""Tests for the ``export-openapi`` CLI command.

The exported schema is the contract source for the native clients
(Android TV, future iOS/Android). These tests lock the API surface that the
clients depend on so it cannot silently disappear.
"""

from __future__ import annotations

import argparse
import json

from hometools.cli import run_export_openapi


def _export(server: str, out_path):
    args = argparse.Namespace(server=server, output=out_path)
    rc = run_export_openapi(args)
    assert rc == 0
    return json.loads(out_path.read_text(encoding="utf-8"))


def test_export_video_schema_contains_playback_contract(tmp_path):
    schema = _export("video", tmp_path / "video.json")
    paths = schema["paths"]
    for required in (
        "/health",
        "/api/video/items",
        "/api/video/metadata",
        "/api/video/progress",
        "/api/video/continue",
        "/api/video/intro",
    ):
        assert required in paths, f"missing {required} in exported video schema"


def test_export_audio_schema_contains_core_contract(tmp_path):
    schema = _export("audio", tmp_path / "audio.json")
    paths = schema["paths"]
    assert "/health" in paths
    assert "/api/audio/tracks" in paths


def test_export_excludes_html_and_binary_routes(tmp_path):
    schema = _export("video", tmp_path / "video.json")
    paths = schema["paths"]
    # Only JSON API + /health belong in the typed contract.
    assert "/" not in paths
    assert "/video/stream" not in paths
    assert "/thumb" not in paths


def test_schema_is_valid_openapi_3(tmp_path):
    schema = _export("video", tmp_path / "video.json")
    assert schema["openapi"].startswith("3.")
    assert "info" in schema and "title" in schema["info"]


def test_live_server_serves_openapi_and_docs_in_browser(tmp_path):
    """`/openapi.json` and `/docs` must work so the API is testable in a browser."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

    schema_resp = client.get("/openapi.json")
    assert schema_resp.status_code == 200
    paths = schema_resp.json()["paths"]
    assert "/api/video/continue" in paths
    assert "/api/video/items" in paths

    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger" in docs_resp.text.lower()


def test_audio_server_serves_openapi_and_docs_in_browser(tmp_path):
    """Parity: the audio server also exposes `/openapi.json` + `/docs`."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

    schema_resp = client.get("/openapi.json")
    assert schema_resp.status_code == 200
    assert "/api/audio/tracks" in schema_resp.json()["paths"]

    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger" in docs_resp.text.lower()
