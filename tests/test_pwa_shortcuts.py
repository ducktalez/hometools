"""Tests for PWA shortcuts — deep linking, shortcuts API, manifest generation."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Core shortcuts module
# ---------------------------------------------------------------------------


class TestShortcutsCore:
    """Tests for the shortcuts persistence module."""

    def test_load_empty(self, tmp_path):
        from hometools.streaming.core.shortcuts import load_shortcuts

        result = load_shortcuts(tmp_path, "audio")
        assert result == []

    def test_save_and_load(self, tmp_path):
        from hometools.streaming.core.shortcuts import load_shortcuts, save_shortcut

        save_shortcut(tmp_path, "audio", item_id="a/b.mp3", title="Song B", url="/?id=a/b.mp3")
        shortcuts = load_shortcuts(tmp_path, "audio")
        assert len(shortcuts) == 1
        assert shortcuts[0]["id"] == "a/b.mp3"
        assert shortcuts[0]["title"] == "Song B"

    def test_save_deduplicates(self, tmp_path):
        from hometools.streaming.core.shortcuts import load_shortcuts, save_shortcut

        save_shortcut(tmp_path, "video", item_id="x.mp4", title="Movie X", url="/?id=x.mp4")
        save_shortcut(tmp_path, "video", item_id="y.mp4", title="Movie Y", url="/?id=y.mp4")
        save_shortcut(tmp_path, "video", item_id="x.mp4", title="Movie X Updated", url="/?id=x.mp4")

        shortcuts = load_shortcuts(tmp_path, "video")
        assert len(shortcuts) == 2
        assert shortcuts[0]["id"] == "x.mp4"
        assert shortcuts[0]["title"] == "Movie X Updated"
        assert shortcuts[1]["id"] == "y.mp4"

    def test_remove_shortcut(self, tmp_path):
        from hometools.streaming.core.shortcuts import load_shortcuts, remove_shortcut, save_shortcut

        save_shortcut(tmp_path, "audio", item_id="a.mp3", title="A", url="/")
        save_shortcut(tmp_path, "audio", item_id="b.mp3", title="B", url="/")

        remove_shortcut(tmp_path, "audio", "a.mp3")
        shortcuts = load_shortcuts(tmp_path, "audio")
        assert len(shortcuts) == 1
        assert shortcuts[0]["id"] == "b.mp3"

    def test_max_shortcuts_cap(self, tmp_path):
        from hometools.streaming.core.shortcuts import _MAX_SHORTCUTS, load_shortcuts, save_shortcut

        for i in range(_MAX_SHORTCUTS + 5):
            save_shortcut(tmp_path, "audio", item_id=f"song{i}.mp3", title=f"Song {i}", url=f"/?id=song{i}.mp3")

        shortcuts = load_shortcuts(tmp_path, "audio")
        assert len(shortcuts) == _MAX_SHORTCUTS
        # Most recent should be first
        assert shortcuts[0]["id"] == f"song{_MAX_SHORTCUTS + 4}.mp3"

    def test_audio_video_isolated(self, tmp_path):
        """Audio and video shortcuts are stored separately."""
        from hometools.streaming.core.shortcuts import load_shortcuts, save_shortcut

        save_shortcut(tmp_path, "audio", item_id="song.mp3", title="Song", url="/")
        save_shortcut(tmp_path, "video", item_id="movie.mp4", title="Movie", url="/")

        assert len(load_shortcuts(tmp_path, "audio")) == 1
        assert len(load_shortcuts(tmp_path, "video")) == 1
        assert load_shortcuts(tmp_path, "audio")[0]["id"] == "song.mp3"
        assert load_shortcuts(tmp_path, "video")[0]["id"] == "movie.mp4"

    def test_corrupted_file_returns_empty(self, tmp_path):
        from hometools.streaming.core.shortcuts import load_shortcuts

        path = tmp_path / "shortcuts" / "audio.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json!!!", encoding="utf-8")

        result = load_shortcuts(tmp_path, "audio")
        assert result == []


# ---------------------------------------------------------------------------
# Server API endpoints
# ---------------------------------------------------------------------------


class TestShortcutsAPI:
    """Test shortcuts endpoints on both servers."""

    def _make_clients(self, tmp_path):
        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        with patch.dict(os.environ, {"HOMETOOLS_CACHE_DIR": str(tmp_path)}):
            audio_client = TestClient(create_audio_app(tmp_path))
            video_client = TestClient(create_video_app(tmp_path))
        return audio_client, video_client

    def test_get_shortcuts_empty(self, tmp_path):
        audio, video = self._make_clients(tmp_path)

        r_a = audio.get("/api/audio/shortcuts")
        r_v = video.get("/api/video/shortcuts")

        assert r_a.status_code == 200
        assert r_v.status_code == 200
        assert r_a.json() == {"items": []}
        assert r_v.json() == {"items": []}

    def test_post_shortcut(self, tmp_path):
        audio, video = self._make_clients(tmp_path)

        r_a = audio.post("/api/audio/shortcuts", json={"id": "song.mp3", "title": "My Song"})
        assert r_a.status_code == 200
        items = r_a.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == "song.mp3"
        assert items[0]["title"] == "My Song"
        assert "url" in items[0]

        r_v = video.post("/api/video/shortcuts", json={"id": "movie.mp4", "title": "My Movie"})
        assert r_v.status_code == 200
        assert len(r_v.json()["items"]) == 1

    def test_post_shortcut_requires_id_and_title(self, tmp_path):
        audio, _ = self._make_clients(tmp_path)

        r = audio.post("/api/audio/shortcuts", json={"title": "Song"})
        assert r.status_code == 400

        r = audio.post("/api/audio/shortcuts", json={"id": "x.mp3"})
        assert r.status_code == 400

    def test_delete_shortcut(self, tmp_path):
        audio, _ = self._make_clients(tmp_path)

        audio.post("/api/audio/shortcuts", json={"id": "song.mp3", "title": "Song"})
        r = audio.delete("/api/audio/shortcuts", params={"id": "song.mp3"})
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_manifest_includes_shortcuts(self, tmp_path):
        audio, video = self._make_clients(tmp_path)

        audio.post("/api/audio/shortcuts", json={"id": "song.mp3", "title": "My Song"})
        video.post("/api/video/shortcuts", json={"id": "movie.mp4", "title": "My Movie"})

        r_a = audio.get("/manifest.json")
        r_v = video.get("/manifest.json")

        a_manifest = r_a.json()
        v_manifest = r_v.json()

        assert "shortcuts" in a_manifest
        assert len(a_manifest["shortcuts"]) == 1
        assert a_manifest["shortcuts"][0]["name"] == "My Song"
        assert "/?id=" in a_manifest["shortcuts"][0]["url"]

        assert "shortcuts" in v_manifest
        assert len(v_manifest["shortcuts"]) == 1
        assert v_manifest["shortcuts"][0]["name"] == "My Movie"

    def test_manifest_without_shortcuts_has_no_key(self, tmp_path):
        audio, _ = self._make_clients(tmp_path)

        r = audio.get("/manifest.json")
        assert "shortcuts" not in r.json()


# ---------------------------------------------------------------------------
# Deep Linking UI
# ---------------------------------------------------------------------------


class TestDeepLinking:
    """Test that the rendered HTML supports deep linking."""

    def test_html_contains_deep_link_js(self, tmp_path):
        """The generated HTML must include deep-link handling code."""
        from hometools.streaming.audio.server import render_audio_index_html

        html = render_audio_index_html([])
        assert "handleDeepLink" in html
        assert "_deepLinkId" in html

    def test_html_contains_pin_button_markup(self, tmp_path):
        """The JS must render pin buttons per track."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
        assert "track-pin-btn" in js
        assert "IC_PIN" in js
        assert "toggleFavorite" in js

    def test_deep_link_url_accepted_by_root(self, tmp_path):
        """Root endpoint must accept ?id= query parameter without error."""
        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        audio_client = TestClient(create_audio_app(tmp_path))
        video_client = TestClient(create_video_app(tmp_path))

        r_a = audio_client.get("/?id=Artist/Song.mp3")
        r_v = video_client.get("/?id=Movies/Film.mp4")

        assert r_a.status_code == 200
        assert r_v.status_code == 200


# ---------------------------------------------------------------------------
# Feature Parity
# ---------------------------------------------------------------------------


class TestShortcutsParity:
    """Both servers must have identical shortcut endpoint shapes."""

    def test_both_servers_have_shortcuts_endpoints(self, tmp_path):
        from hometools.streaming.audio.server import create_app as create_audio_app
        from hometools.streaming.video.server import create_app as create_video_app

        with patch.dict(os.environ, {"HOMETOOLS_CACHE_DIR": str(tmp_path)}):
            audio_client = TestClient(create_audio_app(tmp_path))
            video_client = TestClient(create_video_app(tmp_path))

        # GET
        r_a = audio_client.get("/api/audio/shortcuts")
        r_v = video_client.get("/api/video/shortcuts")
        assert r_a.status_code == 200
        assert r_v.status_code == 200
        assert r_a.json().keys() == r_v.json().keys()

        # POST
        r_a = audio_client.post("/api/audio/shortcuts", json={"id": "x.mp3", "title": "X"})
        r_v = video_client.post("/api/video/shortcuts", json={"id": "x.mp4", "title": "X"})
        assert r_a.status_code == 200
        assert r_v.status_code == 200
        assert r_a.json().keys() == r_v.json().keys()

        # DELETE
        r_a = audio_client.delete("/api/audio/shortcuts", params={"id": "x.mp3"})
        r_v = video_client.delete("/api/video/shortcuts", params={"id": "x.mp4"})
        assert r_a.status_code == 200
        assert r_v.status_code == 200
        assert r_a.json().keys() == r_v.json().keys()
