"""Tests for missing-episode (gap) detection."""

from hometools.streaming.core.episode_gaps import SeasonGap, find_missing_episodes
from hometools.streaming.core.models import MediaItem


def _ep(folder: str, season: int, episode: int, *, artist: str | None = None) -> MediaItem:
    name = f"S{season:02d}E{episode:02d}.mp4"
    rel = f"{folder}/{name}" if folder else name
    return MediaItem(
        relative_path=rel,
        title=name,
        artist=artist if artist is not None else (folder.split("/")[0] if folder else ""),
        stream_url=f"/video/stream?path={rel}",
        media_type="video",
        season=season,
        episode=episode,
    )


def test_single_interior_gap_detected():
    items = [_ep("Show", 1, 1), _ep("Show", 1, 2), _ep("Show", 1, 4)]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    g = gaps[0]
    assert isinstance(g, SeasonGap)
    assert g.season == 1
    assert g.missing_episodes == [3]
    assert g.first_episode == 1
    assert g.last_episode == 4
    assert g.present_episodes == [1, 2, 4]


def test_no_gap_when_contiguous():
    items = [_ep("Show", 1, 1), _ep("Show", 1, 2), _ep("Show", 1, 3)]
    assert find_missing_episodes(items) == []


def test_whole_season_not_reported():
    # Season 1 fully present, season 2 entirely absent → no gap (no interior range)
    items = [_ep("Show", 1, 1), _ep("Show", 1, 2)]
    assert find_missing_episodes(items) == []


def test_single_episode_season_skipped():
    # Only one episode → no range to interpolate
    items = [_ep("Show", 1, 5)]
    assert find_missing_episodes(items) == []


def test_multiple_missing_episodes_in_range():
    items = [_ep("Show", 2, 1), _ep("Show", 2, 5)]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    assert gaps[0].missing_episodes == [2, 3, 4]


def test_seasons_grouped_independently():
    items = [
        _ep("Show", 1, 1),
        _ep("Show", 1, 3),  # missing E02
        _ep("Show", 2, 1),
        _ep("Show", 2, 2),  # complete
    ]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    assert gaps[0].season == 1
    assert gaps[0].missing_episodes == [2]


def test_unrelated_shows_not_merged():
    items = [
        _ep("ShowA", 1, 1),
        _ep("ShowA", 1, 3),
        _ep("ShowB", 1, 1),
        _ep("ShowB", 1, 2),  # complete
    ]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    assert gaps[0].series == "ShowA"
    assert gaps[0].missing_episodes == [2]


def test_non_episode_items_ignored():
    items = [
        MediaItem(
            relative_path="Movies/film.mp4",
            title="film",
            artist="Movies",
            stream_url="/video/stream?path=Movies/film.mp4",
            media_type="video",
        ),
        _ep("Show", 1, 1),
        _ep("Show", 1, 3),
    ]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    assert gaps[0].missing_episodes == [2]


def test_empty_input_returns_empty():
    assert find_missing_episodes([]) == []


def test_to_dict_shape():
    items = [_ep("Show", 1, 1), _ep("Show", 1, 3)]
    g = find_missing_episodes(items)[0]
    d = g.to_dict()
    assert d["series"] == "Show"
    assert d["season"] == 1
    assert d["missing_episodes"] == [2]
    assert d["missing_count"] == 1
    assert d["first_episode"] == 1
    assert d["last_episode"] == 3
    assert d["present_episodes"] == [1, 3]


def test_episodes_in_season_subfolders_grouped_by_folder():
    items = [
        _ep("Show/Staffel 1", 1, 1),
        _ep("Show/Staffel 1", 1, 4),  # missing 2,3
    ]
    gaps = find_missing_episodes(items)
    assert len(gaps) == 1
    assert gaps[0].folder == "Show/Staffel 1"
    assert gaps[0].series == "Show"
    assert gaps[0].missing_episodes == [2, 3]
