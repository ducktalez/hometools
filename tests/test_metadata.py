"""Tests for hometools.audio.metadata — embedded metadata reading."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from hometools.audio.metadata import (
    _find_tag,
    _first_text,
    _m4a_rating_to_stars,
    _read_m4a_rating,
    _read_metadata_ffprobe,
    _read_vorbis_rating,
    audiofile_assume_artist_title,
    get_rating_stars,
    popm_raw_to_stars,
    read_embedded_metadata,
    set_rating_stars,
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


# ---------------------------------------------------------------------------
# M4A rating conversion
# ---------------------------------------------------------------------------


class TestM4aRatingToStars:
    """_m4a_rating_to_stars handles both 0–5 and 0–100 scales."""

    def test_zero(self):
        assert _m4a_rating_to_stars(0) == 0.0

    def test_direct_stars_1_to_5(self):
        for s in range(1, 6):
            assert _m4a_rating_to_stars(s) == float(s)

    def test_percentage_scale(self):
        assert _m4a_rating_to_stars(20) == 1.0
        assert _m4a_rating_to_stars(40) == 2.0
        assert _m4a_rating_to_stars(60) == 3.0
        assert _m4a_rating_to_stars(80) == 4.0
        assert _m4a_rating_to_stars(100) == 5.0

    def test_negative_returns_zero(self):
        assert _m4a_rating_to_stars(-5) == 0.0

    def test_intermediate_percentage(self):
        # 50 → round(50/20) = round(2.5) = 2
        assert _m4a_rating_to_stars(50) == 2.0


# ---------------------------------------------------------------------------
# _read_m4a_rating / _read_vorbis_rating with mocked files
# ---------------------------------------------------------------------------


class TestReadM4aRating:
    """_read_m4a_rating reads the freeform iTunes rating atom."""

    def test_missing_file_returns_zero(self, tmp_path):
        p = tmp_path / "missing.m4a"
        assert _read_m4a_rating(p) == 0.0

    def test_file_without_tags(self, tmp_path):
        p = tmp_path / "empty.m4a"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.MP4") as mock_mp4:
            mock_mp4.return_value.tags = None
            assert _read_m4a_rating(p) == 0.0

    def test_reads_freeform_atom(self, tmp_path):
        p = tmp_path / "rated.m4a"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.MP4") as mock_mp4:
            mock_mp4.return_value.tags = {"----:com.apple.iTunes:RATING": [b"80"]}
            assert _read_m4a_rating(p) == 4.0


class TestReadVorbisRating:
    """_read_vorbis_rating reads from FMPS_RATING or RATING Vorbis comment."""

    def test_fmps_rating(self, tmp_path):
        p = tmp_path / "song.flac"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.File") as mock_file:
            mock_file.return_value.tags = {"FMPS_RATING": ["0.6"]}
            assert _read_vorbis_rating(p) == 3.0

    def test_rating_direct_stars(self, tmp_path):
        p = tmp_path / "song.flac"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.File") as mock_file:
            mock_file.return_value.tags = {"RATING": ["4"]}
            assert _read_vorbis_rating(p) == 4.0

    def test_no_tags_returns_zero(self, tmp_path):
        p = tmp_path / "song.flac"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.File") as mock_file:
            mock_file.return_value.tags = {}
            assert _read_vorbis_rating(p) == 0.0

    def test_fmps_one_is_five_stars(self, tmp_path):
        p = tmp_path / "song.ogg"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.File") as mock_file:
            mock_file.return_value.tags = {"FMPS_RATING": ["1.0"]}
            assert _read_vorbis_rating(p) == 5.0


# ---------------------------------------------------------------------------
# get_rating_stars — format dispatch
# ---------------------------------------------------------------------------


class TestGetRatingStars:
    """get_rating_stars dispatches to the correct format reader."""

    def test_mp3_uses_popm(self, tmp_path):
        p = tmp_path / "song.mp3"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.get_popm_rating", return_value=128):
            assert get_rating_stars(p) == 3.0

    def test_m4a_uses_freeform_atom(self, tmp_path):
        p = tmp_path / "song.m4a"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata._read_m4a_rating", return_value=4.0):
            assert get_rating_stars(p) == 4.0

    def test_flac_uses_vorbis_comment(self, tmp_path):
        p = tmp_path / "song.flac"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata._read_vorbis_rating", return_value=2.0):
            assert get_rating_stars(p) == 2.0

    def test_ogg_uses_vorbis_comment(self, tmp_path):
        p = tmp_path / "song.ogg"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata._read_vorbis_rating", return_value=5.0):
            assert get_rating_stars(p) == 5.0

    def test_unsupported_format_returns_zero(self, tmp_path):
        p = tmp_path / "song.wav"
        p.write_bytes(b"")
        assert get_rating_stars(p) == 0.0


# ---------------------------------------------------------------------------
# set_rating_stars — format dispatch
# ---------------------------------------------------------------------------


class TestSetRatingStars:
    """set_rating_stars dispatches to the correct format writer."""

    def test_mp3_uses_popm(self, tmp_path):
        p = tmp_path / "song.mp3"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata.set_popm_rating", return_value=True) as mock:
            assert set_rating_stars(p, 3.0) is True
            mock.assert_called_once_with(p, 128)

    def test_m4a_uses_freeform_atom(self, tmp_path):
        p = tmp_path / "song.m4a"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata._write_m4a_rating", return_value=True) as mock:
            assert set_rating_stars(p, 4.0) is True
            mock.assert_called_once_with(p, 4.0)

    def test_flac_uses_vorbis(self, tmp_path):
        p = tmp_path / "song.flac"
        p.write_bytes(b"")
        with patch("hometools.audio.metadata._write_vorbis_rating", return_value=True) as mock:
            assert set_rating_stars(p, 5.0) is True
            mock.assert_called_once_with(p, 5.0)

    def test_unsupported_returns_false(self, tmp_path):
        p = tmp_path / "song.wav"
        p.write_bytes(b"")
        assert set_rating_stars(p, 3.0) is False


# ---------------------------------------------------------------------------
# M4A rating roundtrip — real file integration tests
# ---------------------------------------------------------------------------


def _create_silent_m4a(path) -> bool:
    """Create a minimal valid M4A file using ffmpeg (0.1s silence).

    Returns ``True`` on success, ``False`` if ffmpeg is unavailable.
    """
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                "0.1",
                "-c:a",
                "aac",
                "-b:a",
                "32k",
                str(path),
            ],
            capture_output=True,
            timeout=15,
        )
        return path.exists() and path.stat().st_size > 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture()
def m4a_file(tmp_path):
    """Provide a minimal valid M4A file for testing.  Skips if ffmpeg is missing."""
    p = tmp_path / "test_rating.m4a"
    if not _create_silent_m4a(p):
        pytest.skip("ffmpeg not available — cannot create test M4A file")
    return p


class TestM4aRatingRoundtrip:
    """Write then read star ratings on a real M4A file (requires ffmpeg)."""

    def test_write_and_read_all_stars(self, m4a_file):
        """Roundtrip for every star value 0–5."""
        for stars in range(6):
            ok = set_rating_stars(m4a_file, float(stars))
            assert ok is True, f"set_rating_stars({stars}) failed"
            result = get_rating_stars(m4a_file)
            assert result == float(stars), f"Expected {stars}, got {result}"

    def test_write_read_fractional_rounds(self, m4a_file):
        """Fractional star values are rounded to the nearest integer."""
        set_rating_stars(m4a_file, 3.7)
        assert get_rating_stars(m4a_file) == 4.0

    def test_overwrite_preserves_other_tags(self, m4a_file):
        """Writing a rating must not destroy existing MP4 tags."""
        from mutagen.mp4 import MP4

        audio = MP4(m4a_file)
        if audio.tags is None:
            audio.add_tags()
        audio.tags["\xa9nam"] = ["Test Title"]
        audio.save()

        set_rating_stars(m4a_file, 5.0)

        audio2 = MP4(m4a_file)
        assert audio2.tags["\xa9nam"] == ["Test Title"]
        assert get_rating_stars(m4a_file) == 5.0

    def test_unrated_file_returns_zero(self, m4a_file):
        """A fresh M4A without a rating atom returns 0.0."""
        assert get_rating_stars(m4a_file) == 0.0


class TestReadM4aRatingBinaryFallback:
    """_read_m4a_rating handles binary (non-UTF-8) data from other tools."""

    def test_single_byte_binary_value(self, tmp_path):
        """A tool that writes a single byte \\x50 (=80) → 4 stars."""
        p = tmp_path / "binary.m4a"
        p.write_bytes(b"")
        from mutagen.mp4 import MP4FreeForm

        binary_val = MP4FreeForm(bytes([80]), dataformat=0)  # IMPLICIT
        with patch("hometools.audio.metadata.MP4") as mock_mp4:
            mock_mp4.return_value.tags = {
                "----:com.apple.iTunes:RATING": [binary_val],
            }
            assert _read_m4a_rating(p) == 4.0

    def test_two_byte_binary_value(self, tmp_path):
        """Two-byte big-endian binary: \\x00\\x3c (=60) → 3 stars."""
        p = tmp_path / "binary2.m4a"
        p.write_bytes(b"")
        from mutagen.mp4 import MP4FreeForm

        binary_val = MP4FreeForm(b"\x00\x3c", dataformat=0)
        with patch("hometools.audio.metadata.MP4") as mock_mp4:
            mock_mp4.return_value.tags = {
                "----:com.apple.iTunes:RATING": [binary_val],
            }
            assert _read_m4a_rating(p) == 3.0

    def test_empty_bytes_returns_zero(self, tmp_path):
        """Empty freeform data → 0.0 stars."""
        p = tmp_path / "empty.m4a"
        p.write_bytes(b"")
        from mutagen.mp4 import MP4FreeForm

        binary_val = MP4FreeForm(b"", dataformat=0)
        with patch("hometools.audio.metadata.MP4") as mock_mp4:
            mock_mp4.return_value.tags = {
                "----:com.apple.iTunes:RATING": [binary_val],
            }
            assert _read_m4a_rating(p) == 0.0
