"""Tests for user playlists (streaming/core/playlists.py)."""

import json
import threading

from hometools.streaming.core.playlists import (
    add_item,
    create_playlist,
    delete_playlist,
    get_playlist,
    get_revision,
    load_playlists,
    load_playlists_with_revision,
    move_item,
    remove_item,
    rename_playlist,
    reorder_item,
)


class TestPlaylistsCRUD:
    """Basic CRUD operations on playlists."""

    def test_load_empty(self, tmp_path):
        """Loading from non-existent file returns empty list."""
        result = load_playlists(tmp_path, "audio")
        assert result == []

    def test_create_playlist(self, tmp_path):
        """Creating a playlist returns a dict with id, name, created, items."""
        pl = create_playlist(tmp_path, "audio", name="My Playlist")
        assert pl["name"] == "My Playlist"
        assert "id" in pl
        assert pl["items"] == []
        assert "created" in pl

    def test_create_and_load(self, tmp_path):
        """Created playlists persist on disk."""
        create_playlist(tmp_path, "audio", name="First")
        create_playlist(tmp_path, "audio", name="Second")
        loaded = load_playlists(tmp_path, "audio")
        assert len(loaded) == 2
        assert loaded[0]["name"] == "Second"  # newest first
        assert loaded[1]["name"] == "First"

    def test_delete_playlist(self, tmp_path):
        """Deleting a playlist removes it from the list."""
        pl = create_playlist(tmp_path, "audio", name="Doomed")
        remaining = delete_playlist(tmp_path, "audio", pl["id"])
        assert len(remaining) == 0

    def test_rename_playlist(self, tmp_path):
        """Renaming a playlist updates its name."""
        pl = create_playlist(tmp_path, "audio", name="Old")
        updated = rename_playlist(tmp_path, "audio", pl["id"], name="New")
        assert updated is not None
        assert updated["name"] == "New"

    def test_rename_nonexistent(self, tmp_path):
        """Renaming a non-existent playlist returns None."""
        result = rename_playlist(tmp_path, "audio", "nope", name="X")
        assert result is None

    def test_get_playlist(self, tmp_path):
        """Getting a single playlist by id works."""
        pl = create_playlist(tmp_path, "audio", name="Target")
        found = get_playlist(tmp_path, "audio", pl["id"])
        assert found is not None
        assert found["name"] == "Target"

    def test_get_nonexistent(self, tmp_path):
        """Getting a non-existent playlist returns None."""
        assert get_playlist(tmp_path, "audio", "nope") is None

    def test_max_playlists_cap(self, tmp_path):
        """Creating more than max playlists caps the list."""
        for i in range(55):
            create_playlist(tmp_path, "audio", name=f"PL{i}")
        loaded = load_playlists(tmp_path, "audio")
        assert len(loaded) <= 50

    def test_empty_name_defaults(self, tmp_path):
        """Empty name defaults to 'Playlist'."""
        pl = create_playlist(tmp_path, "audio", name="")
        assert pl["name"] == "Playlist"


class TestPlaylistItems:
    """Adding/removing items from playlists."""

    def test_add_item(self, tmp_path):
        """Adding an item to a playlist."""
        pl = create_playlist(tmp_path, "audio", name="Favorites")
        updated = add_item(tmp_path, "audio", pl["id"], relative_path="artist/song.mp3")
        assert updated is not None
        assert "artist/song.mp3" in updated["items"]

    def test_add_duplicate_ignored(self, tmp_path):
        """Adding the same item twice is silently ignored."""
        pl = create_playlist(tmp_path, "audio", name="Test")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        updated = add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert updated is not None
        assert updated["items"].count("a.mp3") == 1

    def test_remove_item(self, tmp_path):
        """Removing an item from a playlist."""
        pl = create_playlist(tmp_path, "audio", name="Test")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        updated = remove_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert updated is not None
        assert "a.mp3" not in updated["items"]

    def test_add_to_nonexistent_playlist(self, tmp_path):
        """Adding to a non-existent playlist returns None."""
        result = add_item(tmp_path, "audio", "nope", relative_path="a.mp3")
        assert result is None

    def test_remove_from_nonexistent_playlist(self, tmp_path):
        """Removing from a non-existent playlist returns None."""
        result = remove_item(tmp_path, "audio", "nope", relative_path="a.mp3")
        assert result is None

    def test_max_items_cap(self, tmp_path):
        """Adding more than max items stops silently."""
        pl = create_playlist(tmp_path, "audio", name="Big")
        for i in range(505):
            add_item(tmp_path, "audio", pl["id"], relative_path=f"song{i}.mp3")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded is not None
        assert len(loaded["items"]) <= 500


class TestPlaylistIsolation:
    """Audio and video playlists are separate."""

    def test_server_isolation(self, tmp_path):
        """Audio and video playlists don't interfere."""
        create_playlist(tmp_path, "audio", name="Audio PL")
        create_playlist(tmp_path, "video", name="Video PL")
        audio = load_playlists(tmp_path, "audio")
        video = load_playlists(tmp_path, "video")
        assert len(audio) == 1
        assert len(video) == 1
        assert audio[0]["name"] == "Audio PL"
        assert video[0]["name"] == "Video PL"


class TestPlaylistThreadSafety:
    """Concurrent access doesn't corrupt data."""

    def test_concurrent_creates(self, tmp_path):
        """Multiple threads creating playlists concurrently."""
        errors = []

        def worker(n):
            try:
                create_playlist(tmp_path, "audio", name=f"Thread-{n}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        loaded = load_playlists(tmp_path, "audio")
        assert len(loaded) == 20


class TestPlaylistCorruption:
    """Handling corrupted or unexpected data."""

    def test_corrupted_json(self, tmp_path):
        """Corrupted JSON file returns empty list."""
        pl_dir = tmp_path / "playlists"
        pl_dir.mkdir()
        (pl_dir / "audio.json").write_text("NOT JSON", encoding="utf-8")
        result = load_playlists(tmp_path, "audio")
        assert result == []

    def test_non_list_json(self, tmp_path):
        """JSON that is not a list returns empty list."""
        pl_dir = tmp_path / "playlists"
        pl_dir.mkdir()
        (pl_dir / "audio.json").write_text('{"foo": "bar"}', encoding="utf-8")
        result = load_playlists(tmp_path, "audio")
        assert result == []


class TestPlaylistReorder:
    """Moving items up/down within a playlist."""

    def _make_playlist(self, tmp_path, items):
        """Helper: create a playlist with given items."""
        pl = create_playlist(tmp_path, "audio", name="Reorder")
        for rp in items:
            add_item(tmp_path, "audio", pl["id"], relative_path=rp)
        return pl

    def test_move_item_down(self, tmp_path):
        """Moving an item down swaps it with the next."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = move_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", direction="down")
        assert updated is not None
        assert updated["items"] == ["b.mp3", "a.mp3", "c.mp3"]

    def test_move_item_up(self, tmp_path):
        """Moving an item up swaps it with the previous."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = move_item(tmp_path, "audio", pl["id"], relative_path="c.mp3", direction="up")
        assert updated is not None
        assert updated["items"] == ["a.mp3", "c.mp3", "b.mp3"]

    def test_move_first_item_up_noop(self, tmp_path):
        """Moving the first item up keeps the list unchanged."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3"])
        updated = move_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", direction="up")
        assert updated is not None
        assert updated["items"] == ["a.mp3", "b.mp3"]

    def test_move_last_item_down_noop(self, tmp_path):
        """Moving the last item down keeps the list unchanged."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3"])
        updated = move_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", direction="down")
        assert updated is not None
        assert updated["items"] == ["a.mp3", "b.mp3"]

    def test_move_nonexistent_item(self, tmp_path):
        """Moving a non-existent item returns None."""
        pl = self._make_playlist(tmp_path, ["a.mp3"])
        result = move_item(tmp_path, "audio", pl["id"], relative_path="nope.mp3", direction="up")
        assert result is None

    def test_move_in_nonexistent_playlist(self, tmp_path):
        """Moving in a non-existent playlist returns None."""
        result = move_item(tmp_path, "audio", "nope", relative_path="a.mp3", direction="up")
        assert result is None

    def test_invalid_direction(self, tmp_path):
        """Invalid direction returns None."""
        pl = self._make_playlist(tmp_path, ["a.mp3"])
        result = move_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", direction="left")
        assert result is None

    def test_move_persists(self, tmp_path):
        """Move is persisted to disk."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        move_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", direction="down")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded is not None
        assert loaded["items"] == ["b.mp3", "a.mp3", "c.mp3"]


class TestPlaylistReorderToIndex:
    """Reorder items to a specific index (drag-and-drop backend)."""

    def _make_playlist(self, tmp_path, items):
        pl = create_playlist(tmp_path, "audio", name="DnD")
        for rp in items:
            add_item(tmp_path, "audio", pl["id"], relative_path=rp)
        return pl

    def test_move_to_end(self, tmp_path):
        """Move first item to the end."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", to_index=2)
        assert updated is not None
        assert updated["items"] == ["b.mp3", "c.mp3", "a.mp3"]

    def test_move_to_start(self, tmp_path):
        """Move last item to the start."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="c.mp3", to_index=0)
        assert updated is not None
        assert updated["items"] == ["c.mp3", "a.mp3", "b.mp3"]

    def test_move_to_middle(self, tmp_path):
        """Move first item to the middle."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3", "d.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", to_index=2)
        assert updated is not None
        assert updated["items"] == ["b.mp3", "c.mp3", "a.mp3", "d.mp3"]

    def test_same_index_noop(self, tmp_path):
        """Moving to the same index is a no-op."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", to_index=1)
        assert updated is not None
        assert updated["items"] == ["a.mp3", "b.mp3", "c.mp3"]

    def test_index_clamped_high(self, tmp_path):
        """Index beyond list length is clamped to last position."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", to_index=99)
        assert updated is not None
        assert updated["items"] == ["b.mp3", "c.mp3", "a.mp3"]

    def test_index_clamped_low(self, tmp_path):
        """Negative index is clamped to 0."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="c.mp3", to_index=-5)
        assert updated is not None
        assert updated["items"] == ["c.mp3", "a.mp3", "b.mp3"]

    def test_nonexistent_item(self, tmp_path):
        """Moving a non-existent item returns None."""
        pl = self._make_playlist(tmp_path, ["a.mp3"])
        result = reorder_item(tmp_path, "audio", pl["id"], relative_path="nope.mp3", to_index=0)
        assert result is None

    def test_nonexistent_playlist(self, tmp_path):
        """Moving in a non-existent playlist returns None."""
        result = reorder_item(tmp_path, "audio", "nope", relative_path="a.mp3", to_index=0)
        assert result is None

    def test_reorder_persists(self, tmp_path):
        """Reorder is persisted to disk."""
        pl = self._make_playlist(tmp_path, ["a.mp3", "b.mp3", "c.mp3"])
        reorder_item(tmp_path, "audio", pl["id"], relative_path="c.mp3", to_index=0)
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded is not None
        assert loaded["items"] == ["c.mp3", "a.mp3", "b.mp3"]


class TestRevisionTracking:
    """Tests for the revision counter introduced in Sprint 4."""

    def test_initial_revision_is_zero(self, tmp_path):
        """Empty storage has revision 0."""
        assert get_revision(tmp_path, "audio") == 0

    def test_create_increments_revision(self, tmp_path):
        """Creating a playlist bumps revision by 1."""
        create_playlist(tmp_path, "audio", name="A")
        assert get_revision(tmp_path, "audio") == 1
        create_playlist(tmp_path, "audio", name="B")
        assert get_revision(tmp_path, "audio") == 2

    def test_delete_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        rev_after_create = get_revision(tmp_path, "audio")
        delete_playlist(tmp_path, "audio", pl["id"])
        assert get_revision(tmp_path, "audio") == rev_after_create + 1

    def test_rename_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        rev = get_revision(tmp_path, "audio")
        rename_playlist(tmp_path, "audio", pl["id"], name="Y")
        assert get_revision(tmp_path, "audio") == rev + 1

    def test_add_item_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        rev = get_revision(tmp_path, "audio")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert get_revision(tmp_path, "audio") == rev + 1

    def test_remove_item_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        rev = get_revision(tmp_path, "audio")
        remove_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert get_revision(tmp_path, "audio") == rev + 1

    def test_move_item_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        add_item(tmp_path, "audio", pl["id"], relative_path="b.mp3")
        rev = get_revision(tmp_path, "audio")
        move_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", direction="up")
        assert get_revision(tmp_path, "audio") == rev + 1

    def test_reorder_item_increments_revision(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        add_item(tmp_path, "audio", pl["id"], relative_path="b.mp3")
        rev = get_revision(tmp_path, "audio")
        reorder_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", to_index=0)
        assert get_revision(tmp_path, "audio") == rev + 1

    def test_load_playlists_with_revision(self, tmp_path):
        """load_playlists_with_revision returns both playlists and revision."""
        create_playlist(tmp_path, "audio", name="A")
        create_playlist(tmp_path, "audio", name="B")
        playlists, rev = load_playlists_with_revision(tmp_path, "audio")
        assert len(playlists) == 2
        assert rev == 2

    def test_revision_per_server(self, tmp_path):
        """Audio and video revisions are independent."""
        create_playlist(tmp_path, "audio", name="A1")
        create_playlist(tmp_path, "audio", name="A2")
        create_playlist(tmp_path, "video", name="V1")
        assert get_revision(tmp_path, "audio") == 2
        assert get_revision(tmp_path, "video") == 1


class TestUpdatedAt:
    """Tests for the updated_at timestamp field."""

    def test_create_has_updated_at(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        assert "updated_at" in pl
        assert pl["updated_at"] == pl["created"]

    def test_rename_updates_updated_at(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        old_ts = pl["updated_at"]
        renamed = rename_playlist(tmp_path, "audio", pl["id"], name="Y")
        assert renamed["updated_at"] >= old_ts

    def test_add_item_updates_updated_at(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        old_ts = pl["updated_at"]
        updated = add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert updated["updated_at"] >= old_ts

    def test_remove_item_updates_updated_at(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        old_ts = loaded["updated_at"]
        updated = remove_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        assert updated["updated_at"] >= old_ts

    def test_reorder_updates_updated_at(self, tmp_path):
        pl = create_playlist(tmp_path, "audio", name="X")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        add_item(tmp_path, "audio", pl["id"], relative_path="b.mp3")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        old_ts = loaded["updated_at"]
        updated = reorder_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", to_index=0)
        assert updated["updated_at"] >= old_ts


class TestPlaylistChangelog:
    """Tests for the changelog JSONL feature."""

    def test_changelog_created_on_mutation(self, tmp_path):
        from hometools.streaming.core.playlists import _changelog_path

        create_playlist(tmp_path, "audio", name="Test")
        path = _changelog_path(tmp_path, "audio")
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["action"] == "create"
        assert "timestamp" in entry

    def test_changelog_grows_with_mutations(self, tmp_path):
        from hometools.streaming.core.playlists import _changelog_path

        pl = create_playlist(tmp_path, "audio", name="Test")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        remove_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        rename_playlist(tmp_path, "audio", pl["id"], name="New")
        delete_playlist(tmp_path, "audio", pl["id"])

        path = _changelog_path(tmp_path, "audio")
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5
        actions = [json.loads(line)["action"] for line in lines]
        assert actions == ["create", "add_item", "remove_item", "rename", "delete"]

    def test_changelog_servers_isolated(self, tmp_path):
        from hometools.streaming.core.playlists import _changelog_path

        create_playlist(tmp_path, "audio", name="A")
        create_playlist(tmp_path, "video", name="V")

        audio_path = _changelog_path(tmp_path, "audio")
        video_path = _changelog_path(tmp_path, "video")
        assert audio_path.exists()
        assert video_path.exists()
        assert audio_path != video_path


class TestBackwardCompatibility:
    """Tests for v1 → v2 storage format migration."""

    def test_legacy_bare_array_is_read(self, tmp_path):
        """v1 format (bare JSON array) is transparently read."""
        from hometools.streaming.core.playlists import _playlists_path

        path = _playlists_path(tmp_path, "audio")
        path.parent.mkdir(parents=True, exist_ok=True)
        legacy = [{"id": "abc123", "name": "Old", "created": "2025-01-01T00:00:00Z", "items": ["x.mp3"]}]
        path.write_text(json.dumps(legacy), encoding="utf-8")

        loaded = load_playlists(tmp_path, "audio")
        assert len(loaded) == 1
        assert loaded[0]["name"] == "Old"

    def test_legacy_revision_is_zero(self, tmp_path):
        """v1 format has revision 0."""
        from hometools.streaming.core.playlists import _playlists_path

        path = _playlists_path(tmp_path, "audio")
        path.parent.mkdir(parents=True, exist_ok=True)
        legacy = [{"id": "abc123", "name": "Old", "created": "2025-01-01T00:00:00Z", "items": []}]
        path.write_text(json.dumps(legacy), encoding="utf-8")

        assert get_revision(tmp_path, "audio") == 0

    def test_legacy_migrates_on_write(self, tmp_path):
        """First write after reading v1 data stores v2 envelope."""
        from hometools.streaming.core.playlists import _playlists_path

        path = _playlists_path(tmp_path, "audio")
        path.parent.mkdir(parents=True, exist_ok=True)
        legacy = [{"id": "abc123", "name": "Old", "created": "2025-01-01T00:00:00Z", "items": []}]
        path.write_text(json.dumps(legacy), encoding="utf-8")

        # Trigger a write (add item bumps revision)
        add_item(tmp_path, "audio", "abc123", relative_path="new.mp3")

        # File should now be v2 envelope
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        assert "revision" in raw
        assert "playlists" in raw
        assert raw["revision"] == 1


class TestVersionEndpoint:
    """Integration tests for the /playlists/version API endpoint."""

    def test_audio_version_initial(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.get("/api/audio/playlists/version")
        assert resp.status_code == 200
        assert resp.json()["revision"] == 0

    def test_audio_version_after_create(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        client.post("/api/audio/playlists", json={"name": "Test"})
        resp = client.get("/api/audio/playlists/version")
        assert resp.json()["revision"] == 1

    def test_audio_playlists_includes_revision(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        client.post("/api/audio/playlists", json={"name": "Test"})
        resp = client.get("/api/audio/playlists")
        assert resp.status_code == 200
        data = resp.json()
        assert "revision" in data
        assert data["revision"] == 1
        assert len(data["items"]) == 1

    def test_video_version_endpoint(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.get("/api/video/playlists/version")
        assert resp.status_code == 200
        assert resp.json()["revision"] == 0

    def test_video_playlists_includes_revision(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        client.post("/api/video/playlists", json={"name": "VPL"})
        resp = client.get("/api/video/playlists")
        data = resp.json()
        assert "revision" in data
        assert data["revision"] == 1

    def test_revision_increments_across_mutations(self, tmp_path):
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        # create → rev 1
        resp = client.post("/api/audio/playlists", json={"name": "PL"})
        pl_id = resp.json()["playlist"]["id"]
        # add item → rev 2
        client.post("/api/audio/playlists/items", json={"playlist_id": pl_id, "relative_path": "a.mp3"})
        # delete → rev 3
        client.delete(f"/api/audio/playlists?id={pl_id}")

        v = client.get("/api/audio/playlists/version").json()
        assert v["revision"] == 3


class TestInsertPosition:
    """Tests for the HOMETOOLS_PLAYLIST_INSERT_POSITION config."""

    def test_add_item_bottom_default(self, tmp_path):
        """Default insert position is bottom (append)."""
        pl = create_playlist(tmp_path, "audio", name="PL")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3")
        add_item(tmp_path, "audio", pl["id"], relative_path="b.mp3")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded["items"] == ["a.mp3", "b.mp3"]

    def test_add_item_top(self, tmp_path):
        """insert_position='top' inserts at index 0."""
        pl = create_playlist(tmp_path, "audio", name="PL")
        add_item(tmp_path, "audio", pl["id"], relative_path="a.mp3", insert_position="top")
        add_item(tmp_path, "audio", pl["id"], relative_path="b.mp3", insert_position="top")
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded["items"] == ["b.mp3", "a.mp3"]

    def test_add_item_top_via_api_audio(self, tmp_path, monkeypatch):
        """Audio server respects HOMETOOLS_PLAYLIST_INSERT_POSITION=top."""
        monkeypatch.setenv("HOMETOOLS_PLAYLIST_INSERT_POSITION", "top")
        from fastapi.testclient import TestClient

        from hometools.streaming.audio.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.post("/api/audio/playlists", json={"name": "T"})
        pl_id = resp.json()["playlist"]["id"]
        client.post("/api/audio/playlists/items", json={"playlist_id": pl_id, "relative_path": "a.mp3"})
        client.post("/api/audio/playlists/items", json={"playlist_id": pl_id, "relative_path": "b.mp3"})
        resp = client.get("/api/audio/playlists")
        pl = next(p for p in resp.json()["items"] if p["id"] == pl_id)
        assert pl["items"] == ["b.mp3", "a.mp3"]

    def test_add_item_top_via_api_video(self, tmp_path, monkeypatch):
        """Video server respects HOMETOOLS_PLAYLIST_INSERT_POSITION=top."""
        monkeypatch.setenv("HOMETOOLS_PLAYLIST_INSERT_POSITION", "top")
        from fastapi.testclient import TestClient

        from hometools.streaming.video.server import create_app

        client = TestClient(create_app(tmp_path, cache_dir=tmp_path))
        resp = client.post("/api/video/playlists", json={"name": "V"})
        pl_id = resp.json()["playlist"]["id"]
        client.post("/api/video/playlists/items", json={"playlist_id": pl_id, "relative_path": "a.mp4"})
        client.post("/api/video/playlists/items", json={"playlist_id": pl_id, "relative_path": "b.mp4"})
        resp = client.get("/api/video/playlists")
        pl = next(p for p in resp.json()["items"] if p["id"] == pl_id)
        assert pl["items"] == ["b.mp4", "a.mp4"]


class TestChangelogRotation:
    """Tests for changelog JSONL rotation."""

    def test_rotation_not_triggered_below_max(self, tmp_path):
        """Changelog is not rotated when below max lines."""
        from hometools.streaming.core.playlists import _changelog_path

        pl = create_playlist(tmp_path, "audio", name="T")
        for i in range(5):
            add_item(tmp_path, "audio", pl["id"], relative_path=f"t{i}.mp3")
        path = _changelog_path(tmp_path, "audio")
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        # 1 create + 5 add_item = 6
        assert len(lines) == 6

    def test_rotation_trims_to_max_lines(self, tmp_path):
        """Changelog is trimmed to _MAX_CHANGELOG_LINES when exceeded."""
        from hometools.streaming.core.playlists import _MAX_CHANGELOG_LINES, _changelog_path, _rotate_changelog

        path = _changelog_path(tmp_path, "audio")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write more than max
        excess = _MAX_CHANGELOG_LINES + 50
        with open(path, "w", encoding="utf-8") as f:
            for i in range(excess):
                f.write(json.dumps({"i": i}) + "\n")
        _rotate_changelog(path)
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == _MAX_CHANGELOG_LINES
        # Last entry should be the most recent
        last = json.loads(lines[-1])
        assert last["i"] == excess - 1

    def test_rotation_noop_on_empty(self, tmp_path):
        """Rotation is a no-op on non-existent file."""
        from hometools.streaming.core.playlists import _changelog_path, _rotate_changelog

        path = _changelog_path(tmp_path, "audio")
        _rotate_changelog(path)  # should not raise
        assert not path.exists()
