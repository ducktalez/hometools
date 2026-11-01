"""Parity tests for shared routes registered via core/server_factory.py."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hometools.streaming.audio.server import create_app as create_audio_app
from hometools.streaming.video.server import create_app as create_video_app

_APPS = {"audio": create_audio_app, "video": create_video_app}


@pytest.fixture(params=["audio", "video"])
def client_and_media(request, tmp_path):
    media = request.param
    lib = tmp_path / "lib"
    lib.mkdir()
    app = _APPS[media](lib, cache_dir=tmp_path / "cache", audit_dir=tmp_path / "audit")
    return TestClient(app), media


def test_health(client_and_media):
    client, _ = client_and_media
    assert client.get("/health").json()["status"] in {"ok", "degraded"}


def test_pwa_routes(client_and_media):
    client, media = client_and_media
    assert media.capitalize() in client.get("/manifest.json").json()["short_name"]
    assert client.get("/sw.js").status_code == 200
    assert client.get("/icon.svg").status_code == 200
    assert client.get("/icon-192.png").headers["content-type"] == "image/png"


def test_shortcuts_roundtrip(client_and_media):
    client, media = client_and_media
    base = f"/api/{media}/shortcuts"
    assert client.get(base).json() == {"items": []}
    items = client.post(base, json={"id": "a/b", "title": "T"}).json()["items"]
    assert len(items) == 1
    assert client.delete(base, params={"id": "a/b"}).json() == {"items": []}
    assert client.post(base, json={"id": "x"}).status_code == 400


def test_playlists_roundtrip(client_and_media):
    client, media = client_and_media
    base = f"/api/{media}/playlists"
    assert client.post(base, json={"name": " "}).status_code == 400
    pl = client.post(base, json={"name": "Mix"}).json()["playlist"]
    assert client.get(base).json()["items"][0]["id"] == pl["id"]
    assert "revision" in client.get(f"{base}/version").json()
    assert client.patch(base, json={"playlist_id": "nope", "name": "x"}).status_code == 404


def test_folder_order_roundtrip(client_and_media):
    client, media = client_and_media
    base = f"/api/{media}/folder-order"
    saved = client.put(base, json={"folder_path": "F", "items": ["a", "b"]}).json()
    assert saved["items"] == ["a", "b"]
    assert client.get(base, params={"path": "F"}).json()["items"] == ["a", "b"]
    assert client.put(base, json={"items": "x"}).status_code == 400


def test_progress_roundtrip(client_and_media):
    client, media = client_and_media
    base = f"/api/{media}/progress"
    assert client.post(base, json={}).status_code == 400
    assert client.post(base, json={"relative_path": "a.mp4", "position_seconds": 5, "duration": 10}).json()["ok"]
    assert client.get(base, params={"path": "a.mp4"}).json()["items"]


def test_todo_state_validation(client_and_media):
    client, media = client_and_media
    base = f"/api/{media}/todos/state"
    assert client.post(base, json={}).status_code == 400
    assert client.post(base, json={"todo_key": "k", "action": "bogus"}).status_code == 400


def test_audit_reveal_delete_validation(client_and_media):
    client, media = client_and_media
    assert client.get(f"/api/{media}/audit").json()["total"] == 0
    assert client.post(f"/api/{media}/reveal", json={}).status_code == 400
    assert client.post(f"/api/{media}/delete-file", json={}).status_code == 400
    assert client.post(f"/api/{media}/delete-file", json={"path": "missing.mp3"}).status_code in {400, 404}


def test_items_status_refresh(client_and_media):
    client, media = client_and_media
    path = "/api/audio/tracks" if media == "audio" else "/api/video/items"
    body = client.get(path).json()
    assert "items" in body
    assert client.post(f"/api/{media}/refresh").json()["ok"] is True
    assert "library_dir" in client.get(f"/api/{media}/status").json()


def test_thumb_missing_404(client_and_media):
    client, _ = client_and_media
    assert client.get("/thumb", params={"path": "nope.mp3"}).status_code == 404
    assert client.get("/thumb", params={"path": "nope.mp3", "size": "lg"}).status_code == 404
