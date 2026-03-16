"""Tests for the audio streaming catalog helpers."""

from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    encode_relative_path,
    list_artists,
    query_tracks,
    sort_tracks,
)


def test_build_audio_index_filters_audio_files_and_sorts(tmp_path):
    (tmp_path / "B Artist - Second.mp3").write_text("b")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "A Artist - First.flac").write_text("a")
    (tmp_path / "ignore.txt").write_text("ignored")

    tracks = build_audio_index(tmp_path)

    assert [track.artist for track in tracks] == ["A Artist", "B Artist"]
    assert [track.title for track in tracks] == ["First", "Second"]
    assert [track.relative_path for track in tracks] == [
        "nested/A Artist - First.flac",
        "B Artist - Second.mp3",
    ]
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
        AudioTrack("a/one.mp3", "Daft Punk", "One More Time", "/audio/stream?path=a"),
        AudioTrack("b/two.mp3", "Muse", "Uprising", "/audio/stream?path=b"),
        AudioTrack("c/three.mp3", "Daft Punk", "Harder Better", "/audio/stream?path=c"),
    ]

    result = query_tracks(tracks, q="hard", artist="daft punk", sort_by="title")

    assert [track.title for track in result] == ["Harder Better"]


def test_query_tracks_matches_relative_path_case_insensitive():
    tracks = [
        AudioTrack("Library/Nested/Track.mp3", "Artist", "Song", "/audio/stream?path=x"),
    ]

    result = query_tracks(tracks, q="nested/track")

    assert len(result) == 1


def test_sort_tracks_supports_title_and_path():
    tracks = [
        AudioTrack("z/final.mp3", "B Artist", "Zulu", "u1"),
        AudioTrack("a/first.mp3", "A Artist", "Alpha", "u2"),
    ]

    assert [track.title for track in sort_tracks(tracks, "title")] == ["Alpha", "Zulu"]
    assert [track.relative_path for track in sort_tracks(tracks, "path")] == ["a/first.mp3", "z/final.mp3"]


def test_list_artists_returns_unique_sorted_values():
    tracks = [
        AudioTrack("a.mp3", "Muse", "A", "u1"),
        AudioTrack("b.mp3", "daft punk", "B", "u2"),
        AudioTrack("c.mp3", "Muse", "C", "u3"),
    ]

    assert list_artists(tracks) == ["daft punk", "Muse"]


