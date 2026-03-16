"""Tests for the shared streaming core — models, catalog, sync, server_utils."""

from pathlib import Path

from hometools.streaming.core.models import MediaItem, encode_relative_path
from hometools.streaming.core.catalog import sort_items, query_items, list_artists
from hometools.streaming.core.sync import plan_sync, sync_library, copy_reason
from hometools.streaming.core.server_utils import resolve_media_path, render_media_page


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

