"""Tests for the audio streaming catalog helpers."""

from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    encode_relative_path,
    list_artists,
    query_tracks,
    sort_tracks,
)
from hometools.streaming.core.models import MediaItem


def test_audio_track_is_media_item():
    """AudioTrack is just an alias for MediaItem."""
    assert AudioTrack is MediaItem


def test_build_audio_index_filters_audio_files_and_sorts(tmp_path):
    (tmp_path / "B Artist - Second.mp3").write_text("b")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "A Artist - First.flac").write_text("a")
    (tmp_path / "ignore.txt").write_text("ignored")

    tracks = build_audio_index(tmp_path)

    assert [track.artist for track in tracks] == ["A Artist", "B Artist"]
    assert [track.title for track in tracks] == ["First", "Second"]
    assert all(track.media_type == "audio" for track in tracks)
    assert all(track.stream_url.startswith("/audio/stream?path=") for track in tracks)


def test_build_audio_index_returns_empty_list_for_missing_directory(tmp_path):
    missing_dir = tmp_path / "does-not-exist"
    assert build_audio_index(missing_dir) == []


def test_encode_relative_path_escapes_spaces_and_slashes():
    encoded = encode_relative_path("folder/My Song.mp3")
    assert "%2F" in encoded
    assert " " not in encoded


def test_query_tracks_filters_by_search_and_artist():
    tracks = [
        MediaItem("a/one.mp3", "One More Time", "Daft Punk", "/audio/stream?path=a", "audio"),
        MediaItem("b/two.mp3", "Uprising", "Muse", "/audio/stream?path=b", "audio"),
        MediaItem("c/three.mp3", "Harder Better", "Daft Punk", "/audio/stream?path=c", "audio"),
    ]
    result = query_tracks(tracks, q="hard", artist="daft punk", sort_by="title")
    assert [t.title for t in result] == ["Harder Better"]


def test_query_tracks_matches_relative_path_case_insensitive():
    tracks = [
        MediaItem("Library/Nested/Track.mp3", "Song", "Artist", "/audio/stream?path=x", "audio"),
    ]
    result = query_tracks(tracks, q="nested/track")
    assert len(result) == 1


def test_sort_tracks_supports_title_and_path():
    tracks = [
        MediaItem("z/final.mp3", "Zulu", "B Artist", "u1", "audio"),
        MediaItem("a/first.mp3", "Alpha", "A Artist", "u2", "audio"),
    ]
    assert [t.title for t in sort_tracks(tracks, "title")] == ["Alpha", "Zulu"]
    assert [t.relative_path for t in sort_tracks(tracks, "path")] == ["a/first.mp3", "z/final.mp3"]


def test_list_artists_returns_unique_sorted_values():
    tracks = [
        MediaItem("a.mp3", "A", "Muse", "u1", "audio"),
        MediaItem("b.mp3", "B", "daft punk", "u2", "audio"),
        MediaItem("c.mp3", "C", "Muse", "u3", "audio"),
    ]
    assert list_artists(tracks) == ["daft punk", "Muse"]
