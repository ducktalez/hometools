"""Tests for the per-folder YAML media overrides system."""

import pytest
import yaml

from hometools.streaming.core.catalog import parse_season_episode, sort_items
from hometools.streaming.core.media_overrides import (
    OVERRIDE_FILENAME,
    apply_overrides,
    load_all_overrides,
    load_overrides,
)
from hometools.streaming.core.models import MediaItem

# ---------------------------------------------------------------------------
# parse helpers (from previous session — ensure Avatar filenames work)
# ---------------------------------------------------------------------------


class TestAvatarFilenameParsing:
    """Verify that parse_season_episode handles all Avatar filename variants."""

    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("Avatar S01E01 German 2005 DVDRiP REPACK XviD-SiMPTY.avi", (1, 1)),
            ("Avatar S02e08.mp4", (2, 8)),
            ("Avatar S02E07 Sukos Erinnerungen German FS DVDRip XviD-CRiSP.avi.mp4", (2, 7)),
            ("Avatar Der Herr der Elemente S03E18 German FS DVDRiP XViD-ETM.mp4", (3, 18)),
            ("Avatar S03E18 Zosins Komet Teil 1 Der Phoenix Koenig.flv", (3, 18)),
            ("Avatar S03E23 German FS DVDRiP XViD-ETM ((Kinox to FAIL)).mp4", (3, 23)),
        ],
    )
    def test_avatar_episode_detection(self, filename, expected):
        assert parse_season_episode(filename) == expected


# ---------------------------------------------------------------------------
# load_overrides
# ---------------------------------------------------------------------------


class TestLoadOverrides:
    def test_returns_none_when_no_file(self, tmp_path):
        assert load_overrides(tmp_path) is None

    def test_loads_valid_yaml(self, tmp_path):
        data = {
            "series_title": "Test Show",
            "episodes": {
                "file.mp4": {"title": "Pilot", "season": 1, "episode": 1},
            },
        }
        (tmp_path / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        ov = load_overrides(tmp_path)
        assert ov is not None
        assert ov.series_title == "Test Show"
        assert "file.mp4" in ov.episodes
        assert ov.episodes["file.mp4"].title == "Pilot"
        assert ov.episodes["file.mp4"].season == 1
        assert ov.episodes["file.mp4"].episode == 1

    def test_partial_override_leaves_none(self, tmp_path):
        data = {"episodes": {"file.mp4": {"title": "Nur Titel"}}}
        (tmp_path / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        ov = load_overrides(tmp_path)
        assert ov is not None
        ep = ov.episodes["file.mp4"]
        assert ep.title == "Nur Titel"
        assert ep.season is None
        assert ep.episode is None

    def test_ignores_malformed_yaml(self, tmp_path):
        (tmp_path / OVERRIDE_FILENAME).write_text("not: [valid: yaml: {{", encoding="utf-8")
        assert load_overrides(tmp_path) is None

    def test_ignores_non_dict_yaml(self, tmp_path):
        (tmp_path / OVERRIDE_FILENAME).write_text("- just\n- a\n- list\n", encoding="utf-8")
        assert load_overrides(tmp_path) is None

    def test_empty_file_returns_none(self, tmp_path):
        (tmp_path / OVERRIDE_FILENAME).write_text("", encoding="utf-8")
        assert load_overrides(tmp_path) is None

    def test_series_title_only(self, tmp_path):
        data = {"series_title": "Avatar: Der Herr der Elemente"}
        (tmp_path / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        ov = load_overrides(tmp_path)
        assert ov is not None
        assert ov.series_title == "Avatar: Der Herr der Elemente"
        assert ov.episodes == {}


# ---------------------------------------------------------------------------
# load_all_overrides
# ---------------------------------------------------------------------------


class TestLoadAllOverrides:
    def test_finds_overrides_in_subfolders(self, tmp_path):
        lib = tmp_path / "library"
        lib.mkdir()
        show = lib / "ShowA"
        show.mkdir()
        data = {"series_title": "Show A", "episodes": {"ep1.mp4": {"title": "Pilot"}}}
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        all_ov = load_all_overrides(lib)
        assert "ShowA" in all_ov
        assert all_ov["ShowA"].series_title == "Show A"

    def test_empty_library_returns_empty(self, tmp_path):
        lib = tmp_path / "empty"
        lib.mkdir()
        assert load_all_overrides(lib) == {}


# ---------------------------------------------------------------------------
# apply_overrides
# ---------------------------------------------------------------------------


class TestApplyOverrides:
    def test_applies_title_override(self, tmp_path):
        lib = tmp_path / "lib"
        show = lib / "Show"
        show.mkdir(parents=True)
        (show / "S01E01.mp4").write_bytes(b"")
        data = {"episodes": {"S01E01.mp4": {"title": "Der Pilot"}}}
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        items = [
            MediaItem("Show/S01E01.mp4", "S01E01", "Show", "/stream?x", "video", season=1, episode=1),
        ]
        result = apply_overrides(items, lib)
        assert result[0].title == "Der Pilot"
        assert result[0].season == 1  # unchanged

    def test_applies_season_episode_override(self, tmp_path):
        lib = tmp_path / "lib"
        show = lib / "Show"
        show.mkdir(parents=True)
        data = {"episodes": {"messy.mp4": {"season": 2, "episode": 5}}}
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        items = [
            MediaItem("Show/messy.mp4", "Messy Title", "Show", "/stream?x", "video"),
        ]
        result = apply_overrides(items, lib)
        assert result[0].season == 2
        assert result[0].episode == 5
        assert result[0].title == "Messy Title"  # unchanged

    def test_applies_series_title_as_artist(self, tmp_path):
        lib = tmp_path / "lib"
        show = lib / "Avatar"
        show.mkdir(parents=True)
        data = {"series_title": "Avatar: Der Herr der Elemente"}
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        items = [
            MediaItem("Avatar/ep.mp4", "Ep", "Avatar", "/stream?x", "video"),
        ]
        result = apply_overrides(items, lib)
        assert result[0].artist == "Avatar: Der Herr der Elemente"

    def test_no_override_file_passes_through(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir(parents=True)

        items = [
            MediaItem("movie.mp4", "Movie", "", "/stream?x", "video"),
        ]
        result = apply_overrides(items, lib)
        assert result[0].title == "Movie"

    def test_unmatched_filename_keeps_series_title(self, tmp_path):
        lib = tmp_path / "lib"
        show = lib / "Show"
        show.mkdir(parents=True)
        data = {
            "series_title": "Clean Name",
            "episodes": {"other.mp4": {"title": "Other"}},
        }
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        items = [
            MediaItem("Show/unmatched.mp4", "Raw Title", "Show", "/stream?x", "video"),
        ]
        result = apply_overrides(items, lib)
        # series_title applies even for unmatched episodes
        assert result[0].artist == "Clean Name"
        # But title stays because no episode override matched
        assert result[0].title == "Raw Title"

    def test_override_and_sort_produces_correct_order(self, tmp_path):
        """Full integration: override + sort gives chronological order."""
        lib = tmp_path / "lib"
        show = lib / "Show"
        show.mkdir(parents=True)
        data = {
            "series_title": "Show",
            "episodes": {
                "messy_third.mp4": {"title": "Episode 3", "season": 1, "episode": 3},
                "first_ep.mp4": {"title": "Episode 1", "season": 1, "episode": 1},
                "another_file.mp4": {"title": "Episode 2", "season": 1, "episode": 2},
            },
        }
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        # Items with wrong/no season/episode (as would come from filename parsing)
        items = [
            MediaItem("Show/messy_third.mp4", "messy third", "Show", "/s?1", "video"),
            MediaItem("Show/first_ep.mp4", "first ep", "Show", "/s?2", "video"),
            MediaItem("Show/another_file.mp4", "another file", "Show", "/s?3", "video"),
        ]

        result = apply_overrides(items, lib)
        sorted_result = sort_items(result, sort_by="artist")

        assert [(i.season, i.episode, i.title) for i in sorted_result] == [
            (1, 1, "Episode 1"),
            (1, 2, "Episode 2"),
            (1, 3, "Episode 3"),
        ]


# ---------------------------------------------------------------------------
# build_video_index integration
# ---------------------------------------------------------------------------


class TestBuildVideoIndexWithOverrides:
    def test_overrides_applied_during_index_build(self, tmp_path):
        """build_video_index should pick up hometools_overrides.yaml."""
        from unittest.mock import patch

        from hometools.streaming.video.catalog import build_video_index

        show = tmp_path / "Show"
        show.mkdir()
        (show / "S01E02.mp4").write_bytes(b"")
        (show / "S01E01.mp4").write_bytes(b"")

        data = {
            "series_title": "Clean Show Name",
            "episodes": {
                "S01E01.mp4": {"title": "Pilot"},
                "S01E02.mp4": {"title": "Second Episode"},
            },
        }
        (show / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")

        with patch("hometools.streaming.video.catalog._read_metadata_fast", return_value=None):
            items = build_video_index(tmp_path)

        assert len(items) == 2
        # Check overrides applied
        ep1 = next(i for i in items if i.episode == 1)
        ep2 = next(i for i in items if i.episode == 2)
        assert ep1.title == "Pilot"
        assert ep2.title == "Second Episode"
        assert ep1.artist == "Clean Show Name"
        # Check chronological order
        assert items[0].episode == 1
        assert items[1].episode == 2
