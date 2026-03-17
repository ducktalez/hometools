"""Tests for the video streaming catalog and sync."""

from unittest.mock import patch

from hometools.streaming.video.catalog import (
    _folder_as_artist,
    _title_from_filename,
    build_video_index,
)
from hometools.streaming.video.sync import plan_video_sync, sync_video_library

# ---------------------------------------------------------------------------
# Video catalog
# ---------------------------------------------------------------------------


def test_title_from_filename_strips_codec_tags():
    assert _title_from_filename("Movie.Name.1080p.x264.BluRay") == "Movie Name"


def test_title_from_filename_removes_brackets():
    assert _title_from_filename("Title [HEVC] (2024)") == "Title"


def test_title_from_filename_plain_name():
    assert _title_from_filename("Borat") == "Borat"


def test_folder_as_artist(tmp_path):
    root = tmp_path / "lib"
    sub = root / "Action"
    sub.mkdir(parents=True)
    f = sub / "movie.mp4"
    f.write_text("")
    assert _folder_as_artist(f, root) == "Action"


def test_folder_as_artist_no_subfolder(tmp_path):
    f = tmp_path / "movie.mp4"
    f.write_text("")
    assert _folder_as_artist(f, tmp_path) == ""


def test_build_video_index_finds_videos(tmp_path):
    genre = tmp_path / "Comedy"
    genre.mkdir()
    (genre / "Borat.mp4").write_bytes(b"")
    (genre / "notes.txt").write_text("ignored")
    (tmp_path / "standalone.mkv").write_bytes(b"")

    items = build_video_index(tmp_path)
    assert len(items) == 2
    titles = {i.title for i in items}
    assert "Borat" in titles
    assert all(i.media_type == "video" for i in items)
    # Folder-based artist
    comedy_item = next(i for i in items if i.title == "Borat")
    assert comedy_item.artist == "Comedy"


def test_build_video_index_empty_for_missing_dir(tmp_path):
    assert build_video_index(tmp_path / "nope") == []


# ---------------------------------------------------------------------------
# Video sync
# ---------------------------------------------------------------------------


def test_plan_video_sync_finds_mp4(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "movie.mp4").write_text("data")
    (source / "readme.txt").write_text("skip")

    ops = plan_video_sync(source, target)
    assert len(ops) == 1
    assert ops[0].destination.name == "movie.mp4"


def test_sync_video_library_copies(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "film.mkv").write_text("video-data")

    ops = sync_video_library(source, target)
    assert len(ops) == 1
    assert (target / "film.mkv").exists()


# ---------------------------------------------------------------------------
# Embedded metadata (video)
# ---------------------------------------------------------------------------


def test_build_video_index_prefers_embedded_title(tmp_path):
    """When a video file has an embedded title tag, use it instead of parsing the filename."""
    (tmp_path / "messy.filename.1080p.x264.mp4").write_bytes(b"")

    fake_meta = {"title": "The Real Title", "artist": "Director X"}

    with patch("hometools.streaming.video.catalog._read_metadata_fast", return_value=fake_meta):
        items = build_video_index(tmp_path)

    assert len(items) == 1
    assert items[0].title == "The Real Title"
    assert items[0].artist == "Director X"


def test_build_video_index_falls_back_to_filename_when_no_metadata(tmp_path):
    """Without embedded metadata the filename/folder heuristics still work."""
    genre = tmp_path / "Action"
    genre.mkdir()
    (genre / "Borat.mp4").write_bytes(b"")

    with patch("hometools.streaming.video.catalog._read_metadata_fast", return_value=None):
        items = build_video_index(tmp_path)

    assert len(items) == 1
    assert items[0].title == "Borat"
    assert items[0].artist == "Action"


def test_build_video_index_partial_metadata_uses_fallback(tmp_path):
    """If only title is in metadata, folder is still used for artist."""
    genre = tmp_path / "Comedy"
    genre.mkdir()
    (genre / "movie.mp4").write_bytes(b"")

    # Metadata has title but no artist
    fake_meta = {"title": "Funny Movie", "artist": ""}

    with patch("hometools.streaming.video.catalog._read_metadata_fast", return_value=fake_meta):
        items = build_video_index(tmp_path)

    assert len(items) == 1
    assert items[0].title == "Funny Movie"
    assert items[0].artist == "Comedy"
