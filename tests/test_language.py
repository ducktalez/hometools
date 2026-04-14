"""Tests for streaming/core/language.py — language tag parsing and folder name cleanup."""

from hometools.streaming.core.language import (
    clean_folder_name,
    parse_language_full,
    parse_language_tag,
    parse_subtitle_hint,
    strip_language_tag,
)

# ---------------------------------------------------------------------------
# parse_language_tag
# ---------------------------------------------------------------------------


class TestParseLanguageTag:
    def test_engl(self):
        assert parse_language_tag("Malcolm in the Middle (engl)") == ("Malcolm in the Middle", "en")

    def test_english(self):
        assert parse_language_tag("Breaking Bad (English)") == ("Breaking Bad", "en")

    def test_eng(self):
        assert parse_language_tag("Scrubs (eng)") == ("Scrubs", "en")

    def test_en(self):
        assert parse_language_tag("Friends (en)") == ("Friends", "en")

    def test_engl_gersub(self):
        name, code = parse_language_tag("Game of Thrones (engl, gersub)")
        assert name == "Game of Thrones"
        assert code == "en"

    def test_engl_desub(self):
        name, code = parse_language_tag("Narcos (engl, desub)")
        assert name == "Narcos"
        assert code == "en"

    def test_german(self):
        assert parse_language_tag("Malcolm Mittendrin (german)") == ("Malcolm Mittendrin", "de")

    def test_deutsch(self):
        assert parse_language_tag("Tatort (deutsch)") == ("Tatort", "de")

    def test_de(self):
        assert parse_language_tag("Stromberg (de)") == ("Stromberg", "de")

    def test_french(self):
        assert parse_language_tag("Amélie (french)") == ("Amélie", "fr")

    def test_fr(self):
        assert parse_language_tag("Intouchables (fr)") == ("Intouchables", "fr")

    def test_japanese(self):
        assert parse_language_tag("Naruto (japanese)") == ("Naruto", "ja")

    def test_jap(self):
        assert parse_language_tag("One Piece (jap)") == ("One Piece", "ja")

    def test_no_tag(self):
        assert parse_language_tag("Malcolm Mittendrin") == ("Malcolm Mittendrin", "")

    def test_empty(self):
        assert parse_language_tag("") == ("", "")

    def test_case_insensitive(self):
        assert parse_language_tag("Show (ENGL)") == ("Show", "en")
        assert parse_language_tag("Show (Engl)") == ("Show", "en")

    def test_whitespace_in_tag(self):
        assert parse_language_tag("Show ( engl )") == ("Show", "en")

    def test_spanish(self):
        assert parse_language_tag("Casa de Papel (es)") == ("Casa de Papel", "es")

    def test_italian(self):
        assert parse_language_tag("Gomorra (it)") == ("Gomorra", "it")

    def test_korean(self):
        assert parse_language_tag("Squid Game (ko)") == ("Squid Game", "ko")

    def test_german_engsub(self):
        name, code = parse_language_tag("Show (german, engsub)")
        assert name == "Show"
        assert code == "de"


# ---------------------------------------------------------------------------
# strip_language_tag
# ---------------------------------------------------------------------------


class TestStripLanguageTag:
    def test_strips_engl(self):
        assert strip_language_tag("Show (engl)") == "Show"

    def test_strips_german(self):
        assert strip_language_tag("Show (german)") == "Show"

    def test_no_tag(self):
        assert strip_language_tag("Show") == "Show"

    def test_preserves_other_parens(self):
        # Non-language parens like (2024) should be preserved
        assert strip_language_tag("Movie (2024)") == "Movie (2024)"


# ---------------------------------------------------------------------------
# clean_folder_name
# ---------------------------------------------------------------------------


class TestCleanFolderName:
    def test_hash_and_lang(self):
        assert clean_folder_name("#Malcolm in the Middle (engl)") == "Malcolm in the Middle"

    def test_hash_only(self):
        assert clean_folder_name("#Breaking Bad") == "Breaking Bad"

    def test_lang_only(self):
        assert clean_folder_name("Friends (engl)") == "Friends"

    def test_neither(self):
        assert clean_folder_name("Malcolm Mittendrin") == "Malcolm Mittendrin"

    def test_hash_and_de(self):
        assert clean_folder_name("#Tatort (de)") == "Tatort"

    def test_engl_gersub(self):
        assert clean_folder_name("Show (engl, gersub)") == "Show"

    def test_empty(self):
        assert clean_folder_name("") == ""

    def test_hash_only_char(self):
        assert clean_folder_name("#") == ""


# ---------------------------------------------------------------------------
# parse_subtitle_hint
# ---------------------------------------------------------------------------


class TestParseSubtitleHint:
    def test_gersub(self):
        assert parse_subtitle_hint("Breaking Bad (engl, gersub)") == "de"

    def test_desub(self):
        assert parse_subtitle_hint("Narcos (engl, desub)") == "de"

    def test_german_subs(self):
        assert parse_subtitle_hint("Show (eng, german subs)") == "de"

    def test_deutsch_sub(self):
        assert parse_subtitle_hint("Show (eng, deutsch sub)") == "de"

    def test_english_sub(self):
        assert parse_subtitle_hint("Show (japanese, engsub)") == "en"

    def test_en_subs(self):
        assert parse_subtitle_hint("Show (jap, en subs)") == "en"

    def test_french_sub(self):
        assert parse_subtitle_hint("Show (engl, frsub)") == "fr"

    def test_spanish_sub(self):
        assert parse_subtitle_hint("Show (engl, essub)") == "es"

    def test_italian_sub(self):
        assert parse_subtitle_hint("Show (engl, itsub)") == "it"

    def test_japanese_sub(self):
        assert parse_subtitle_hint("Show (engl, jasub)") == "ja"

    def test_no_subtitle(self):
        assert parse_subtitle_hint("Malcolm in the Middle (engl)") == ""

    def test_plain_name(self):
        assert parse_subtitle_hint("Malcolm Mittendrin") == ""

    def test_empty(self):
        assert parse_subtitle_hint("") == ""

    def test_case_insensitive(self):
        assert parse_subtitle_hint("Show (ENGL, GERSUB)") == "de"

    def test_whitespace_in_tag(self):
        assert parse_subtitle_hint("Show ( engl , ger sub )") == "de"


# ---------------------------------------------------------------------------
# parse_language_full
# ---------------------------------------------------------------------------


class TestParseLanguageFull:
    def test_full_compound(self):
        assert parse_language_full("Breaking Bad (engl, gersub)") == ("Breaking Bad", "en", "de")

    def test_audio_only(self):
        assert parse_language_full("Malcolm in the Middle (engl)") == ("Malcolm in the Middle", "en", "")

    def test_no_tags(self):
        assert parse_language_full("Malcolm Mittendrin") == ("Malcolm Mittendrin", "", "")

    def test_engl_with_de_sub(self):
        assert parse_language_full("Show (engl, desub)") == ("Show", "en", "de")

    def test_japanese_with_de_sub(self):
        assert parse_language_full("Anime (jap, gersub)") == ("Anime", "ja", "de")

    def test_german_with_en_sub(self):
        assert parse_language_full("Show (german, engsub)") == ("Show", "de", "en")

    def test_italian_with_en_sub(self):
        assert parse_language_full("Film (it, ensub)") == ("Film", "it", "en")

    def test_empty(self):
        assert parse_language_full("") == ("", "", "")


# ---------------------------------------------------------------------------
# Integration: build_video_index uses language field
# ---------------------------------------------------------------------------


def test_build_video_index_sets_language(tmp_path):
    """Videos in a folder with (engl) tag should get language='en' on MediaItem."""
    from hometools.streaming.video.catalog import build_video_index

    folder = tmp_path / "Series (engl)"
    folder.mkdir()
    (folder / "ep01.mp4").write_bytes(b"\x00" * 100)

    items = build_video_index(tmp_path)
    assert len(items) == 1
    assert items[0].language == "en"
    assert items[0].artist == "Series (engl)"  # artist stays as raw folder name


def test_build_video_index_no_language(tmp_path):
    """Videos without a language tag should get language=''."""
    from hometools.streaming.video.catalog import build_video_index

    folder = tmp_path / "My Series"
    folder.mkdir()
    (folder / "ep01.mp4").write_bytes(b"\x00" * 100)

    items = build_video_index(tmp_path)
    assert len(items) == 1
    assert items[0].language == ""


def test_build_video_index_german_tag(tmp_path):
    """Videos in a folder with (de) tag should get language='de'."""
    from hometools.streaming.video.catalog import build_video_index

    folder = tmp_path / "Tatort (de)"
    folder.mkdir()
    (folder / "ep01.mp4").write_bytes(b"\x00" * 100)

    items = build_video_index(tmp_path)
    assert len(items) == 1
    assert items[0].language == "de"


# ---------------------------------------------------------------------------
# Integration: subtitle_language in build_video_index
# ---------------------------------------------------------------------------


def test_build_video_index_sets_subtitle_language(tmp_path):
    """Videos in a folder with (engl, gersub) should get subtitle_language='de'."""
    from hometools.streaming.video.catalog import build_video_index

    folder = tmp_path / "Show (engl, gersub)"
    folder.mkdir()
    (folder / "ep01.mp4").write_bytes(b"\x00" * 100)

    items = build_video_index(tmp_path)
    assert len(items) == 1
    assert items[0].language == "en"
    assert items[0].subtitle_language == "de"


def test_build_video_index_no_subtitle_language(tmp_path):
    """Videos without subtitle hint should get subtitle_language=''."""
    from hometools.streaming.video.catalog import build_video_index

    folder = tmp_path / "Show (engl)"
    folder.mkdir()
    (folder / "ep01.mp4").write_bytes(b"\x00" * 100)

    items = build_video_index(tmp_path)
    assert len(items) == 1
    assert items[0].language == "en"
    assert items[0].subtitle_language == ""
