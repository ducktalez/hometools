"""Tests for the Skip-Intro feature (markers, overrides, endpoints, UI)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from hometools.streaming.core import intro_markers
from hometools.streaming.core.media_overrides import _parse_overrides, apply_overrides
from hometools.streaming.core.models import MediaItem
from hometools.streaming.video.server import create_app


def _item(rel: str, *, season: int = 1, episode: int = 1, intro_start: float = 0.0, intro_end: float = 0.0) -> MediaItem:
    return MediaItem(
        relative_path=rel,
        title=rel.rsplit("/", 1)[-1],
        artist="Series",
        stream_url=f"/video/stream?path={rel}",
        media_type="video",
        season=season,
        episode=episode,
        intro_start=intro_start,
        intro_end=intro_end,
    )


# ---------------------------------------------------------------------------
# MediaItem
# ---------------------------------------------------------------------------


class TestMediaItemIntroFields:
    def test_defaults_zero(self):
        item = _item("S/e1.mp4")
        assert item.intro_start == 0.0
        assert item.intro_end == 0.0

    def test_to_dict_includes_intro(self):
        d = _item("S/e1.mp4", intro_start=2.0, intro_end=90.0).to_dict()
        assert d["intro_start"] == 2.0
        assert d["intro_end"] == 90.0


# ---------------------------------------------------------------------------
# YAML overrides
# ---------------------------------------------------------------------------


class TestIntroOverrides:
    def test_folder_level_intro_parsed(self):
        ov = _parse_overrides({"intro_start": 0, "intro_end": 90})
        assert ov.intro_end == 90.0

    def test_mmss_string_parsed(self):
        ov = _parse_overrides({"intro_end": "1:35"})
        assert ov.intro_end == 95.0

    def test_episode_intro_wins_over_folder(self, tmp_path):
        # Folder default 90s, episode override 30s
        items = [_item("Series/S01E01.mp4")]
        overrides = {
            "Series": _parse_overrides(
                {
                    "intro_end": 90,
                    "episodes": {"S01E01.mp4": {"intro_end": 30}},
                }
            )
        }
        result = apply_overrides(items, tmp_path, overrides=overrides)
        assert result[0].intro_end == 30.0

    def test_folder_default_applies_to_episode_without_override(self, tmp_path):
        items = [_item("Series/S01E02.mp4")]
        overrides = {"Series": _parse_overrides({"intro_end": 90})}
        result = apply_overrides(items, tmp_path, overrides=overrides)
        assert result[0].intro_end == 90.0


# ---------------------------------------------------------------------------
# Marker store
# ---------------------------------------------------------------------------


class TestMarkerStore:
    def test_set_get_roundtrip(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=88)
        m = intro_markers.get_marker(tmp_path, "video", "S/e1.mp4")
        assert m == {"start": 0.0, "end": 88.0, "source": "manual"}

    def test_delete(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=88)
        assert intro_markers.delete_marker(tmp_path, "video", "S/e1.mp4") is True
        assert intro_markers.get_marker(tmp_path, "video", "S/e1.mp4") is None

    def test_auto_does_not_clobber_manual(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=88, source="manual")
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=10, source="auto")
        m = intro_markers.get_marker(tmp_path, "video", "S/e1.mp4")
        assert m["end"] == 88.0
        assert m["source"] == "manual"

    def test_empty_path_rejected(self, tmp_path):
        assert intro_markers.set_marker(tmp_path, "video", "", start=0, end=5) is None

    def test_end_before_start_clamped(self, tmp_path):
        m = intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=50, end=10)
        assert m["start"] == 0.0
        assert m["end"] == 10.0


# ---------------------------------------------------------------------------
# apply_intro_markers precedence
# ---------------------------------------------------------------------------


class TestApplyMarkers:
    def test_manual_overrides_existing_yaml(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=120, source="manual")
        items = [_item("S/e1.mp4", intro_end=90.0)]  # YAML value
        result = intro_markers.apply_intro_markers(items, tmp_path, "video")
        assert result[0].intro_end == 120.0

    def test_auto_only_fills_gaps(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=12, source="auto")
        items = [_item("S/e1.mp4", intro_end=90.0)]  # YAML already set
        result = intro_markers.apply_intro_markers(items, tmp_path, "video")
        assert result[0].intro_end == 90.0  # auto must not override

    def test_auto_applies_when_no_value(self, tmp_path):
        intro_markers.set_marker(tmp_path, "video", "S/e1.mp4", start=0, end=12, source="auto")
        items = [_item("S/e1.mp4", intro_end=0.0)]
        result = intro_markers.apply_intro_markers(items, tmp_path, "video")
        assert result[0].intro_end == 12.0

    def test_no_markers_returns_unchanged(self, tmp_path):
        items = [_item("S/e1.mp4")]
        assert intro_markers.apply_intro_markers(items, tmp_path, "video") == items


# ---------------------------------------------------------------------------
# Chapter detection (ffprobe mocked)
# ---------------------------------------------------------------------------


class TestChapterDetection:
    def test_no_ffprobe_returns_none(self, tmp_path):
        with patch("hometools.streaming.core.intro_markers.shutil.which", return_value=None):
            assert intro_markers.detect_intro_from_chapters(tmp_path / "x.mp4") is None

    def test_intro_chapter_detected(self, tmp_path):
        chapters = {
            "chapters": [
                {"start_time": "0.000", "end_time": "92.000", "tags": {"title": "Opening Credits"}},
                {"start_time": "92.000", "end_time": "1400.0", "tags": {"title": "Episode"}},
            ]
        }
        proc = MagicMock(returncode=0, stdout=json.dumps(chapters))
        with (
            patch("hometools.streaming.core.intro_markers.shutil.which", return_value="/usr/bin/ffprobe"),
            patch("hometools.streaming.core.intro_markers.subprocess.run", return_value=proc),
        ):
            window = intro_markers.detect_intro_from_chapters(tmp_path / "x.mp4")
        assert window == (0.0, 92.0)

    def test_overlong_chapter_ignored(self, tmp_path):
        chapters = {"chapters": [{"start_time": "0", "end_time": "9999", "tags": {"title": "Intro"}}]}
        proc = MagicMock(returncode=0, stdout=json.dumps(chapters))
        with (
            patch("hometools.streaming.core.intro_markers.shutil.which", return_value="/usr/bin/ffprobe"),
            patch("hometools.streaming.core.intro_markers.subprocess.run", return_value=proc),
        ):
            assert intro_markers.detect_intro_from_chapters(tmp_path / "x.mp4") is None

    def test_no_matching_chapter(self, tmp_path):
        chapters = {"chapters": [{"start_time": "0", "end_time": "60", "tags": {"title": "Scene 1"}}]}
        proc = MagicMock(returncode=0, stdout=json.dumps(chapters))
        with (
            patch("hometools.streaming.core.intro_markers.shutil.which", return_value="/usr/bin/ffprobe"),
            patch("hometools.streaming.core.intro_markers.subprocess.run", return_value=proc),
        ):
            assert intro_markers.detect_intro_from_chapters(tmp_path / "x.mp4") is None


# ---------------------------------------------------------------------------
# Server endpoints
# ---------------------------------------------------------------------------


class TestIntroEndpoints:
    def test_set_get_delete(self, tmp_path):
        client = TestClient(create_app(tmp_path, cache_dir=tmp_path / "cache"))

        r = client.post("/api/video/intro", json={"path": "S/e1.mp4", "start": 0, "end": 88})
        assert r.status_code == 200
        assert r.json()["marker"]["end"] == 88.0

        r = client.get("/api/video/intro", params={"path": "S/e1.mp4"})
        assert r.json()["marker"]["end"] == 88.0

        r = client.request("DELETE", "/api/video/intro", params={"path": "S/e1.mp4"})
        assert r.json()["deleted"] is True

    def test_set_requires_path(self, tmp_path):
        client = TestClient(create_app(tmp_path, cache_dir=tmp_path / "cache"))
        r = client.post("/api/video/intro", json={"start": 0, "end": 5})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# UI injection
# ---------------------------------------------------------------------------


class TestSkipIntroUI:
    def test_video_page_has_button_when_enabled(self):
        from hometools.streaming.core.server_utils import render_media_page

        html = render_media_page(
            title="t",
            emoji="x",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            enable_skip_intro=True,
        )
        assert 'class="video-skip-intro-btn"' in html
        assert "var SKIP_INTRO_ENABLED = true" in html

    def test_video_page_no_button_when_disabled(self):
        from hometools.streaming.core.server_utils import render_media_page

        html = render_media_page(
            title="t",
            emoji="x",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            enable_skip_intro=False,
        )
        assert 'class="video-skip-intro-btn"' not in html
        assert "var SKIP_INTRO_ENABLED = false" in html

    def test_audio_page_never_has_button(self):
        from hometools.streaming.core.server_utils import render_media_page

        html = render_media_page(
            title="t",
            emoji="x",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/audio/items",
            enable_skip_intro=True,
        )
        # audio mode never renders the overlay button element
        assert 'class="video-skip-intro-btn"' not in html
