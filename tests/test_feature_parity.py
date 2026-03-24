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
