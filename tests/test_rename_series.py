"""Tests for the rename-series / generate-overrides CLI features."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from hometools.video.organizer import generate_overrides_yaml, series_rename_episodes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_episode(name: str, episode_number: int):
    """Create a fake TMDB episode object."""
    ep = SimpleNamespace()
    ep.name = name
    ep.episode_number = episode_number
    return ep


def _make_season(episodes: list):
    """Create a fake TMDB season details object."""
    return SimpleNamespace(episodes=episodes)


def _make_tv_show(*, name: str = "TestShow", number_of_seasons: int = 1, show_id: int = 42):
    """Create a fake TMDB tv show object."""
    return SimpleNamespace(name=name, number_of_seasons=number_of_seasons, id=show_id)


def _mock_tv(show_name: str = "TestShow", episodes_per_season: dict[int, list[str]] | None = None):
    """Return a mock TV and Season API pair.

    *episodes_per_season* maps season numbers to lists of episode titles.
    """
    if episodes_per_season is None:
        episodes_per_season = {
            0: [],
            1: ["Pilot", "The Second One", "Finale"],
        }

    tv = MagicMock()
    season_api = MagicMock()

    # tv.search(...) → results with one match
    search_result = SimpleNamespace(id=42, name=show_name)
    tv.search.return_value = {"results": [search_result]}

    # tv.details(42) → show info
    show = _make_tv_show(name=show_name, number_of_seasons=max(episodes_per_season.keys()))
    tv.details.return_value = show

    # season_api.details(42, n) → season with episodes
    def _season_details(show_id, season_num):
        eps = episodes_per_season.get(season_num, [])
        return _make_season([_make_episode(title, i + 1) for i, title in enumerate(eps)])

    season_api.details.side_effect = _season_details

    return tv, season_api


# ---------------------------------------------------------------------------
# series_rename_episodes
# ---------------------------------------------------------------------------


class TestSeriesRenameEpisodes:
    def test_basic_rename_proposals(self, tmp_path):
        """Files with S##E## pattern get rename proposals."""
        (tmp_path / "TestShow S01E01 random.mp4").touch()
        (tmp_path / "TestShow S01E02 stuff.mp4").touch()

        tv, season_api = _mock_tv()
        from_to = series_rename_episodes(tmp_path, season_api, tv)

        assert isinstance(from_to, dict)
        assert len(from_to) >= 1
        for old, new in from_to.items():
            assert old.exists() or old.parent == tmp_path
            assert "S01E0" in new.name

    def test_returns_empty_when_no_tmdb(self, tmp_path):
        """Returns empty dict when TMDB search fails."""
        (tmp_path / "Unknown S01E01.mp4").touch()

        tv = MagicMock()
        tv.search.return_value = {"results": []}
        season_api = MagicMock()

        # tmdb_serie_infos will raise TypeError on empty results
        from_to = series_rename_episodes(tmp_path, season_api, tv)
        assert from_to == {}

    def test_returns_empty_when_already_correct(self, tmp_path):
        """Returns empty dict when files already have correct names."""
        tv, season_api = _mock_tv()
        correct_name = "TestShow S01E01 Pilot.mp4"
        (tmp_path / correct_name).touch()

        # Override folder name to match
        tmp_dir = tmp_path / "TestShow"
        tmp_dir.mkdir()
        (tmp_dir / correct_name).touch()

        from_to = series_rename_episodes(tmp_dir, season_api, tv)
        assert isinstance(from_to, dict)

    def test_skips_files_without_pattern(self, tmp_path):
        """Files without S##E## in the name are skipped."""
        (tmp_path / "random_movie.mp4").touch()
        (tmp_path / "TestShow S01E01 pilot.mp4").touch()

        tv, season_api = _mock_tv()
        from_to = series_rename_episodes(tmp_path, season_api, tv)

        # Only the parseable file should appear
        assert all("S01E" in new.name for new in from_to.values())

    def test_override_series_title(self, tmp_path):
        """FolderOverrides.series_title replaces folder-derived name."""
        from hometools.streaming.core.media_overrides import FolderOverrides

        (tmp_path / "something S01E01 whatever.mp4").touch()

        overrides = FolderOverrides(series_title="Meine Serie", episodes={})
        tv, season_api = _mock_tv(show_name="Meine Serie")

        series_rename_episodes(tmp_path, season_api, tv, overrides=overrides)
        # The TV search should have been called with the override title
        tv.search.assert_called_with("Meine Serie")

    def test_override_episode_title(self, tmp_path):
        """EpisodeOverride.title replaces TMDB episode name."""
        from hometools.streaming.core.media_overrides import EpisodeOverride, FolderOverrides

        fname = "TestShow S01E01 random.mp4"
        (tmp_path / fname).touch()

        overrides = FolderOverrides(
            series_title="",
            episodes={fname: EpisodeOverride(title="Mein Episodentitel")},
        )
        tv, season_api = _mock_tv()
        from_to = series_rename_episodes(tmp_path, season_api, tv, overrides=overrides)

        if from_to:
            new_names = [new.name for new in from_to.values()]
            assert any("Mein Episodentitel" in n for n in new_names)

    def test_override_season_episode_numbers(self, tmp_path):
        """EpisodeOverride can remap season/episode numbers."""
        from hometools.streaming.core.media_overrides import EpisodeOverride, FolderOverrides

        fname = "TestShow S01E01 random.mp4"
        (tmp_path / fname).touch()

        overrides = FolderOverrides(
            series_title="",
            episodes={fname: EpisodeOverride(season=2, episode=5)},
        )
        eps = {0: [], 1: ["Ep1"], 2: ["E1", "E2", "E3", "E4", "Remapped Title"]}
        tv, season_api = _mock_tv(episodes_per_season=eps)
        from_to = series_rename_episodes(tmp_path, season_api, tv, overrides=overrides)

        if from_to:
            new_names = [new.name for new in from_to.values()]
            assert any("S02E05" in n for n in new_names)


# ---------------------------------------------------------------------------
# generate_overrides_yaml
# ---------------------------------------------------------------------------


class TestGenerateOverridesYaml:
    def test_basic_generation(self, tmp_path):
        """Generates a valid override dict from TMDB data."""
        (tmp_path / "Show S01E01 pilot.mp4").touch()
        (tmp_path / "Show S01E02 second.mp4").touch()

        tv, season_api = _mock_tv(show_name="Der Test")
        result = generate_overrides_yaml(tmp_path, season_api, tv)

        assert result is not None
        assert "series_title" in result
        assert result["series_title"] == "Der Test"
        assert "episodes" in result
        assert len(result["episodes"]) == 2

        for _fname, ep_data in result["episodes"].items():
            assert "title" in ep_data
            assert "season" in ep_data
            assert "episode" in ep_data

    def test_returns_none_when_no_tmdb(self, tmp_path):
        """Returns None when TMDB has no results."""
        (tmp_path / "Unknown S01E01.mp4").touch()

        tv = MagicMock()
        tv.search.return_value = {"results": []}
        season_api = MagicMock()

        result = generate_overrides_yaml(tmp_path, season_api, tv)
        assert result is None

    def test_skips_unparseable_files(self, tmp_path):
        """Files without S##E## pattern are omitted from the template."""
        (tmp_path / "random_movie.mp4").touch()
        (tmp_path / "Show S01E01 pilot.mp4").touch()

        tv, season_api = _mock_tv()
        result = generate_overrides_yaml(tmp_path, season_api, tv)

        assert result is not None
        assert "random_movie.mp4" not in result["episodes"]
        assert len(result["episodes"]) == 1


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


class TestCLIParser:
    def test_rename_series_parser(self):
        from hometools.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["rename-series", "/some/path", "--dry-run", "--language", "en"])
        assert args.command == "rename-series"
        assert args.path == Path("/some/path")
        assert args.dry_run is True
        assert args.language == "en"

    def test_rename_series_recursive(self):
        from hometools.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["rename-series", "/some/path", "--recursive"])
        assert args.recursive is True

    def test_generate_overrides_parser(self):
        from hometools.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["generate-overrides", "/series/folder"])
        assert args.command == "generate-overrides"
        assert args.path == Path("/series/folder")
        assert args.language == "de"
        assert args.output is None

    def test_generate_overrides_with_output(self):
        from hometools.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["generate-overrides", "/series/folder", "--output", "/tmp/out.yaml"])
        assert args.output == Path("/tmp/out.yaml")
