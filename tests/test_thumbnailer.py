"""Tests for the shadow-cache thumbnail system."""

import time
from pathlib import Path
from unittest.mock import patch

from hometools.streaming.core.thumbnailer import (
    FAILURE_FILE,
    THUMB_SUFFIX,
    _compute_seek_seconds,
    _failure_key,
    check_thumbnail_cached,
    ensure_thumbnail,
    extract_audio_cover,
    extract_video_thumbnail,
    get_thumbnail_path,
    load_failures,
    record_failure,
    save_failures,
    should_skip_failure,
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

    def fake_extract(media_path, thumb_path, seek_sec=None):
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


# ---------------------------------------------------------------------------
# Seek computation (_compute_seek_seconds)
# ---------------------------------------------------------------------------


def test_compute_seek_seconds_with_duration():
    """20 % of a 600-second video → 120 seconds."""
    with patch("hometools.streaming.core.thumbnailer._get_video_duration", return_value=600.0):
        assert _compute_seek_seconds(Path("dummy.mp4")) == 120


def test_compute_seek_seconds_short_video():
    """20 % of a 3-second video → at least 1 second."""
    with patch("hometools.streaming.core.thumbnailer._get_video_duration", return_value=3.0):
        assert _compute_seek_seconds(Path("short.mp4")) == 1


def test_compute_seek_seconds_no_ffprobe():
    """When ffprobe fails, fall back to 5 seconds."""
    with patch("hometools.streaming.core.thumbnailer._get_video_duration", return_value=None):
        assert _compute_seek_seconds(Path("unknown.mp4")) == 5


def test_compute_seek_seconds_series_episode():
    """22-minute episode (1320 s) → 20 % = 264 s ≈ 4 min 24 s (skips intro)."""
    with patch("hometools.streaming.core.thumbnailer._get_video_duration", return_value=1320.0):
        assert _compute_seek_seconds(Path("episode.mp4")) == 264


def test_compute_seek_seconds_feature_film():
    """120-minute film (7200 s) → 20 % = 1440 s = 24 min."""
    with patch("hometools.streaming.core.thumbnailer._get_video_duration", return_value=7200.0):
        assert _compute_seek_seconds(Path("film.mp4")) == 1440


# ---------------------------------------------------------------------------
# Failure registry
# ---------------------------------------------------------------------------


def test_failure_key_format():
    assert _failure_key("video", "Comedy/Borat.mp4") == "video::Comedy/Borat.mp4"


def test_load_failures_empty(tmp_path):
    """No failure file on disk → empty dict."""
    assert load_failures(tmp_path) == {}


def test_save_and_load_failures(tmp_path):
    """Round-trip: save then load failure data."""
    failures = {}
    record_failure(failures, "video", "x.mp4", "ffmpeg timeout", 1000.0)
    save_failures(tmp_path, failures)

    loaded = load_failures(tmp_path)
    assert "video::x.mp4" in loaded
    assert loaded["video::x.mp4"]["reason"] == "ffmpeg timeout"
    assert loaded["video::x.mp4"]["source_mtime"] == 1000.0


def test_should_skip_failure_no_entry():
    """Unknown file → do not skip."""
    assert should_skip_failure({}, "audio", "song.mp3", 999.0) is False


def test_should_skip_failure_same_mtime():
    """Same mtime as recorded → skip (file unchanged)."""
    failures = {}
    record_failure(failures, "video", "x.mp4", "error", 1000.0)
    assert should_skip_failure(failures, "video", "x.mp4", 1000.0) is True


def test_should_skip_failure_newer_source():
    """Source mtime newer than recorded → do NOT skip (retry)."""
    failures = {}
    record_failure(failures, "video", "x.mp4", "error", 1000.0)
    assert should_skip_failure(failures, "video", "x.mp4", 2000.0) is False


def test_load_failures_corrupt_json(tmp_path):
    """Corrupt JSON file → gracefully return empty dict."""
    (tmp_path / FAILURE_FILE).write_text("not valid json{{{", encoding="utf-8")
    assert load_failures(tmp_path) == {}


# ---------------------------------------------------------------------------
# MTime-based thumbnail invalidation (background worker)
# ---------------------------------------------------------------------------


def test_worker_regenerates_when_source_newer(tmp_path):
    """Worker regenerates thumbnail when source file is newer."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"original")

    # Create an old thumbnail
    thumb = get_thumbnail_path(cache, "audio", "song.mp3")
    thumb.parent.mkdir(parents=True, exist_ok=True)
    thumb.write_bytes(b"\xff\xd8old-thumb")

    # Make source newer than thumbnail
    time.sleep(0.05)
    media.write_bytes(b"updated-content")

    def fake_extract(media_path, thumb_path):
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"\xff\xd8new-thumb")
        return True

    work = [(media, cache, "audio", "song.mp3")]
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=fake_extract):
        started = start_background_thumbnail_generation(work)
        assert started is True
        time.sleep(0.5)

    assert thumb.read_bytes() == b"\xff\xd8new-thumb"


def test_worker_skips_when_thumbnail_up_to_date(tmp_path):
    """Worker does NOT regenerate when thumbnail is newer than source."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"content")

    # Create thumbnail AFTER source
    time.sleep(0.05)
    thumb = get_thumbnail_path(cache, "audio", "song.mp3")
    thumb.parent.mkdir(parents=True, exist_ok=True)
    thumb.write_bytes(b"\xff\xd8current-thumb")

    extract_called = []

    def spy_extract(media_path, thumb_path):
        extract_called.append(True)
        return True

    work = [(media, cache, "audio", "song.mp3")]
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=spy_extract):
        started = start_background_thumbnail_generation(work)
        assert started is True
        time.sleep(0.5)

    # Extraction should NOT have been called
    assert extract_called == []
    assert thumb.read_bytes() == b"\xff\xd8current-thumb"


def test_worker_records_and_skips_failures(tmp_path):
    """Worker records failures and skips them on the next run."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"content")

    extract_calls = []

    def failing_extract(media_path, thumb_path):
        extract_calls.append(True)
        return False  # simulate extraction failure

    work = [(media, cache, "audio", "song.mp3")]

    # First run: extraction fails → recorded in failures.json
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=failing_extract):
        start_background_thumbnail_generation(work)
        time.sleep(0.5)

    assert len(extract_calls) == 1
    failures = load_failures(cache)
    assert "audio::song.mp3" in failures

    # Second run: same file, same mtime → should be skipped
    extract_calls.clear()
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=failing_extract):
        start_background_thumbnail_generation(work)
        time.sleep(0.5)

    assert extract_calls == []  # not retried


def test_worker_retries_failure_after_source_update(tmp_path):
    """Worker retries a failed file when the source mtime is newer."""
    cache = tmp_path / "cache"
    media = tmp_path / "song.mp3"
    media.write_bytes(b"v1")

    def failing_extract(media_path, thumb_path):
        return False

    work = [(media, cache, "audio", "song.mp3")]

    # First run: fails
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=failing_extract):
        start_background_thumbnail_generation(work)
        time.sleep(0.5)

    # Update source file → newer mtime
    time.sleep(0.05)
    media.write_bytes(b"v2-fixed-cover")

    retry_calls = []

    def success_extract(media_path, thumb_path):
        retry_calls.append(True)
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"\xff\xd8fixed")
        return True

    work = [(media, cache, "audio", "song.mp3")]
    with patch("hometools.streaming.core.thumbnailer.extract_audio_cover", side_effect=success_extract):
        start_background_thumbnail_generation(work)
        time.sleep(0.5)

    # Should have retried and succeeded
    assert len(retry_calls) == 1
    thumb = get_thumbnail_path(cache, "audio", "song.mp3")
    assert thumb.exists()
