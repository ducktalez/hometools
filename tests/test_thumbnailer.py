"""Tests for the shadow-cache thumbnail system."""

from pathlib import Path
from unittest.mock import patch

from hometools.streaming.core.thumbnailer import (
    THUMB_SUFFIX,
    check_thumbnail_cached,
    ensure_thumbnail,
    extract_audio_cover,
    extract_video_thumbnail,
    get_thumbnail_path,
    start_background_thumbnail_generation,
)

# ---------------------------------------------------------------------------
# Pure path helpers
# ---------------------------------------------------------------------------


def test_get_thumbnail_path_audio():
    p = get_thumbnail_path(Path("/cache"), "audio", "Artist/Song.mp3")
    assert p == Path("/cache/audio/Artist/Song.mp3" + THUMB_SUFFIX)


def test_get_thumbnail_path_video():
    p = get_thumbnail_path(Path("/cache"), "video", "Comedy/Borat.mp4")
    assert p == Path("/cache/video/Comedy/Borat.mp4" + THUMB_SUFFIX)


def test_thumb_suffix_is_jpeg():
    assert THUMB_SUFFIX.endswith(".jpg")


# ---------------------------------------------------------------------------
# ensure_thumbnail
# ---------------------------------------------------------------------------


def test_ensure_thumbnail_returns_cached(tmp_path):
    """If a thumbnail already exists on disk, return it without extraction."""
    cache = tmp_path / "cache"
    thumb = cache / "audio" / "Artist" / ("Song.mp3" + THUMB_SUFFIX)
    thumb.parent.mkdir(parents=True)
    thumb.write_bytes(b"\xff\xd8dummy-jpeg")

    result = ensure_thumbnail(
        media_path=tmp_path / "Song.mp3",  # doesn't need to exist
        cache_dir=cache,
        media_type="audio",
        relative_path="Artist/Song.mp3",
    )
    assert result == thumb


def test_ensure_thumbnail_returns_none_for_unknown_type(tmp_path):
    cache = tmp_path / "cache"
    result = ensure_thumbnail(
        media_path=tmp_path / "file.xyz",
        cache_dir=cache,
        media_type="unknown",
        relative_path="file.xyz",
    )
    assert result is None


def test_ensure_thumbnail_audio_no_cover(tmp_path):
    """When no cover can be extracted, return None."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"not-a-real-mp3")

    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", return_value=False):
        result = ensure_thumbnail(media, cache, "audio", "song.mp3")
    assert result is None


def test_ensure_thumbnail_audio_with_cover(tmp_path):
    """When extraction succeeds, return the thumbnail path."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"fake")

    def fake_extract(media_path, thumb_path):
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"\xff\xd8fake-jpeg")
        return True

    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=fake_extract):
        result = ensure_thumbnail(media, cache, "audio", "song.mp3")
    assert result is not None
    assert result.exists()


def test_ensure_thumbnail_video_no_ffmpeg(tmp_path):
    """When ffmpeg is not available, return None."""
    cache = tmp_path / "cache"
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"fake-video")

    with patch("hometools.streaming.core.thumbnailer.extract_video_thumbnail", return_value=False):
        result = ensure_thumbnail(media, cache, "video", "movie.mp4")
    assert result is None


def test_ensure_thumbnail_video_success(tmp_path):
    """When ffmpeg extraction succeeds, return the thumbnail path."""
    cache = tmp_path / "cache"
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"fake-video")

    def fake_extract(media_path, thumb_path, seek_sec=5):
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"\xff\xd8fake-frame")
        return True

    with patch("hometools.streaming.core.thumbnailer.extract_video_thumbnail", side_effect=fake_extract):
        result = ensure_thumbnail(media, cache, "video", "movie.mp4")
    assert result is not None
    assert result.exists()


# ---------------------------------------------------------------------------
# extract_audio_cover (without mutagen installed)
# ---------------------------------------------------------------------------


def test_extract_audio_cover_no_mutagen(tmp_path):
    """When mutagen is not installed, extraction returns False gracefully."""
    media = tmp_path / "song.mp3"
    media.write_bytes(b"fake-mp3")
    thumb = tmp_path / "thumb.jpg"

    with patch("hometools.streaming.core.thumbnailer._extract_cover_bytes", return_value=None):
        assert extract_audio_cover(media, thumb) is False
    assert not thumb.exists()


# ---------------------------------------------------------------------------
# extract_video_thumbnail (without ffmpeg)
# ---------------------------------------------------------------------------


def test_extract_video_thumbnail_no_ffmpeg(tmp_path):
    """When ffmpeg is not on PATH, extraction returns False gracefully."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"fake-video")
    thumb = tmp_path / "thumb.jpg"

    with patch("hometools.streaming.core.thumbnailer.subprocess.run", side_effect=FileNotFoundError):
        assert extract_video_thumbnail(media, thumb) is False


def test_extract_video_thumbnail_ffmpeg_failure(tmp_path):
    """When ffmpeg returns non-zero, extraction returns False."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"fake-video")
    thumb = tmp_path / "thumb.jpg"

    import subprocess

    mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"error")
    with patch("hometools.streaming.core.thumbnailer.subprocess.run", return_value=mock_result):
        assert extract_video_thumbnail(media, thumb) is False


# ---------------------------------------------------------------------------
# check_thumbnail_cached
# ---------------------------------------------------------------------------


def test_check_thumbnail_cached_returns_path_when_exists(tmp_path):
    """Return the path when a thumbnail is already on disk."""
    cache = tmp_path / "cache"
    thumb = cache / "audio" / "Artist" / ("Song.mp3" + THUMB_SUFFIX)
    thumb.parent.mkdir(parents=True)
    thumb.write_bytes(b"\xff\xd8dummy")

    result = check_thumbnail_cached(cache, "audio", "Artist/Song.mp3")
    assert result == thumb


def test_check_thumbnail_cached_returns_none_when_missing(tmp_path):
    """Return None when no thumbnail exists on disk (no generation attempted)."""
    cache = tmp_path / "cache"
    result = check_thumbnail_cached(cache, "audio", "Artist/Song.mp3")
    assert result is None


# ---------------------------------------------------------------------------
# start_background_thumbnail_generation
# ---------------------------------------------------------------------------


def test_start_background_generation_empty_list():
    """Empty work list should not start a thread, return False."""
    assert start_background_thumbnail_generation([]) is False


def test_start_background_generation_creates_thumbnails(tmp_path):
    """Background thread generates thumbnails for work items."""
    import time

    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"fake")

    def fake_extract(media_path, thumb_path):
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"\xff\xd8fake")
        return True

    work = [(media, cache, "audio", "song.mp3")]
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=fake_extract):
        started = start_background_thumbnail_generation(work)
        assert started is True

        # Wait briefly for the daemon thread to finish (patch must stay active)
        time.sleep(0.5)

        thumb_path = get_thumbnail_path(cache, "audio", "song.mp3")
        assert thumb_path.exists()


def test_ensure_thumbnail_never_raises(tmp_path):
    """ensure_thumbnail must never raise, even on unexpected errors."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"fake")

    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=RuntimeError("boom")):
        result = ensure_thumbnail(media, cache, "audio", "song.mp3")
    assert result is None
