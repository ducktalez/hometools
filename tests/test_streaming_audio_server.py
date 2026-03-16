"""Tests for HTML rendering and path safety in the audio streaming server."""

from hometools.streaming.audio.catalog import AudioTrack
from hometools.streaming.audio.server import render_audio_index_html, resolve_audio_path


def test_render_audio_index_html_contains_filter_controls(tmp_path):
    tracks = [
        AudioTrack(
            relative_path="Artist/Song.mp3",
            artist="Artist",
            title="Song",
            stream_url="/audio/stream?path=Artist%2FSong.mp3",
        )
    ]

    html = render_audio_index_html(tracks, tmp_path)

    assert 'id="search-input"' in html
    assert 'id="artist-filter"' in html
    assert 'id="sort-field"' in html
    assert '/api/audio/tracks?' in html


def test_resolve_audio_path_rejects_directory_escape(tmp_path):
    safe_file = tmp_path / "ok.mp3"
    safe_file.write_text("audio")

    try:
        resolve_audio_path(tmp_path, "..%2Foutside.mp3")
    except ValueError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("Expected ValueError for path traversal")


def test_resolve_audio_path_rejects_non_audio_file(tmp_path):
    text_file = tmp_path / "note.txt"
    text_file.write_text("not audio")

    try:
        resolve_audio_path(tmp_path, "note.txt")
    except ValueError as exc:
        assert "Unsupported audio suffix" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported suffix")

