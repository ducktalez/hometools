"""Tests for hometools.audio.sanitize – pure string transformation functions."""

from hometools.audio.sanitize import (
    sanitize_track_to_path,
    split_extreme,
    split_stem,
    stem_identifier,
)

# ---------------------------------------------------------------------------
# stem_identifier
# ---------------------------------------------------------------------------


class TestStemIdentifier:
    def test_returns_list(self):
        result = stem_identifier("Artist - Title")
        assert isinstance(result, list)
        assert len(result) > 1

    def test_no_change_for_clean_stem(self):
        result = stem_identifier("Artist - Title")
        assert result[-1] == "Artist - Title"

    def test_collapses_double_spaces(self):
        result = stem_identifier("Artist  -  Title")
        assert "  " not in result[-1]

    def test_strips_leading_trailing_spaces(self):
        result = stem_identifier("  Artist - Title  ")
        assert result[-1] == "Artist - Title"

    def test_removes_official_video(self):
        result = stem_identifier("Artist - Title (Official Video)")
        assert "Official" not in result[-1]
        assert "()" not in result[-1]

    def test_removes_official_music_video(self):
        result = stem_identifier("Artist - Title (Official Music Video)")
        assert "Official" not in result[-1]

    def test_normalizes_featuring(self):
        result = stem_identifier("Artist featuring Someone - Title")
        assert "feat. " in result[-1]

    def test_normalizes_feat_dot(self):
        result = stem_identifier("Artist feat Someone - Title")
        assert "feat. " in result[-1]

    def test_normalizes_prod_variants(self):
        for variant in ["produced by", "prod. by", "prod by", "produced"]:
            result = stem_identifier(f"Artist - Title ({variant} Producer)")
            assert "prod. " in result[-1], f"Failed for variant: {variant}"

    def test_normalizes_versus(self):
        result = stem_identifier("Artist vs Someone - Title")
        assert "vs. " in result[-1]

    def test_replaces_html_amp(self):
        result = stem_identifier("Artist1 &amp; Artist2 - Title")
        assert "&amp;" not in result[-1]
        assert "&" in result[-1]

    def test_removes_bitrate_tag(self):
        result = stem_identifier("Artist - Title (152kbit_Opus)")
        assert "152kbit" not in result[-1]

    def test_removes_website_links(self):
        result = stem_identifier("Artist - Title (www.example.com)")
        assert "example" not in result[-1]

    def test_removes_emojis(self):
        result = stem_identifier("Artist - Title 😆😆😆")
        assert "😆" not in result[-1]

    def test_removes_empty_brackets(self):
        result = stem_identifier("Artist - Title () []")
        assert "()" not in result[-1]
        assert "[]" not in result[-1]

    def test_complex_real_world_stem(self):
        """Test with the actual complex filename from wa_data."""
        stem = (
            "2raumwohnung - Wir Werden Sehen (Paul Kalkbrenner Remix) 😆😆😆 "
            "Δ ASAP Rocky feat. 2 Chainz, Drake & Kendrick Lamar - "
            "Fuckin Problem (Prod. By 40) many productions, (prod Simon), "
            "prod sdf erg34, prod. sdf erg34 asd - Topic official video (www.dfg)"
        )
        result = stem_identifier(stem)
        cleaned = result[-1]
        assert "😆" not in cleaned
        assert "()" not in cleaned
        assert "  " not in cleaned


# ---------------------------------------------------------------------------
# sanitize_track_to_path
# ---------------------------------------------------------------------------


class TestSanitizeTrackToPath:
    def test_returns_list(self):
        result = sanitize_track_to_path("Artist - Title")
        assert isinstance(result, list)

    def test_acdc_special_case(self):
        result = sanitize_track_to_path("AC/DC - Highway to Hell")[-1]
        assert "/" not in result
        assert "ACDC" in result

    def test_removes_quotes(self):
        result = sanitize_track_to_path('Artist - "Title"')[-1]
        assert '"' not in result

    def test_replaces_slashes(self):
        result = sanitize_track_to_path("Artist - Title / Subtitle")[-1]
        assert "/" not in result
        assert "\\" not in result

    def test_replaces_invalid_chars(self):
        for char in ["<", ">", ":", "|", "?", "*"]:
            result = sanitize_track_to_path(f"Artist - Title{char}Extra")[-1]
            assert char not in result, f"Character {char!r} should have been replaced"

    def test_clean_input_stays_clean(self):
        result = sanitize_track_to_path("Queen - Bohemian Rhapsody")[-1]
        assert result == "Queen - Bohemian Rhapsody"


# ---------------------------------------------------------------------------
# split_stem
# ---------------------------------------------------------------------------


class TestSplitStem:
    def test_basic_split(self):
        parts = split_stem("Artist - Title")
        assert "Artist" in parts
        assert "Title" in parts

    def test_featuring_split(self):
        parts = split_stem("Artist feat. Someone - Title")
        assert len(parts) >= 3

    def test_min_length_filter(self):
        parts = split_stem("A - B - CD", min_length=2)
        assert "A" not in parts

    def test_brackets_split(self):
        parts = split_stem("Artist - Title (Remix)")
        assert any("Remix" in p for p in parts)


# ---------------------------------------------------------------------------
# split_extreme
# ---------------------------------------------------------------------------


class TestSplitExtreme:
    def test_removes_keywords(self):
        parts = split_extreme("Artist - Title (Official Remix Extended Version)")
        for keyword in ["Official", "Remix", "Extended", "Version"]:
            assert all(keyword.lower() not in p.lower() for p in parts)

    def test_keeps_meaningful_parts(self):
        parts = split_extreme("Deadmau5 - Strobe (Original Mix)")
        assert any("Deadmau5" in p for p in parts) or any("Strobe" in p for p in parts)
