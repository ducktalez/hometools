"""Tests for hometools.audio.metadata — embedded metadata reading."""

import subprocess
from unittest.mock import MagicMock, patch

from hometools.audio.metadata import (
    _find_tag,
    _first_text,
    _read_metadata_ffprobe,
    audiofile_assume_artist_title,
    popm_raw_to_stars,
    read_embedded_metadata,
    stars_to_popm_raw,
    write_track_tags,
)

# ---------------------------------------------------------------------------
# _first_text helper
# ---------------------------------------------------------------------------


def test_first_text_from_list():
    assert _first_text(["Hello", "World"]) == "Hello"


def test_first_text_from_empty_list():
    assert _first_text([]) == ""


def test_first_text_from_string():
    assert _first_text("plain") == "plain"


def test_first_text_from_id3_frame():
    """ID3 TextFrame objects have a .text attribute."""
    frame = MagicMock()
    frame.text = ["Song Title"]
    assert _first_text(frame) == "Song Title"


def test_first_text_strips_whitespace():
    assert _first_text(["  padded  "]) == "padded"


# ---------------------------------------------------------------------------
# _find_tag helper
# ---------------------------------------------------------------------------


def test_find_tag_returns_first_match():
    tags = {"©nam": ["MP4 Title"], "TIT2": MagicMock(text=["ID3 Title"])}
    # ©nam comes first in priority → should win
    assert _find_tag(tags, "©nam", "TIT2") == "MP4 Title"


def test_find_tag_skips_missing_keys():
    tags = {"artist": ["Vorbis Artist"]}
    assert _find_tag(tags, "©ART", "artist", "TPE1") == "Vorbis Artist"


def test_find_tag_returns_empty_when_nothing_found():
    tags = {"unrelated": ["value"]}
    assert _find_tag(tags, "title", "TIT2") == ""


# ---------------------------------------------------------------------------
# read_embedded_metadata
# ---------------------------------------------------------------------------


def test_read_embedded_metadata_mp4_tags(tmp_path):
    """MP4/M4A files use ©nam / ©ART keys."""
    dummy = tmp_path / "song.m4a"
    dummy.write_bytes(b"")

    fake_audio = MagicMock()
    fake_audio.tags = {"\xa9nam": ["My M4A Song"], "\xa9ART": ["Cool Artist"]}

    with patch("hometools.audio.metadata.File", return_value=fake_audio):
        result = read_embedded_metadata(dummy)

    assert result == {"title": "My M4A Song", "artist": "Cool Artist"}


def test_read_embedded_metadata_id3_tags(tmp_path):
    """MP3 files use ID3 frames (TIT2, TPE1)."""
    dummy = tmp_path / "song.mp3"
    dummy.write_bytes(b"")

    tit2 = MagicMock()
    tit2.text = ["ID3 Title"]
    tpe1 = MagicMock()
    tpe1.text = ["ID3 Artist"]

    fake_audio = MagicMock()
    fake_audio.tags = {"TIT2": tit2, "TPE1": tpe1}

    with patch("hometools.audio.metadata.File", return_value=fake_audio):
        result = read_embedded_metadata(dummy)

    assert result == {"title": "ID3 Title", "artist": "ID3 Artist"}


def test_read_embedded_metadata_vorbis_tags(tmp_path):
    """FLAC/OGG files use Vorbis comment keys."""
    dummy = tmp_path / "song.flac"
    dummy.write_bytes(b"")

    fake_audio = MagicMock()
    fake_audio.tags = {"title": ["Vorbis Title"], "artist": ["Vorbis Artist"]}

    with patch("hometools.audio.metadata.File", return_value=fake_audio):
        result = read_embedded_metadata(dummy)

    assert result == {"title": "Vorbis Title", "artist": "Vorbis Artist"}


def test_read_embedded_metadata_returns_none_for_unreadable_file(tmp_path):
    """When mutagen can't read the file and ffprobe isn't available, return None."""
    dummy = tmp_path / "unknown.xyz"
    dummy.write_bytes(b"")

    with (
        patch("hometools.audio.metadata.File", return_value=None),
        patch("hometools.audio.metadata._read_metadata_ffprobe", return_value=None),
    ):
        result = read_embedded_metadata(dummy)

    assert result is None


def test_read_embedded_metadata_falls_back_to_ffprobe(tmp_path):
    """When mutagen returns None, ffprobe is tried as fallback."""
    dummy = tmp_path / "movie.mkv"
    dummy.write_bytes(b"")

    with (
        patch("hometools.audio.metadata.File", return_value=None),
        patch(
            "hometools.audio.metadata._read_metadata_ffprobe",
            return_value={"title": "FFprobe Title", "artist": "FFprobe Artist"},
        ),
    ):
        result = read_embedded_metadata(dummy)

    assert result == {"title": "FFprobe Title", "artist": "FFprobe Artist"}


def test_read_embedded_metadata_title_only(tmp_path):
    """When only title is embedded, artist should be empty string."""
    dummy = tmp_path / "song.m4a"
    dummy.write_bytes(b"")

    fake_audio = MagicMock()
    fake_audio.tags = {"\xa9nam": ["Only Title"]}

    with patch("hometools.audio.metadata.File", return_value=fake_audio):
        result = read_embedded_metadata(dummy)

    assert result == {"title": "Only Title", "artist": ""}


def test_read_metadata_ffprobe_uses_utf8_safe_subprocess(tmp_path):
    """ffprobe metadata lookup must use the UTF-8-safe subprocess wrapper on Windows."""
    dummy = tmp_path / "movie.mkv"
    dummy.write_bytes(b"")

    expected = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"format": {"tags": {"title": "Pok\u00e9mon", "artist": "Bj\u00f6rk"}}}',
        stderr="",
    )

    with patch("hometools.audio.metadata.run_text_subprocess", return_value=expected) as mocked_run:
        result = _read_metadata_ffprobe(dummy)

    assert result == {"title": "Pokémon", "artist": "Björk"}
    _args, kwargs = mocked_run.call_args
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] == 10


# ---------------------------------------------------------------------------
# audiofile_assume_artist_title with embedded metadata
# ---------------------------------------------------------------------------


def test_assume_artist_title_prefers_embedded(tmp_path):
    """Embedded metadata should take priority over filename parsing."""
    f = tmp_path / "Wrong Artist - Wrong Title.mp3"
    f.write_bytes(b"")

    fake_meta = {"title": "Correct Title", "artist": "Correct Artist"}

    with patch("hometools.audio.metadata.read_embedded_metadata", return_value=fake_meta):
        artist, title = audiofile_assume_artist_title(f)

    assert artist == "Correct Artist"
    assert title == "Correct Title"


def test_assume_artist_title_falls_back_to_filename(tmp_path):
    """Without embedded metadata, filename parsing is used."""
    f = tmp_path / "File Artist - File Title.mp3"
    f.write_bytes(b"")

    with patch("hometools.audio.metadata.read_embedded_metadata", return_value=None):
        artist, title = audiofile_assume_artist_title(f)

    assert artist == "File Artist"
    assert title == "File Title"


def test_assume_artist_title_partial_metadata(tmp_path):
    """Embedded title with empty artist → artist from filename."""
    f = tmp_path / "Filename Artist - Ignored.mp3"
    f.write_bytes(b"")

    fake_meta = {"title": "Embedded Title", "artist": ""}

    with patch("hometools.audio.metadata.read_embedded_metadata", return_value=fake_meta):
        artist, title = audiofile_assume_artist_title(f)

    assert title == "Embedded Title"
    assert artist == "Filename Artist"


def test_assume_artist_title_lut_overrides_embedded(tmp_path):
    """LUT entries have highest priority, overriding even embedded metadata."""
    f = tmp_path / "Whatever.mp3"
    f.write_bytes(b"")

    fake_meta = {"title": "Embedded", "artist": "Embedded"}
    lut = {f.as_posix(): {"TAG": {"title": "LUT Title", "artist": "LUT Artist"}}}

    with patch("hometools.audio.metadata.read_embedded_metadata", return_value=fake_meta):
        artist, title = audiofile_assume_artist_title(f, lut=lut)

    assert title == "LUT Title"
    assert artist == "LUT Artist"


# ---------------------------------------------------------------------------
# write_track_tags
# ---------------------------------------------------------------------------


def test_write_track_tags_returns_false_for_missing_file(tmp_path):
    """Non-existent file → False (no exception)."""
    result = write_track_tags(tmp_path / "missing.mp3", title="T", artist="A")
    assert result is False


def test_write_track_tags_returns_false_for_unknown_extension(tmp_path):
    """Unsupported extension → False (no exception)."""
    f = tmp_path / "track.xyz"
    f.write_bytes(b"data")
    result = write_track_tags(f, title="T")
    assert result is False


def test_write_track_tags_no_fields_is_noop(tmp_path):
    """Calling with no fields is a no-op and returns True (nothing to do = success)."""
    f = tmp_path / "track.mp3"
    f.write_bytes(b"data")
    result = write_track_tags(f)
    assert result is True


# ---------------------------------------------------------------------------
# get_genre
# ---------------------------------------------------------------------------


def test_get_genre_returns_empty_for_missing_file(tmp_path):
    """get_genre must return empty string for non-existent file."""
    from hometools.audio.metadata import get_genre

    result = get_genre(tmp_path / "nope.mp3")
    assert result == ""


def test_get_genre_returns_empty_for_untagged(tmp_path):
    """get_genre must return empty string for file without genre tag."""
    from hometools.audio.metadata import get_genre

    f = tmp_path / "track.mp3"
    f.write_bytes(b"not a real audio file")
    result = get_genre(f)
    assert result == ""


def test_get_genre_uses_find_tag():
    """get_genre must search for genre-related tag keys."""
    from unittest.mock import MagicMock, patch

    from hometools.audio.metadata import get_genre

    # Simulate an ID3 TCON frame (genre tag)
    tcon_frame = MagicMock()
    tcon_frame.text = ["Rock"]

    fake_audio = MagicMock()
    fake_audio.tags = {"TCON": tcon_frame}

    with patch("hometools.audio.metadata.File", return_value=fake_audio):
        result = get_genre(MagicMock())
        assert result == "Rock"


# ---------------------------------------------------------------------------
# POPM ↔ Stars conversion (WMP standard mapping)
# ---------------------------------------------------------------------------


class TestPopmRawToStars:
    """popm_raw_to_stars uses the Windows Media Player step mapping."""

    def test_unrated(self):
        assert popm_raw_to_stars(0) == 0.0

    def test_one_star_canonical(self):
        assert popm_raw_to_stars(1) == 1.0

    def test_one_star_upper_bound(self):
        assert popm_raw_to_stars(31) == 1.0

    def test_two_star_lower_bound(self):
        assert popm_raw_to_stars(32) == 2.0

    def test_two_star_canonical(self):
        assert popm_raw_to_stars(64) == 2.0

    def test_two_star_upper_bound(self):
        assert popm_raw_to_stars(95) == 2.0

    def test_three_star_lower_bound(self):
        assert popm_raw_to_stars(96) == 3.0

    def test_three_star_canonical(self):
        assert popm_raw_to_stars(128) == 3.0

    def test_three_star_value_102(self):
        """raw=102 must be 3★ (WMP range 96–159), not 2★ as linear mapping yields."""
        assert popm_raw_to_stars(102) == 3.0

    def test_four_star_lower_bound(self):
        assert popm_raw_to_stars(160) == 4.0

    def test_four_star_canonical(self):
        assert popm_raw_to_stars(196) == 4.0

    def test_five_star_lower_bound(self):
        assert popm_raw_to_stars(224) == 5.0

    def test_five_star_canonical(self):
        assert popm_raw_to_stars(255) == 5.0


class TestStarsToPopmRaw:
    """stars_to_popm_raw writes canonical WMP raw values."""

    def test_zero_unrated(self):
        assert stars_to_popm_raw(0) == 0

    def test_one_star(self):
        assert stars_to_popm_raw(1) == 1

    def test_two_stars(self):
        assert stars_to_popm_raw(2) == 64

    def test_three_stars(self):
        assert stars_to_popm_raw(3) == 128

    def test_four_stars(self):
        assert stars_to_popm_raw(4) == 196

    def test_five_stars(self):
        assert stars_to_popm_raw(5) == 255

    def test_clamped_above_5(self):
        assert stars_to_popm_raw(7) == 255

    def test_clamped_below_0(self):
        assert stars_to_popm_raw(-1) == 0

    def test_float_rounds(self):
        """2.6 rounds to 3 → raw=128."""
        assert stars_to_popm_raw(2.6) == 128


class TestPopmRoundtrip:
    """Writing then reading stars must produce the same value."""

    def test_roundtrip_all_stars(self):
        for stars in range(6):
            raw = stars_to_popm_raw(stars)
            assert popm_raw_to_stars(raw) == float(stars)
