"""Feature parity tests — ensure audio and video servers stay in sync."""


class TestServerEndpointParity:
    """Both audio and video servers must expose identical endpoints."""

    def test_both_servers_respond_to_health(self):
        """Both /health endpoints must exist."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_app = create_audio_app()
        video_app = create_video_app()

        audio_client = TestClient(audio_app)
        video_client = TestClient(video_app)

        assert audio_client.get("/health").status_code == 200
        assert video_client.get("/health").status_code == 200

    def test_both_servers_have_manifest(self):
        """Both /manifest.json endpoints must exist."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_app = create_audio_app()
        video_app = create_video_app()

        audio_client = TestClient(audio_app)
        video_client = TestClient(video_app)

        audio_manifest = audio_client.get("/manifest.json")
        video_manifest = video_client.get("/manifest.json")

        assert audio_manifest.status_code == 200
        assert video_manifest.status_code == 200

        # Both must be valid JSON with required PWA fields
        audio_data = audio_manifest.json()
        video_data = video_manifest.json()

        for data in [audio_data, video_data]:
            assert "name" in data
            assert "display" in data
            assert "icons" in data

    def test_both_servers_have_service_worker(self):
        """Both /sw.js endpoints must exist."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_app = create_audio_app()
        video_app = create_video_app()

        audio_client = TestClient(audio_app)
        video_client = TestClient(video_app)

        assert audio_client.get("/sw.js").status_code == 200
        assert video_client.get("/sw.js").status_code == 200

    def test_both_servers_have_status_endpoint(self):
        """Both servers must expose cache/index diagnostics."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app())
        video_client = TestClient(create_video_app())

        audio_status = audio_client.get("/api/audio/status")
        video_status = video_client.get("/api/video/status")

        assert audio_status.status_code == 200
        assert video_status.status_code == 200
        assert "cache" in audio_status.json()
        assert "cache" in video_status.json()
        assert "issues" in audio_status.json()
        assert "issues" in video_status.json()
        assert "todos" in audio_status.json()
        assert "todos" in video_status.json()
        assert "items" in audio_status.json()["todos"]
        assert "items" in video_status.json()["todos"]

    def test_both_servers_have_todo_state_endpoint(self, tmp_path, monkeypatch):
        """Both servers must expose the same TODO action endpoint shape."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.core.issue_registry import record_issue
        from hometools.streaming.video.server import create_app as create_video_app

        monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
        record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        audio_todo_key = audio_client.get("/api/audio/status").json()["todos"]["items"][0]["todo_key"]
        video_todo_key = video_client.get("/api/video/status").json()["todos"]["items"][0]["todo_key"]

        audio_resp = audio_client.post("/api/audio/todos/state", json={"todo_key": audio_todo_key, "action": "acknowledge"})
        video_resp = video_client.post("/api/video/todos/state", json={"todo_key": video_todo_key, "action": "acknowledge"})

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert audio_resp.json().keys() == video_resp.json().keys()

    def test_both_servers_have_icons(self):
        """Both servers must provide icon endpoints."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_app = create_audio_app()
        video_app = create_video_app()

        audio_client = TestClient(audio_app)
        video_client = TestClient(video_app)

        icon_paths = ["/icon.svg", "/icon-192.png", "/icon-512.png"]

        for path in icon_paths:
            audio_resp = audio_client.get(path)
            video_resp = video_client.get(path)

            assert audio_resp.status_code == 200, f"Audio missing {path}"
            assert video_resp.status_code == 200, f"Video missing {path}"

    def test_both_servers_have_progress_endpoints(self, tmp_path):
        """Both servers must expose identical progress save/load endpoints."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        payload = {"relative_path": "test/file.mp4", "position_seconds": 42.0, "duration": 100.0}

        audio_post = audio_client.post("/api/audio/progress", json=payload)
        video_post = video_client.post("/api/video/progress", json=payload)
        assert audio_post.status_code == 200
        assert video_post.status_code == 200
        assert audio_post.json().keys() == video_post.json().keys()

        audio_get = audio_client.get("/api/audio/progress", params={"path": "test/file.mp4"})
        video_get = video_client.get("/api/video/progress", params={"path": "test/file.mp4"})
        assert audio_get.status_code == 200
        assert video_get.status_code == 200
        assert audio_get.json().keys() == video_get.json().keys()


class TestAPIResponseParity:
    """API responses must have consistent structure."""

    def test_catalog_api_response_structure_audio(self, tmp_path):
        """Audio API must return consistent structure."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        app = create_app(tmp_path)
        client = TestClient(app)

        response = client.get("/api/audio/tracks")
        assert response.status_code == 200

        data = response.json()
        assert "count" in data
        assert "items" in data
        assert "artists" in data
        assert "query" in data

    def test_both_home_pages_include_offline_library_ui(self, tmp_path):
        """Both shared UIs must expose the offline library controls."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        for html in (audio_html, video_html):
            assert 'id="downloaded-pill"' in html
            assert 'id="offline-library"' in html
            assert 'id="offline-download-list"' in html

    def test_both_home_pages_include_recent_sort_option(self, tmp_path):
        """Both UIs must have the 'recent' sort option in the dropdown."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        for html in (audio_html, video_html):
            assert 'value="recent"' in html

    def test_both_home_pages_include_custom_sort_option(self, tmp_path):
        """Both UIs must have the 'custom' (Liste) sort option in the dropdown."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        for html in (audio_html, video_html):
            assert 'value="custom"' in html

    def test_catalog_api_response_structure_video(self, tmp_path):
        """Video API must return consistent structure."""
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        app = create_app(tmp_path)
        client = TestClient(app)

        response = client.get("/api/video/items")
        assert response.status_code == 200

        data = response.json()
        assert "count" in data
        assert "items" in data
        assert "artists" in data
        assert "query" in data


class TestMediaItemSchema:
    """All media items must have required fields."""

    def test_audio_track_has_required_fields(self, tmp_path):
        """AudioTrack must have fields Frontend depends on."""

        from hometools.streaming.audio.catalog import build_audio_index

        # Create test file
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "test.mp3").write_bytes(b"")

        # Build index
        items = build_audio_index(lib_dir)

        if items:
            item = items[0]
            track_dict = item.to_dict()

            required_fields = {"title", "artist", "stream_url", "thumbnail_url", "media_type", "relative_path"}

            missing = required_fields - set(track_dict.keys())
            assert not missing, f"Audio track missing fields: {missing}"

    def test_video_item_has_required_fields(self, tmp_path):
        """VideoItem must have fields Frontend depends on."""
        from hometools.streaming.video.catalog import build_video_index

        # Create test file
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "test.mp4").write_bytes(b"")

        # Build index
        items = build_video_index(lib_dir)

        if items:
            item = items[0]
            video_dict = item.to_dict()

            required_fields = {"title", "artist", "stream_url", "thumbnail_url", "media_type", "relative_path"}

            missing = required_fields - set(video_dict.keys())
            assert not missing, f"Video item missing fields: {missing}"


class TestLargeThumbnailParity:
    """Both servers must support ?size=lg on the /thumb endpoint."""

    def test_both_servers_support_thumb_size_lg(self, tmp_path):
        """Both /thumb endpoints accept ?size=lg query parameter."""
        import os
        from unittest.mock import patch

        from starlette.testclient import TestClient

        from hometools.streaming.audio.server import create_app as audio_app
        from hometools.streaming.core.thumbnailer import get_thumbnail_lg_path
        from hometools.streaming.video.server import create_app as video_app

        cache_dir = tmp_path / "cache"

        # Create large thumbnails on disk
        for media_type in ("audio", "video"):
            lg_path = get_thumbnail_lg_path(cache_dir, media_type, "test.mp3" if media_type == "audio" else "test.mp4")
            lg_path.parent.mkdir(parents=True, exist_ok=True)
            lg_path.write_bytes(b"\xff\xd8fake-large-jpeg")

        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        with patch.dict(os.environ, {"HOMETOOLS_CACHE_DIR": str(cache_dir)}):
            audio = TestClient(audio_app(lib_dir))
            video = TestClient(video_app(lib_dir))

            r_a = audio.get("/thumb", params={"path": "test.mp3", "size": "lg"})
            assert r_a.status_code == 200, "Audio /thumb?size=lg should return 200"

            r_v = video.get("/thumb", params={"path": "test.mp4", "size": "lg"})
            assert r_v.status_code == 200, "Video /thumb?size=lg should return 200"


class TestPlaylistParity:
    """Both servers must expose identical playlist endpoints."""

    def test_both_servers_have_playlist_get_endpoint(self, tmp_path):
        """Both servers must have GET /api/<media>/playlists."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_resp = audio_client.get("/api/audio/playlists")
        video_resp = video_client.get("/api/video/playlists")

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert "items" in audio_resp.json()
        assert "items" in video_resp.json()

    def test_both_servers_have_playlist_create_endpoint(self, tmp_path):
        """Both servers must have POST /api/<media>/playlists."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_resp = audio_client.post("/api/audio/playlists", json={"name": "Test"})
        video_resp = video_client.post("/api/video/playlists", json={"name": "Test"})

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200
        assert "playlist" in audio_resp.json()
        assert "playlist" in video_resp.json()

    def test_both_servers_have_playlist_delete_endpoint(self, tmp_path):
        """Both servers must have DELETE /api/<media>/playlists."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        # Create then delete
        a_pl = audio_client.post("/api/audio/playlists", json={"name": "Del"}).json()["playlist"]
        v_pl = video_client.post("/api/video/playlists", json={"name": "Del"}).json()["playlist"]

        audio_resp = audio_client.delete("/api/audio/playlists", params={"id": a_pl["id"]})
        video_resp = video_client.delete("/api/video/playlists", params={"id": v_pl["id"]})

        assert audio_resp.status_code == 200
        assert video_resp.status_code == 200

    def test_both_servers_have_playlist_items_endpoints(self, tmp_path):
        """Both servers must support adding/removing items."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_pl = audio_client.post("/api/audio/playlists", json={"name": "Items"}).json()["playlist"]
        v_pl = video_client.post("/api/video/playlists", json={"name": "Items"}).json()["playlist"]

        a_add = audio_client.post("/api/audio/playlists/items", json={"playlist_id": a_pl["id"], "relative_path": "test.mp3"})
        v_add = video_client.post("/api/video/playlists/items", json={"playlist_id": v_pl["id"], "relative_path": "test.mp4"})

        assert a_add.status_code == 200
        assert v_add.status_code == 200

        a_rm = audio_client.delete("/api/audio/playlists/items", params={"playlist_id": a_pl["id"], "path": "test.mp3"})
        v_rm = video_client.delete("/api/video/playlists/items", params={"playlist_id": v_pl["id"], "path": "test.mp4"})

        assert a_rm.status_code == 200
        assert v_rm.status_code == 200

    def test_both_servers_have_playlist_move_endpoint(self, tmp_path):
        """Both servers must support PATCH /api/<media>/playlists/items for reordering."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_pl = audio_client.post("/api/audio/playlists", json={"name": "Move"}).json()["playlist"]
        v_pl = video_client.post("/api/video/playlists", json={"name": "Move"}).json()["playlist"]

        # Add two items so move has something to swap
        audio_client.post("/api/audio/playlists/items", json={"playlist_id": a_pl["id"], "relative_path": "a.mp3"})
        audio_client.post("/api/audio/playlists/items", json={"playlist_id": a_pl["id"], "relative_path": "b.mp3"})
        video_client.post("/api/video/playlists/items", json={"playlist_id": v_pl["id"], "relative_path": "a.mp4"})
        video_client.post("/api/video/playlists/items", json={"playlist_id": v_pl["id"], "relative_path": "b.mp4"})

        a_move = audio_client.patch(
            "/api/audio/playlists/items", json={"playlist_id": a_pl["id"], "relative_path": "a.mp3", "direction": "down"}
        )
        v_move = video_client.patch(
            "/api/video/playlists/items", json={"playlist_id": v_pl["id"], "relative_path": "a.mp4", "direction": "down"}
        )

        assert a_move.status_code == 200
        assert v_move.status_code == 200
        assert a_move.json()["playlist"]["items"] == ["b.mp3", "a.mp3"]
        assert v_move.json()["playlist"]["items"] == ["b.mp4", "a.mp4"]

    def test_both_servers_have_playlist_reorder_endpoint(self, tmp_path):
        """Both servers must support PUT /api/<media>/playlists/items for drag-and-drop reordering."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_pl = audio_client.post("/api/audio/playlists", json={"name": "DnD"}).json()["playlist"]
        v_pl = video_client.post("/api/video/playlists", json={"name": "DnD"}).json()["playlist"]

        for rp in ["a.mp3", "b.mp3", "c.mp3"]:
            audio_client.post("/api/audio/playlists/items", json={"playlist_id": a_pl["id"], "relative_path": rp})
        for rp in ["a.mp4", "b.mp4", "c.mp4"]:
            video_client.post("/api/video/playlists/items", json={"playlist_id": v_pl["id"], "relative_path": rp})

        a_reorder = audio_client.put(
            "/api/audio/playlists/items",
            json={"playlist_id": a_pl["id"], "relative_path": "a.mp3", "to_index": 2},
        )
        v_reorder = video_client.put(
            "/api/video/playlists/items",
            json={"playlist_id": v_pl["id"], "relative_path": "a.mp4", "to_index": 2},
        )

        assert a_reorder.status_code == 200
        assert v_reorder.status_code == 200
        assert a_reorder.json()["playlist"]["items"] == ["b.mp3", "c.mp3", "a.mp3"]
        assert v_reorder.json()["playlist"]["items"] == ["b.mp4", "c.mp4", "a.mp4"]

    def test_both_home_pages_include_playlist_ui(self, tmp_path):
        """Both UIs must have playlist elements when enabled."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        for label, html in [("audio", audio_html), ("video", video_html)]:
            # Pill and library panel removed — playlists as pseudo-folders
            assert 'id="playlist-modal-backdrop"' in html, f"{label} missing playlist-modal"
            assert "PLAYLISTS_ENABLED" in html, f"{label} missing PLAYLISTS_ENABLED JS var"
            assert (
                "playlist-folder-card" in html
                or "playlist_folder_card" in html
                or "playlist-new-card" in html
                or "PLAYLISTS_API_PATH" in html
            ), f"{label} missing playlist pseudo-folder support"


class TestPlaylistSyncParity:
    """Both servers must expose playlist version/revision endpoints."""

    def test_both_servers_have_playlists_version_endpoint(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_resp = audio_client.get("/api/audio/playlists/version")
        v_resp = video_client.get("/api/video/playlists/version")

        assert a_resp.status_code == 200
        assert v_resp.status_code == 200
        assert a_resp.json().keys() == v_resp.json().keys()
        assert "revision" in a_resp.json()

    def test_both_playlists_responses_include_revision(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_resp = audio_client.get("/api/audio/playlists")
        v_resp = video_client.get("/api/video/playlists")

        assert "revision" in a_resp.json()
        assert "revision" in v_resp.json()

    def test_both_home_pages_include_playlist_sync_js(self, tmp_path):
        """Both UIs must expose the PLAYLISTS_VERSION_PATH JS variable."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        assert "PLAYLISTS_VERSION_PATH" in audio_html
        assert "PLAYLISTS_VERSION_PATH" in video_html
        assert "_startPlaylistSync" in audio_html
        assert "_startPlaylistSync" in video_html

    def test_both_home_pages_include_sync_interval_var(self, tmp_path):
        """Both UIs must expose the _PLAYLIST_SYNC_INTERVAL JS variable."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        assert "_PLAYLIST_SYNC_INTERVAL" in audio_html
        assert "_PLAYLIST_SYNC_INTERVAL" in video_html

    def test_both_home_pages_include_optimistic_helpers(self, tmp_path):
        """Both UIs must expose _snapshotPlaylists / _restorePlaylists."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        assert "_snapshotPlaylists" in audio_html
        assert "_snapshotPlaylists" in video_html
        assert "_restorePlaylists" in audio_html
        assert "_restorePlaylists" in video_html

    def test_both_servers_insert_position_parity(self, tmp_path, monkeypatch):
        """Both servers respect HOMETOOLS_PLAYLIST_INSERT_POSITION consistently."""
        monkeypatch.setenv("HOMETOOLS_PLAYLIST_INSERT_POSITION", "top")
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        ac = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        vc = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        a_pl = ac.post("/api/audio/playlists", json={"name": "A"}).json()["playlist"]["id"]
        ac.post("/api/audio/playlists/items", json={"playlist_id": a_pl, "relative_path": "x.mp3"})
        ac.post("/api/audio/playlists/items", json={"playlist_id": a_pl, "relative_path": "y.mp3"})

        v_pl = vc.post("/api/video/playlists", json={"name": "V"}).json()["playlist"]["id"]
        vc.post("/api/video/playlists/items", json={"playlist_id": v_pl, "relative_path": "x.mp4"})
        vc.post("/api/video/playlists/items", json={"playlist_id": v_pl, "relative_path": "y.mp4"})

        a_items = next(p for p in ac.get("/api/audio/playlists").json()["items"] if p["id"] == a_pl)["items"]
        v_items = next(p for p in vc.get("/api/video/playlists").json()["items"] if p["id"] == v_pl)["items"]

        # Both should have newest at top
        assert a_items[0] == "y.mp3"
        assert v_items[0] == "y.mp4"

    def test_both_home_pages_include_min_rating_threshold(self, tmp_path):
        """Both UIs must expose the MIN_RATING_THRESHOLD JS variable."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        audio_html = audio_client.get("/").text
        video_html = video_client.get("/").text

        assert "MIN_RATING_THRESHOLD" in audio_html
        assert "MIN_RATING_THRESHOLD" in video_html


class TestQueueParity:
    """Queue (Warteschlange) must be present in both audio and video UIs."""

    def test_both_home_pages_include_queue_button(self, tmp_path):
        """Both UIs must have the queue button in the player bar."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        assert 'id="btn-queue"' in audio_html
        assert 'id="btn-queue"' in video_html

    def test_both_home_pages_include_queue_panel(self, tmp_path):
        """Both UIs must have the queue panel HTML."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        assert 'id="queue-panel"' in audio_html
        assert 'id="queue-panel"' in video_html

    def test_both_home_pages_include_queue_js(self, tmp_path):
        """Both UIs must have IC_QUEUE JS variable and queue functions."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        for html in [audio_html, video_html]:
            assert "IC_QUEUE" in html
            assert "_userQueue" in html
            assert "addToQueue" in html
            assert "dequeueNext" in html


class TestRefreshParity:
    """Refresh endpoint and button must be present in both servers."""

    def test_both_servers_have_refresh_endpoint(self, tmp_path):
        """POST /api/{audio,video}/refresh must exist in both servers."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        video_client = TestClient(create_video_app(tmp_path, cache_dir=tmp_path))

        r1 = audio_client.post("/api/audio/refresh")
        r2 = video_client.post("/api/video/refresh")

        assert r1.status_code == 200
        assert r1.json()["ok"] is True
        assert r2.status_code == 200
        assert r2.json()["ok"] is True

    def test_both_home_pages_include_refresh_button(self, tmp_path):
        """Both UIs must have the refresh button in the header."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        assert 'id="refresh-btn"' in audio_html
        assert 'id="refresh-btn"' in video_html

    def test_both_home_pages_include_refresh_js(self, tmp_path):
        """Both UIs must have the refreshCatalog JS function."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        for html in [audio_html, video_html]:
            assert "refreshCatalog" in html
            assert "IC_REFRESH" in html


class TestLazyRatingRefreshParity:
    """Lazy per-folder rating refresh is audio-only (POPM) but the JS
    infrastructure (refreshFolderRatings) is shared in server_utils.py
    and must exist in both UIs (guarded by RATING_WRITE_ENABLED)."""

    def test_audio_has_refresh_ratings_endpoint(self, tmp_path):
        """POST /api/audio/refresh-ratings must exist."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app

        client = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path))
        resp = client.post("/api/audio/refresh-ratings", json={"paths": ["x.mp3"]})
        # 200 OK (path not found → silently skipped, empty ratings)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_both_uis_include_refreshFolderRatings_js(self, tmp_path):
        """Both UIs must include the refreshFolderRatings JS function."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        video_html = TestClient(create_video_app(tmp_path, cache_dir=tmp_path)).get("/").text

        for html in [audio_html, video_html]:
            assert "refreshFolderRatings" in html

    def test_lazy_refresh_called_in_showPlaylist(self, tmp_path):
        """showPlaylist must call refreshFolderRatings for lazy rating updates."""
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app as create_audio_app

        html = TestClient(create_audio_app(tmp_path, cache_dir=tmp_path)).get("/").text
        assert "refreshFolderRatings(items)" in html
