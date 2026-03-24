"""Tests for the playback progress persistence module."""

from __future__ import annotations

import json
import threading

from hometools.streaming.core.progress import (
    delete_progress,
    get_recent_progress,
    load_all_progress,
    load_progress,
    save_progress,
)


class TestSaveAndLoad:
    def test_save_and_load(self, tmp_path):
        """Save progress and load it back."""
        assert save_progress(tmp_path, "folder/song.mp3", 42.5, 180.0)
        entry = load_progress(tmp_path, "folder/song.mp3")
        assert entry is not None
        assert entry["position_seconds"] == 42.5
        assert entry["duration"] == 180.0
        assert "timestamp" in entry

    def test_load_nonexistent(self, tmp_path):
        """Loading progress for an unknown path returns None."""
        assert load_progress(tmp_path, "does/not/exist.mp3") is None

    def test_overwrite_progress(self, tmp_path):
        """Saving again overwrites the previous entry."""
        save_progress(tmp_path, "a.mp3", 10.0, 60.0)
        save_progress(tmp_path, "a.mp3", 30.0, 60.0)
        entry = load_progress(tmp_path, "a.mp3")
        assert entry is not None
        assert entry["position_seconds"] == 30.0

    def test_multiple_tracks(self, tmp_path):
        """Multiple tracks are stored independently."""
        save_progress(tmp_path, "a.mp3", 10.0, 60.0)
        save_progress(tmp_path, "b.mp4", 20.0, 120.0)
        assert load_progress(tmp_path, "a.mp3")["position_seconds"] == 10.0
        assert load_progress(tmp_path, "b.mp4")["position_seconds"] == 20.0

    def test_empty_relative_path(self, tmp_path):
        """Empty relative_path is rejected."""
        assert save_progress(tmp_path, "", 10.0) is False
        assert load_progress(tmp_path, "") is None


class TestDeleteProgress:
    def test_delete_existing(self, tmp_path):
        """Deleting an existing entry removes it."""
        save_progress(tmp_path, "a.mp3", 10.0, 60.0)
        assert delete_progress(tmp_path, "a.mp3") is True
        assert load_progress(tmp_path, "a.mp3") is None

    def test_delete_nonexistent(self, tmp_path):
        """Deleting a non-existent entry returns False."""
        assert delete_progress(tmp_path, "nope.mp3") is False

    def test_delete_empty_path(self, tmp_path):
        """Empty path is rejected."""
        assert delete_progress(tmp_path, "") is False


class TestLoadAll:
    def test_load_all_empty(self, tmp_path):
        """Empty cache returns empty dict."""
        assert load_all_progress(tmp_path) == {}

    def test_load_all_with_entries(self, tmp_path):
        """All saved entries are returned."""
        save_progress(tmp_path, "a.mp3", 10.0, 60.0)
        save_progress(tmp_path, "b.mp4", 20.0, 120.0)
        all_data = load_all_progress(tmp_path)
        assert len(all_data) == 2
        assert "a.mp3" in all_data
        assert "b.mp4" in all_data


class TestAtomicWrite:
    def test_file_is_valid_json(self, tmp_path):
        """The on-disk file must be valid JSON with version and items."""
        save_progress(tmp_path, "x.mp3", 5.0, 30.0)
        progress_file = tmp_path / "progress" / "playback_progress.json"
        assert progress_file.exists()
        data = json.loads(progress_file.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert isinstance(data["items"], dict)
        assert "x.mp3" in data["items"]


class TestThreadSafety:
    def test_concurrent_writes(self, tmp_path):
        """Concurrent saves from multiple threads must not corrupt the file."""
        errors = []

        def worker(i):
            try:
                for j in range(10):
                    save_progress(tmp_path, f"track_{i}_{j}.mp3", float(j), 100.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        all_data = load_all_progress(tmp_path)
        assert len(all_data) == 50  # 5 threads × 10 tracks


class TestRobustness:
    def test_corrupted_file(self, tmp_path):
        """Corrupted JSON file returns empty/None gracefully."""
        progress_dir = tmp_path / "progress"
        progress_dir.mkdir(parents=True)
        (progress_dir / "playback_progress.json").write_text("NOT JSON", encoding="utf-8")

        assert load_progress(tmp_path, "a.mp3") is None
        assert load_all_progress(tmp_path) == {}
        # Save should still work (overwrite corrupted file)
        assert save_progress(tmp_path, "a.mp3", 10.0, 60.0)
        assert load_progress(tmp_path, "a.mp3") is not None


# ---------------------------------------------------------------------------
# get_recent_progress
# ---------------------------------------------------------------------------


class TestGetRecentProgress:
    def test_empty_returns_empty_list(self, tmp_path):
        assert get_recent_progress(tmp_path) == []

    def test_returns_entries_newest_first(self, tmp_path):
        import time

        save_progress(tmp_path, "old.mp3", 10.0, 100.0)
        time.sleep(0.01)
        save_progress(tmp_path, "new.mp3", 20.0, 200.0)

        recent = get_recent_progress(tmp_path)
        assert len(recent) == 2
        assert recent[0]["relative_path"] == "new.mp3"
        assert recent[1]["relative_path"] == "old.mp3"

    def test_limit_is_respected(self, tmp_path):
        for i in range(10):
            save_progress(tmp_path, f"track{i}.mp3", float(i), 100.0)
        recent = get_recent_progress(tmp_path, limit=3)
        assert len(recent) == 3

    def test_entry_has_relative_path(self, tmp_path):
        save_progress(tmp_path, "Artist/Song.mp3", 5.0, 180.0)
        recent = get_recent_progress(tmp_path)
        assert recent[0]["relative_path"] == "Artist/Song.mp3"
        assert recent[0]["position_seconds"] == 5.0
        assert recent[0]["duration"] == 180.0

    def test_progress_pct_not_added_by_module(self, tmp_path):
        """get_recent_progress returns raw entries; progress_pct is computed by the API layer."""
        save_progress(tmp_path, "track.mp3", 50.0, 200.0)
        recent = get_recent_progress(tmp_path)
        # progress_pct is NOT a stored field — it's computed by the endpoint
        assert "progress_pct" not in recent[0]


# ---------------------------------------------------------------------------
# /api/audio/recent and /api/video/recent endpoints
# ---------------------------------------------------------------------------


def test_audio_recent_endpoint_exists():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.get("/api/audio/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_audio_recent_default_empty(tmp_path):
    """With no progress entries, /api/audio/recent returns an empty list."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.get("/api/audio/recent?limit=5")
    assert resp.status_code == 200
    # No tracks played yet → empty (catalog items won't match ghost progress)
    assert isinstance(resp.json()["items"], list)


def test_audio_recent_limit_param():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    # limit param accepted without error
    assert client.get("/api/audio/recent?limit=1").status_code == 200
    assert client.get("/api/audio/recent?limit=50").status_code == 200


def test_video_recent_endpoint_exists():
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    resp = client.get("/api/video/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


# ---------------------------------------------------------------------------
# Recently played UI section in rendered HTML
# ---------------------------------------------------------------------------


def test_recent_section_in_audio_page():
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="Test",
        emoji="🎵",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
    )
    assert 'id="recent-section"' in page
    assert 'class="recent-scroll"' in page
    assert "Zuletzt gespielt" in page


def test_recent_section_starts_hidden():
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="Test",
        emoji="🎵",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
    )
    assert 'id="recent-section" hidden' in page


def test_recent_api_path_injected_in_js():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
    assert "RECENT_API_PATH = '/api/audio/recent'" in js


def test_recent_api_path_video():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/video/items", item_noun="video")
    assert "RECENT_API_PATH = '/api/video/recent'" in js


def test_audiobook_dirs_injected_in_js():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
    assert "AUDIOBOOK_DIRS = " in js
    # Should be a JSON array
    import re

    m = re.search(r"AUDIOBOOK_DIRS = (\[.*?\]);", js)
    assert m, "AUDIOBOOK_DIRS must be a JS array literal"
    import json

    dirs = json.loads(m.group(1))
    assert isinstance(dirs, list)
    assert len(dirs) > 0


def test_load_recently_played_js_function():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
    assert "loadRecentlyPlayed" in js
    assert "RECENT_API_PATH" in js
    assert "recent-card" in js


# ---------------------------------------------------------------------------
# Audiobook config
# ---------------------------------------------------------------------------


def test_get_audiobook_dirs_returns_list():
    from hometools.config import get_audiobook_dirs

    dirs = get_audiobook_dirs()
    assert isinstance(dirs, list)
    assert len(dirs) > 0


def test_is_audiobook_folder_matches():
    from hometools.config import is_audiobook_folder

    # ASCII test cases
    assert is_audiobook_folder("Audiobooks")
    assert is_audiobook_folder("Audiobook - Krimi")
    assert is_audiobook_folder("Spoken Word Collection")
    assert not is_audiobook_folder("Musik")
    assert not is_audiobook_folder("Podcast")

    # Umlaut cases using Unicode escapes (Windows-encoding-safe in source)
    # H\u00f6rbuch = Hörbuch (u), H\u00f6rb\u00fccher = Hörbücher (ü — different prefix!)
    assert is_audiobook_folder("H\u00f6rbuch - Stephen King")  # matches Hörbuch prefix
    assert is_audiobook_folder("H\u00f6rb\u00fccher")  # matches Hörbücher prefix (ü≠u)
    assert is_audiobook_folder("H\u00f6rspiel - Krimi")  # matches Hörspiel prefix
    # Explicit dirs bypass env entirely
    assert is_audiobook_folder("MyBooks", ["MyBooks", "Audio"])
    assert not is_audiobook_folder("MyBooks", ["Audio"])


def test_feature_parity_recent_endpoints():
    """Both audio and video servers must expose /api/<media>/recent."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app as audio_app
    from hometools.streaming.video.server import create_app as video_app

    for app_factory, path in [(audio_app, "/api/audio/recent"), (video_app, "/api/video/recent")]:
        client = TestClient(app_factory())
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"
        assert "items" in resp.json()
