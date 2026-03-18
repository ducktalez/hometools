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
            assert 'id="offline-btn"' in html
            assert 'id="offline-library"' in html
            assert 'id="offline-download-list"' in html

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
