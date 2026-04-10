"""Tests for the shared streaming core — models, catalog, sync, server_utils."""

from hometools.streaming.core.catalog import list_artists, parse_season_episode, query_items, sort_items
from hometools.streaming.core.models import MediaItem, encode_relative_path
from hometools.streaming.core.server_utils import render_media_page, resolve_media_path
from hometools.streaming.core.sync import copy_reason, plan_sync, sync_library

# ---------------------------------------------------------------------------
# MediaItem model
# ---------------------------------------------------------------------------


def test_media_item_to_dict():
    item = MediaItem("a.mp3", "Song", "Artist", "/stream?x", "audio")
    d = item.to_dict()
    assert d["title"] == "Song"
    assert d["media_type"] == "audio"


def test_encode_relative_path_escapes():
    assert "%2F" in encode_relative_path("folder/file.mp4")


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------


def test_sort_items_by_title():
    items = [
        MediaItem("b.mp3", "Zulu", "B", "u1", "audio"),
        MediaItem("a.mp3", "Alpha", "A", "u2", "audio"),
    ]
    assert [i.title for i in sort_items(items, "title")] == ["Alpha", "Zulu"]


def test_query_items_filter_and_search():
    items = [
        MediaItem("a.mp3", "One", "Daft Punk", "u1", "audio"),
        MediaItem("b.mp4", "Two", "Muse", "u2", "video"),
        MediaItem("c.mp3", "Three", "Daft Punk", "u3", "audio"),
    ]
    result = query_items(items, q="thr", artist="daft punk")
    assert len(result) == 1
    assert result[0].title == "Three"


def test_list_artists_excludes_empty():
    items = [
        MediaItem("a.mp4", "Movie", "", "u1", "video"),
        MediaItem("b.mp3", "Song", "Muse", "u2", "audio"),
    ]
    assert list_artists(items) == ["Muse"]


# ---------------------------------------------------------------------------
# Season / episode parsing
# ---------------------------------------------------------------------------


def test_parse_season_episode_standard():
    assert parse_season_episode("Breaking.Bad.S02E03.720p.mkv") == (2, 3)


def test_parse_season_episode_lowercase():
    assert parse_season_episode("show.s01e10.title.mp4") == (1, 10)


def test_parse_season_episode_large_episode():
    assert parse_season_episode("Anime S01E1034 Title.mp4") == (1, 1034)


def test_parse_season_episode_x_pattern():
    assert parse_season_episode("show.1x05.title.mp4") == (1, 5)


def test_parse_season_episode_x_pattern_two_digit_season():
    assert parse_season_episode("show.12x03.title.mkv") == (12, 3)


def test_parse_season_episode_no_match():
    assert parse_season_episode("Random Movie 2024.mp4") == (0, 0)


def test_parse_season_episode_empty_string():
    assert parse_season_episode("") == (0, 0)


def test_parse_season_episode_prefers_s_pattern_over_x():
    # When both patterns match, S##E## should win (it comes first)
    assert parse_season_episode("show.S03E04.1x02.mp4") == (3, 4)


# ---------------------------------------------------------------------------
# Series sort ordering
# ---------------------------------------------------------------------------


def test_sort_items_series_by_season_episode():
    """Series episodes in the same folder must be sorted by (season, episode)."""
    items = [
        MediaItem("s/S01E10.mp4", "Ep 10", "Show", "u1", "video", season=1, episode=10),
        MediaItem("s/S01E02.mp4", "Ep 2", "Show", "u2", "video", season=1, episode=2),
        MediaItem("s/S02E01.mp4", "Ep 1", "Show", "u3", "video", season=2, episode=1),
        MediaItem("s/S01E01.mp4", "Ep 1", "Show", "u4", "video", season=1, episode=1),
    ]
    sorted_items = sort_items(items, "artist")
    assert [(i.season, i.episode) for i in sorted_items] == [
        (1, 1),
        (1, 2),
        (1, 10),
        (2, 1),
    ]


def test_sort_items_non_series_unaffected():
    """Items without season/episode still sort by title within the same folder."""
    items = [
        MediaItem("a/Z.mp4", "Zulu", "Folder", "u1", "video"),
        MediaItem("a/A.mp4", "Alpha", "Folder", "u2", "video"),
    ]
    sorted_items = sort_items(items, "artist")
    assert [i.title for i in sorted_items] == ["Alpha", "Zulu"]


def test_sort_items_mixed_series_and_non_series():
    """Non-series items (season=0, episode=0) sort before series episodes."""
    items = [
        MediaItem("a/S01E02.mp4", "Ep 2", "Folder", "u1", "video", season=1, episode=2),
        MediaItem("a/intro.mp4", "Intro", "Folder", "u2", "video"),
        MediaItem("a/S01E01.mp4", "Ep 1", "Folder", "u3", "video", season=1, episode=1),
    ]
    sorted_items = sort_items(items, "artist")
    assert [i.title for i in sorted_items] == ["Intro", "Ep 1", "Ep 2"]


def test_sort_items_by_title_also_uses_season_episode():
    """Title sort should also use season/episode for same-title items."""
    items = [
        MediaItem("s/S01E10.mp4", "Show", "A", "u1", "video", season=1, episode=10),
        MediaItem("s/S01E02.mp4", "Show", "A", "u2", "video", season=1, episode=2),
    ]
    sorted_items = sort_items(items, "title")
    assert [(i.season, i.episode) for i in sorted_items] == [(1, 2), (1, 10)]


def test_sort_items_by_recent():
    """Recent sort orders by mtime descending (newest first)."""
    items = [
        MediaItem("a.mp3", "Old", "A", "u1", "audio", mtime=1000.0),
        MediaItem("b.mp3", "New", "B", "u2", "audio", mtime=3000.0),
        MediaItem("c.mp3", "Mid", "C", "u3", "audio", mtime=2000.0),
    ]
    sorted_items = sort_items(items, "recent")
    assert [i.title for i in sorted_items] == ["New", "Mid", "Old"]


def test_sort_items_by_recent_tiebreaker():
    """Items with same mtime sort alphabetically by title."""
    items = [
        MediaItem("a.mp3", "Zulu", "A", "u1", "audio", mtime=1000.0),
        MediaItem("b.mp3", "Alpha", "B", "u2", "audio", mtime=1000.0),
    ]
    sorted_items = sort_items(items, "recent")
    assert [i.title for i in sorted_items] == ["Alpha", "Zulu"]


def test_media_item_has_mtime_field():
    """MediaItem includes mtime in to_dict() with default 0.0."""
    item = MediaItem("a.mp3", "Song", "Artist", "/stream", "audio")
    d = item.to_dict()
    assert "mtime" in d
    assert d["mtime"] == 0.0

    item_with_mtime = MediaItem("b.mp3", "Song2", "Artist", "/stream", "audio", mtime=12345.6)
    assert item_with_mtime.mtime == 12345.6


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------


def test_plan_sync_finds_missing_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "track.mp3").write_text("data")
    (source / "ignore.txt").write_text("skip")

    ops = plan_sync(source, target, [".mp3"])
    assert len(ops) == 1
    assert ops[0].reason == "missing"


def test_sync_library_copies(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "movie.mp4").write_text("video")

    ops = sync_library(source, target, [".mp4"])
    assert len(ops) == 1
    assert (target / "movie.mp4").exists()


def test_sync_library_dry_run(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "movie.mp4").write_text("video")

    ops = sync_library(source, target, [".mp4"], dry_run=True)
    assert len(ops) == 1
    assert not (target / "movie.mp4").exists()


def test_copy_reason_detects_size_change(tmp_path):
    (tmp_path / "a.mp3").write_text("short")
    (tmp_path / "b.mp3").write_text("much longer content here")
    assert copy_reason(tmp_path / "b.mp3", tmp_path / "a.mp3") == "size-changed"


# ---------------------------------------------------------------------------
# Server utilities
# ---------------------------------------------------------------------------


def test_resolve_media_path_rejects_traversal(tmp_path):
    (tmp_path / "ok.mp3").write_text("audio")
    try:
        resolve_media_path(tmp_path, "..%2Foutside.mp3", [".mp3"])
    except ValueError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_resolve_media_path_rejects_wrong_suffix(tmp_path):
    (tmp_path / "note.txt").write_text("text")
    try:
        resolve_media_path(tmp_path, "note.txt", [".mp3"])
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_render_media_page_contains_expected_elements():
    page = render_media_page(
        title="Test",
        emoji="🎵",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        item_noun="item",
    )
    assert "<audio" in page
    assert "🎵" in page
    assert 'id="folder-grid"' in page
    assert 'id="play-all-btn"' in page
    assert "item" in page


def test_media_item_has_thumbnail_lg_url_field():
    """MediaItem supports thumbnail_lg_url field with empty default."""
    item = MediaItem(
        relative_path="a.mp4",
        title="A",
        artist="X",
        stream_url="/stream",
        media_type="video",
    )
    assert item.thumbnail_lg_url == ""

    item2 = MediaItem(
        relative_path="a.mp4",
        title="A",
        artist="X",
        stream_url="/stream",
        media_type="video",
        thumbnail_lg_url="/thumb?path=a.mp4&size=lg",
    )
    assert item2.thumbnail_lg_url == "/thumb?path=a.mp4&size=lg"
    assert "thumbnail_lg_url" in item2.to_dict()


# ---------------------------------------------------------------------------
# IndexCache.patch_items
# ---------------------------------------------------------------------------


class TestIndexCachePatchItems:
    """Tests for the lazy per-item patch method on IndexCache."""

    def _make_cache(self, items):
        from hometools.streaming.core.index_cache import IndexCache

        cache = IndexCache(lambda lib, *, cache_dir=None: items, ttl=9999, label="test")
        cache._items = list(items)
        cache._built_at = __import__("time").monotonic()
        cache._library_dir = __import__("pathlib").Path("/fake")
        cache._cache_dir = None
        return cache

    def test_patch_updates_rating(self):
        items = [
            MediaItem("a.mp3", "A", "X", "/s", "audio", rating=2.0),
            MediaItem("b.mp3", "B", "X", "/s", "audio", rating=0.0),
        ]
        cache = self._make_cache(items)
        changed = cache.patch_items({"a.mp3": {"rating": 5.0}})
        assert changed == 1
        assert cache._items[0].rating == 5.0
        assert cache._items[1].rating == 0.0  # unchanged

    def test_patch_no_change_returns_zero(self):
        items = [MediaItem("a.mp3", "A", "X", "/s", "audio", rating=3.0)]
        cache = self._make_cache(items)
        changed = cache.patch_items({"a.mp3": {"rating": 3.0}})
        assert changed == 0

    def test_patch_unknown_path_ignored(self):
        items = [MediaItem("a.mp3", "A", "X", "/s", "audio", rating=1.0)]
        cache = self._make_cache(items)
        changed = cache.patch_items({"nonexistent.mp3": {"rating": 5.0}})
        assert changed == 0
        assert cache._items[0].rating == 1.0

    def test_patch_empty_updates(self):
        items = [MediaItem("a.mp3", "A", "X", "/s", "audio")]
        cache = self._make_cache(items)
        assert cache.patch_items({}) == 0

    def test_patch_empty_cache(self):
        from hometools.streaming.core.index_cache import IndexCache

        cache = IndexCache(lambda lib, *, cache_dir=None: [], ttl=9999, label="test")
        assert cache.patch_items({"a.mp3": {"rating": 5.0}}) == 0

    def test_patch_multiple_items(self):
        items = [
            MediaItem("a.mp3", "A", "X", "/s", "audio", rating=1.0),
            MediaItem("b.mp3", "B", "X", "/s", "audio", rating=2.0),
            MediaItem("c.mp3", "C", "X", "/s", "audio", rating=3.0),
        ]
        cache = self._make_cache(items)
        changed = cache.patch_items(
            {
                "a.mp3": {"rating": 5.0},
                "c.mp3": {"rating": 4.0},
            }
        )
        assert changed == 2
        assert cache._items[0].rating == 5.0
        assert cache._items[1].rating == 2.0  # unchanged
        assert cache._items[2].rating == 4.0

    def test_patch_invalid_field_skipped(self):
        """Invalid field names are skipped gracefully (no crash)."""
        items = [MediaItem("a.mp3", "A", "X", "/s", "audio", rating=1.0)]
        cache = self._make_cache(items)
        changed = cache.patch_items({"a.mp3": {"nonexistent_field": 42}})
        assert changed == 0  # replace() fails, item kept as-is
