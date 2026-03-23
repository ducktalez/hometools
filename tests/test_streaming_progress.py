"""Tests for the playback progress persistence module."""

from __future__ import annotations

import json
import threading

from hometools.streaming.core.progress import (
    delete_progress,
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
