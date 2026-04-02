"""Tests for user playlists (streaming/core/playlists.py)."""

import threading

from hometools.streaming.core.playlists import (
    add_item,
    create_playlist,
    delete_playlist,
    get_playlist,
    load_playlists,
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
