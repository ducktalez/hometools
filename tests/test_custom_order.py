"""Tests for server-side custom order persistence (folder + favorites reorder)."""

from pathlib import Path


class TestCustomOrderModule:
    """Unit tests for streaming.core.custom_order."""

    def test_load_empty_returns_empty_list(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order

        result = load_order(tmp_path, "audio", "some/folder")
        assert result == []

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        items = ["a.mp3", "b.mp3", "c.mp3"]
        saved = save_order(tmp_path, "audio", "Music/Rock", items)
        assert saved == items

        loaded = load_order(tmp_path, "audio", "Music/Rock")
        assert loaded == items

    def test_different_servers_are_isolated(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        save_order(tmp_path, "audio", "shared/folder", ["a.mp3"])
        save_order(tmp_path, "video", "shared/folder", ["b.mp4"])

        assert load_order(tmp_path, "audio", "shared/folder") == ["a.mp3"]
        assert load_order(tmp_path, "video", "shared/folder") == ["b.mp4"]

    def test_different_folders_are_isolated(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        save_order(tmp_path, "audio", "folder-a", ["x.mp3"])
        save_order(tmp_path, "audio", "folder-b", ["y.mp3"])

        assert load_order(tmp_path, "audio", "folder-a") == ["x.mp3"]
        assert load_order(tmp_path, "audio", "folder-b") == ["y.mp3"]

    def test_overwrite_existing_order(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        save_order(tmp_path, "audio", "f", ["a.mp3", "b.mp3"])
        save_order(tmp_path, "audio", "f", ["b.mp3", "a.mp3"])

        assert load_order(tmp_path, "audio", "f") == ["b.mp3", "a.mp3"]

    def test_delete_order(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import delete_order, load_order, save_order

        save_order(tmp_path, "audio", "f", ["a.mp3"])
        assert load_order(tmp_path, "audio", "f") == ["a.mp3"]

        ok = delete_order(tmp_path, "audio", "f")
        assert ok is True
        assert load_order(tmp_path, "audio", "f") == []

    def test_delete_nonexistent_returns_false(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import delete_order

        ok = delete_order(tmp_path, "audio", "nonexistent")
        assert ok is False

    def test_favorites_virtual_path(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        items = ["fav1.mp3", "fav2.mp3"]
        save_order(tmp_path, "audio", "__favorites__", items)
        assert load_order(tmp_path, "audio", "__favorites__") == items

    def test_max_items_clamped(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import _MAX_ITEMS, load_order, save_order

        items = [f"item-{i}.mp3" for i in range(_MAX_ITEMS + 100)]
        saved = save_order(tmp_path, "audio", "big", items)
        assert len(saved) == _MAX_ITEMS

        loaded = load_order(tmp_path, "audio", "big")
        assert len(loaded) == _MAX_ITEMS

    def test_root_folder_empty_string(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        save_order(tmp_path, "audio", "", ["root1.mp3", "root2.mp3"])
        assert load_order(tmp_path, "audio", "") == ["root1.mp3", "root2.mp3"]

    def test_corrupted_file_returns_empty(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import _order_path, load_order

        path = _order_path(tmp_path, "audio", "broken")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NOT JSON!!!", encoding="utf-8")

        result = load_order(tmp_path, "audio", "broken")
        assert result == []

    def test_order_key_is_stable(self):
        from hometools.streaming.core.custom_order import _order_key

        k1 = _order_key("Music/Rock")
        k2 = _order_key("Music/Rock")
        assert k1 == k2
        # backslash normalised to forward slash
        k3 = _order_key("Music\\Rock")
        assert k1 == k3

    def test_atomic_write_creates_directory(self, tmp_path: Path):
        from hometools.streaming.core.custom_order import load_order, save_order

        deep = tmp_path / "deep" / "nested"
        # Directory doesn't exist yet
        save_order(deep, "audio", "folder", ["a.mp3"])
        assert load_order(deep, "audio", "folder") == ["a.mp3"]


class TestCustomOrderEndpoints:
    """Integration tests for the folder-order API endpoints."""

    def test_audio_get_empty(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.get("/api/audio/folder-order", params={"path": "some/folder"})
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    def test_audio_put_and_get(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

        put_resp = client.put(
            "/api/audio/folder-order",
            json={"folder_path": "Rock", "items": ["a.mp3", "b.mp3"]},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["items"] == ["a.mp3", "b.mp3"]

        get_resp = client.get("/api/audio/folder-order", params={"path": "Rock"})
        assert get_resp.status_code == 200
        assert get_resp.json()["items"] == ["a.mp3", "b.mp3"]

    def test_audio_delete(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        client.put("/api/audio/folder-order", json={"folder_path": "f", "items": ["x.mp3"]})

        del_resp = client.delete("/api/audio/folder-order", params={"path": "f"})
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        get_resp = client.get("/api/audio/folder-order", params={"path": "f"})
        assert get_resp.json()["items"] == []

    def test_audio_put_invalid_items(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.put(
            "/api/audio/folder-order",
            json={"folder_path": "f", "items": "not-a-list"},
        )
        assert resp.status_code == 400

    def test_video_get_empty(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.get("/api/video/folder-order", params={"path": "some/folder"})
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    def test_video_put_and_get(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

        put_resp = client.put(
            "/api/video/folder-order",
            json={"folder_path": "Series/S01", "items": ["e01.mp4", "e02.mp4"]},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["items"] == ["e01.mp4", "e02.mp4"]

        get_resp = client.get("/api/video/folder-order", params={"path": "Series/S01"})
        assert get_resp.status_code == 200
        assert get_resp.json()["items"] == ["e01.mp4", "e02.mp4"]

    def test_video_delete(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        client.put("/api/video/folder-order", json={"folder_path": "f", "items": ["x.mp4"]})

        del_resp = client.delete("/api/video/folder-order", params={"path": "f"})
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

    def test_favorites_order_via_api(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))

        client.put(
            "/api/audio/folder-order",
            json={"folder_path": "__favorites__", "items": ["fav1.mp3", "fav2.mp3"]},
        )
        resp = client.get("/api/audio/folder-order", params={"path": "__favorites__"})
        assert resp.json()["items"] == ["fav1.mp3", "fav2.mp3"]


class TestCustomOrderFeatureParity:
    """Feature parity: both servers must expose identical folder-order endpoints."""

    def test_both_servers_have_folder_order_get(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_resp = audio_client.get("/api/audio/folder-order", params={"path": "f"})
        video_resp = video_client.get("/api/video/folder-order", params={"path": "f"})

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert audio_resp.json().keys() == video_resp.json().keys()

    def test_both_servers_have_folder_order_put(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        payload_a = {"folder_path": "f", "items": ["a.mp3"]}
        payload_v = {"folder_path": "f", "items": ["a.mp4"]}

        audio_resp = audio_client.put("/api/audio/folder-order", json=payload_a)
        video_resp = video_client.put("/api/video/folder-order", json=payload_v)

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert audio_resp.json().keys() == video_resp.json().keys()

    def test_both_servers_have_folder_order_delete(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_resp = audio_client.delete("/api/audio/folder-order", params={"path": "f"})
        video_resp = video_client.delete("/api/video/folder-order", params={"path": "f"})

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert audio_resp.json().keys() == video_resp.json().keys()

    def test_both_home_pages_include_folder_order_api_path(self, tmp_path: Path):
        """Both UIs must expose the FOLDER_ORDER_API_PATH JS variable."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        assert "FOLDER_ORDER_API_PATH" in audio_html
        assert "FOLDER_ORDER_API_PATH" in video_html
