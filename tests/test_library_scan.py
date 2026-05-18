"""Tests for streaming/core/library_scan.py — library structure analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from hometools.streaming.core.library_scan import (
    ScanReport,
    _check_episode_naming,
    _check_oversized_flat,
    _check_untagged_language,
    _has_lang_tag,
    scan_audio_library,
    scan_video_library,
)

# ---------------------------------------------------------------------------
# _has_lang_tag
# ---------------------------------------------------------------------------


class TestHasLangTag:
    def test_detects_engl(self):
        assert _has_lang_tag("Breaking Bad (engl)") is True

    def test_detects_de(self):
        assert _has_lang_tag("Tatort (de)") is True

    def test_detects_english_full(self):
        assert _has_lang_tag("Friends (english)") is True

    def test_detects_german_full(self):
        assert _has_lang_tag("Borat (german)") is True

    def test_no_tag(self):
        assert _has_lang_tag("Malcolm Mittendrin") is False

    def test_no_tag_with_parens(self):
        assert _has_lang_tag("Series (2024)") is False


# ---------------------------------------------------------------------------
# _check_episode_naming
# ---------------------------------------------------------------------------


class TestCheckEpisodeNaming:
    def _make_files(self, names: list[str], tmp_path: Path) -> list[Path]:
        files = []
        for name in names:
            p = tmp_path / name
            p.write_bytes(b"")
            files.append(p)
        return files

    def test_all_parseable_no_issue(self, tmp_path):
        files = self._make_files(["S01E01.mkv", "S01E02.mkv", "S01E03.mkv", "S01E04.mkv"], tmp_path)
        assert _check_episode_naming("Show", files) is None

    def test_too_few_files_no_issue(self, tmp_path):
        files = self._make_files(["ep1.mkv", "ep2.mkv"], tmp_path)
        assert _check_episode_naming("Show", files, min_files=4) is None

    def test_mostly_unparseable_returns_issue(self, tmp_path):
        files = self._make_files(
            ["S01E01.mkv", "random_movie.mkv", "another_thing.mkv", "thing3.mkv", "thing4.mkv"],
            tmp_path,
        )
        issue = _check_episode_naming("Show", files)
        assert issue is not None
        assert issue.check == "episode_naming"
        assert issue.severity == "warning"
        assert issue.folder == "Show"
        assert "generate-overrides" in issue.hint

    def test_exactly_at_threshold_no_issue(self, tmp_path):
        files = self._make_files(["S01E01.mkv", "S01E02.mkv", "no_number.mkv", "no_number2.mkv"], tmp_path)
        # 50% parseable — exactly at boundary (>= 0.5 → no issue)
        assert _check_episode_naming("Show", files, min_ratio=0.5) is None


# ---------------------------------------------------------------------------
# _check_oversized_flat
# ---------------------------------------------------------------------------


class TestCheckOversizedFlat:
    def _make_files(self, count: int, tmp_path: Path) -> list[Path]:
        files = []
        for i in range(count):
            p = tmp_path / f"file_{i:03d}.mp4"
            p.write_bytes(b"")
            files.append(p)
        return files

    def test_under_threshold_no_issue(self, tmp_path):
        files = self._make_files(10, tmp_path)
        assert _check_oversized_flat("Folder", files, threshold=30, media_label="Video") is None

    def test_at_threshold_no_issue(self, tmp_path):
        files = self._make_files(30, tmp_path)
        assert _check_oversized_flat("Folder", files, threshold=30, media_label="Video") is None

    def test_over_threshold_returns_issue(self, tmp_path):
        files = self._make_files(31, tmp_path)
        issue = _check_oversized_flat("Folder", files, threshold=30, media_label="Video")
        assert issue is not None
        assert issue.check == "oversized_folder"
        assert issue.severity == "info"
        assert "31" in issue.message

    def test_empty_folder_no_issue(self, tmp_path):
        assert _check_oversized_flat("Folder", [], threshold=30, media_label="Video") is None


# ---------------------------------------------------------------------------
# _check_untagged_language
# ---------------------------------------------------------------------------


class TestCheckUntaggedLanguage:
    def test_has_lang_tag_in_name_no_issue(self):
        assert _check_untagged_language("Breaking Bad (engl)", "Breaking Bad (engl)", False, False) is None

    def test_has_language_override_no_issue(self):
        assert _check_untagged_language("Show", "Show", has_override_language=True, has_override_group=False) is None

    def test_has_group_override_no_issue(self):
        assert _check_untagged_language("Show", "Show", has_override_language=False, has_override_group=True) is None

    def test_no_hint_returns_issue(self):
        issue = _check_untagged_language("Malcolm Mittendrin", "Malcolm Mittendrin", False, False)
        assert issue is not None
        assert issue.check == "untagged_language"
        assert issue.severity == "info"
        assert "language" in issue.hint


# ---------------------------------------------------------------------------
# scan_video_library
# ---------------------------------------------------------------------------


class TestScanVideoLibrary:
    def test_empty_library_no_issues(self, tmp_path):
        report = scan_video_library(tmp_path)
        assert isinstance(report, ScanReport)
        assert report.issues == []
        assert report.media_type == "video"

    def test_missing_library_returns_empty_report(self, tmp_path):
        report = scan_video_library(tmp_path / "does_not_exist")
        assert report.issues == []
        assert report.scanned_folders == 0

    def test_detects_episode_naming_issue(self, tmp_path):
        series = tmp_path / "My Series"
        series.mkdir()
        for i in range(5):
            (series / f"random_file_{i}.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={})
        assert any(i.check == "episode_naming" for i in report.issues)

    def test_no_episode_naming_issue_for_well_named_files(self, tmp_path):
        series = tmp_path / "My Series"
        series.mkdir()
        for i in range(1, 5):
            (series / f"S01E{i:02d}.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={})
        assert not any(i.check == "episode_naming" for i in report.issues)

    def test_detects_untagged_language(self, tmp_path):
        folder = tmp_path / "Untagged Series"
        folder.mkdir()
        (folder / "S01E01.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={})
        assert any(i.check == "untagged_language" for i in report.issues)

    def test_no_untagged_issue_when_lang_in_name(self, tmp_path):
        folder = tmp_path / "Breaking Bad (engl)"
        folder.mkdir()
        (folder / "S01E01.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={})
        assert not any(i.check == "untagged_language" for i in report.issues)

    def test_no_untagged_issue_when_language_override(self, tmp_path):
        from hometools.streaming.core.media_overrides import FolderOverrides

        folder = tmp_path / "Malcolm Mittendrin"
        folder.mkdir()
        (folder / "S01E01.mkv").write_bytes(b"")
        overrides = {
            "Malcolm Mittendrin": FolderOverrides(
                series_title="Malcolm in the Middle",
                episodes={},
                language="de",
            )
        }
        report = scan_video_library(tmp_path, overrides=overrides)
        assert not any(i.check == "untagged_language" for i in report.issues)

    def test_detects_oversized_flat_folder(self, tmp_path):
        folder = tmp_path / "Huge Folder"
        folder.mkdir()
        for i in range(35):
            (folder / f"movie_{i:03d}.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={}, oversized_threshold=30)
        assert any(i.check == "oversized_folder" for i in report.issues)

    def test_no_oversized_issue_when_has_subfolders(self, tmp_path):
        folder = tmp_path / "Series"
        folder.mkdir()
        season = folder / "Staffel 1"
        season.mkdir()
        for i in range(35):
            (season / f"S01E{i:02d}.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={}, oversized_threshold=30)
        assert not any(i.check == "oversized_folder" and i.folder == "Series" for i in report.issues)

    def test_scanned_folders_and_files_counted(self, tmp_path):
        for series_name in ("Series A (de)", "Series B (en)"):
            f = tmp_path / series_name
            f.mkdir()
            for i in range(3):
                (f / f"S01E{i + 1:02d}.mkv").write_bytes(b"")
        report = scan_video_library(tmp_path, overrides={})
        assert report.scanned_folders == 2
        assert report.checked_files == 6

    def test_to_dict_structure(self, tmp_path):
        report = scan_video_library(tmp_path, overrides={})
        d = report.to_dict()
        assert "issues" in d
        assert "media_type" in d
        assert d["media_type"] == "video"


# ---------------------------------------------------------------------------
# scan_audio_library
# ---------------------------------------------------------------------------


class TestScanAudioLibrary:
    def test_empty_library_no_issues(self, tmp_path):
        report = scan_audio_library(tmp_path)
        assert report.issues == []
        assert report.media_type == "audio"

    def test_detects_oversized_audio_folder(self, tmp_path):
        folder = tmp_path / "Big Artist"
        folder.mkdir()
        for i in range(110):
            (folder / f"track_{i:03d}.mp3").write_bytes(b"")
        report = scan_audio_library(tmp_path, oversized_threshold=100)
        assert any(i.check == "oversized_folder" for i in report.issues)

    def test_no_oversized_under_threshold(self, tmp_path):
        folder = tmp_path / "Normal Artist"
        folder.mkdir()
        for i in range(50):
            (folder / f"track_{i:03d}.mp3").write_bytes(b"")
        report = scan_audio_library(tmp_path, oversized_threshold=100)
        assert not report.issues


# ---------------------------------------------------------------------------
# CLI handler integration
# ---------------------------------------------------------------------------


class TestScanLibraryCli:
    def test_command_registered(self):
        from hometools.cli import build_parser

        parser = build_parser()
        # Command exists — parse_args raises SystemExit(0) for --help
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["scan-library", "--help"])
        assert exc_info.value.code == 0

    def test_returns_0_clean_library(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOMETOOLS_VIDEO_LIBRARY_DIR", str(tmp_path))
        import argparse

        from hometools.cli import run_scan_library

        args = argparse.Namespace(
            library_dir=tmp_path,
            media="video",
            json=False,
            fail_on_warning=False,
        )
        assert run_scan_library(args) == 0

    def test_returns_1_with_fail_on_warning(self, tmp_path, monkeypatch):
        # Create a folder that triggers a warning (bad episode naming)
        series = tmp_path / "My Show"
        series.mkdir()
        for i in range(5):
            (series / f"random_{i}.mkv").write_bytes(b"")

        import argparse

        from hometools.cli import run_scan_library

        args = argparse.Namespace(
            library_dir=tmp_path,
            media="video",
            json=False,
            fail_on_warning=True,
        )
        result = run_scan_library(args)
        assert result == 1

    def test_json_output(self, tmp_path, capsys):
        import argparse
        import json as _json

        from hometools.cli import run_scan_library

        args = argparse.Namespace(
            library_dir=tmp_path,
            media="video",
            json=True,
            fail_on_warning=False,
        )
        run_scan_library(args)
        captured = capsys.readouterr()
        data = _json.loads(captured.out)
        assert "issues" in data
        assert data["media_type"] == "video"
