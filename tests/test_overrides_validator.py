"""Tests for the hometools_overrides.yaml linter."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hometools.streaming.core.language import KNOWN_LANGUAGE_CODES
from hometools.streaming.core.media_overrides import OVERRIDE_FILENAME
from hometools.streaming.core.overrides_validator import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Issue,
    ValidationReport,
    validate_overrides,
)


def _write_yaml(folder: Path, data: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / OVERRIDE_FILENAME).write_text(yaml.dump(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# KNOWN_LANGUAGE_CODES sanity
# ---------------------------------------------------------------------------


class TestKnownLanguageCodes:
    def test_contains_expected_codes(self):
        assert {"en", "de", "fr"} <= KNOWN_LANGUAGE_CODES

    def test_is_immutable(self):
        with pytest.raises(AttributeError):
            KNOWN_LANGUAGE_CODES.add("xx")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Empty / clean libraries
# ---------------------------------------------------------------------------


class TestEmptyLibrary:
    def test_empty_library_has_no_issues(self, tmp_path: Path):
        r = validate_overrides(tmp_path)
        assert isinstance(r, ValidationReport)
        assert r.issues == []
        assert r.parsed_files == 0

    def test_nonexistent_library_returns_empty_report(self, tmp_path: Path):
        r = validate_overrides(tmp_path / "does_not_exist")
        assert r.issues == []
        assert r.parsed_files == 0

    def test_valid_override_produces_no_issues(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "ep1.mp4").write_bytes(b"")
        _write_yaml(
            show,
            {
                "series_title": "Show",
                "language": "de",
                "episodes": {"ep1.mp4": {"title": "Pilot", "language": "en"}},
            },
        )
        r = validate_overrides(tmp_path)
        assert r.parsed_files == 1
        assert r.issues == []


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_malformed_yaml_produces_parse_error(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / OVERRIDE_FILENAME).write_text("not: [valid: yaml: {{", encoding="utf-8")

        r = validate_overrides(tmp_path)
        codes = [i.code for i in r.issues]
        assert "parse_error" in codes
        err = next(i for i in r.issues if i.code == "parse_error")
        assert err.severity == SEVERITY_ERROR
        assert err.folder == "Show"
        assert r.has_errors

    def test_non_dict_yaml_produces_parse_error(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / OVERRIDE_FILENAME).write_text("- just\n- a\n- list\n", encoding="utf-8")

        r = validate_overrides(tmp_path)
        assert any(i.code == "parse_error" for i in r.issues)


# ---------------------------------------------------------------------------
# Unknown language codes
# ---------------------------------------------------------------------------


class TestUnknownLanguage:
    def test_unknown_folder_language(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"language": "xx"})
        r = validate_overrides(tmp_path)
        assert any(i.code == "unknown_language" and "xx" in i.message for i in r.issues)
        assert not r.has_errors  # warning only

    def test_unknown_subtitle_language(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"subtitle_language": "qq"})
        r = validate_overrides(tmp_path)
        assert any(i.code == "unknown_language" and "qq" in i.message for i in r.issues)

    def test_unknown_episode_language(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "ep.mp4").write_bytes(b"")
        _write_yaml(show, {"episodes": {"ep.mp4": {"language": "zz"}}})
        r = validate_overrides(tmp_path)
        assert any(i.code == "unknown_language" and "zz" in i.message for i in r.issues)

    def test_known_language_passes(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"language": "de", "subtitle_language": "en"})
        r = validate_overrides(tmp_path)
        assert not any(i.code == "unknown_language" for i in r.issues)


# ---------------------------------------------------------------------------
# Unknown episode keys
# ---------------------------------------------------------------------------


class TestUnknownEpisodeKey:
    def test_missing_file_triggers_warning(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "real.mp4").write_bytes(b"")
        _write_yaml(show, {"episodes": {"typo.mp4": {"title": "X"}}})
        r = validate_overrides(tmp_path)
        warns = [i for i in r.issues if i.code == "unknown_episode_key"]
        assert len(warns) == 1
        assert "typo.mp4" in warns[0].message
        assert warns[0].severity == SEVERITY_WARNING

    def test_existing_file_no_warning(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "ep.mp4").write_bytes(b"")
        _write_yaml(show, {"episodes": {"ep.mp4": {"title": "X"}}})
        r = validate_overrides(tmp_path)
        assert not any(i.code == "unknown_episode_key" for i in r.issues)


# ---------------------------------------------------------------------------
# Unknown top-level / episode fields (typo detection)
# ---------------------------------------------------------------------------


class TestUnknownFields:
    def test_unknown_top_level_key(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"series_titel": "X"})  # German typo
        r = validate_overrides(tmp_path)
        assert any(i.code == "unknown_field" and "series_titel" in i.message for i in r.issues)

    def test_unknown_episode_field(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "ep.mp4").write_bytes(b"")
        _write_yaml(show, {"episodes": {"ep.mp4": {"titlee": "X"}}})  # typo
        r = validate_overrides(tmp_path)
        assert any(i.code == "unknown_field" and "titlee" in i.message for i in r.issues)


# ---------------------------------------------------------------------------
# No-op + non-media extension hints
# ---------------------------------------------------------------------------


class TestInfoChecks:
    def test_empty_override_emits_info(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {})
        r = validate_overrides(tmp_path)
        assert any(i.code == "empty_override" and i.severity == SEVERITY_INFO for i in r.issues)

    def test_non_media_extension_emits_info(self, tmp_path: Path):
        show = tmp_path / "Show"
        show.mkdir()
        (show / "notes.txt").write_bytes(b"")
        _write_yaml(show, {"episodes": {"notes.txt": {"title": "X"}}})
        r = validate_overrides(tmp_path)
        assert any(i.code == "non_media_extension" and i.severity == SEVERITY_INFO for i in r.issues)


# ---------------------------------------------------------------------------
# Language-group cross-folder check
# ---------------------------------------------------------------------------


class TestLanguageGroupCollisions:
    def test_lonely_group_emits_info(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"language_group": "solo"})
        r = validate_overrides(tmp_path)
        assert any(i.code == "lonely_language_group" for i in r.issues)

    def test_two_folders_same_group_no_warning(self, tmp_path: Path):
        a = tmp_path / "ShowA"
        b = tmp_path / "ShowB"
        _write_yaml(a, {"language_group": "linked", "language": "de"})
        _write_yaml(b, {"language_group": "linked", "language": "en"})
        r = validate_overrides(tmp_path)
        assert not any(i.code == "lonely_language_group" for i in r.issues)


# ---------------------------------------------------------------------------
# Report API
# ---------------------------------------------------------------------------


class TestReportApi:
    def test_to_dict_shape(self, tmp_path: Path):
        show = tmp_path / "Show"
        _write_yaml(show, {"language": "xx"})
        d = validate_overrides(tmp_path).to_dict()
        assert "scanned_folders" in d
        assert "parsed_files" in d
        assert "issues" in d
        assert d["summary"]["total"] == len(d["issues"])
        assert d["summary"]["warnings"] >= 1

    def test_issue_is_frozen(self):
        from dataclasses import FrozenInstanceError

        i = Issue(folder="x", severity=SEVERITY_WARNING, code="foo", message="bar")
        with pytest.raises(FrozenInstanceError):
            i.folder = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CLI integration (handler invocation)
# ---------------------------------------------------------------------------


class TestCliHandler:
    def test_run_validate_overrides_returns_0_on_clean(self, tmp_path: Path, capsys):
        import argparse

        from hometools.cli import run_validate_overrides

        ns = argparse.Namespace(
            library_dir=tmp_path,
            json=False,
            fail_on_warning=False,
        )
        rc = run_validate_overrides(ns)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Keine Befunde" in out or "Gescannt:" in out

    def test_run_validate_overrides_returns_1_on_error(self, tmp_path: Path):
        import argparse

        from hometools.cli import run_validate_overrides

        show = tmp_path / "Show"
        show.mkdir()
        (show / OVERRIDE_FILENAME).write_text("not: [valid: {{", encoding="utf-8")

        ns = argparse.Namespace(library_dir=tmp_path, json=False, fail_on_warning=False)
        rc = run_validate_overrides(ns)
        assert rc == 1

    def test_run_validate_overrides_fail_on_warning(self, tmp_path: Path):
        import argparse

        from hometools.cli import run_validate_overrides

        show = tmp_path / "Show"
        _write_yaml(show, {"language": "xx"})  # warning only
        ns = argparse.Namespace(library_dir=tmp_path, json=False, fail_on_warning=True)
        rc = run_validate_overrides(ns)
        assert rc == 1

        ns2 = argparse.Namespace(library_dir=tmp_path, json=False, fail_on_warning=False)
        rc2 = run_validate_overrides(ns2)
        assert rc2 == 0

    def test_run_validate_overrides_json_output(self, tmp_path: Path, capsys):
        import argparse
        import json as _json

        from hometools.cli import run_validate_overrides

        show = tmp_path / "Show"
        _write_yaml(show, {"language": "xx"})
        ns = argparse.Namespace(library_dir=tmp_path, json=True, fail_on_warning=False)
        run_validate_overrides(ns)
        payload = _json.loads(capsys.readouterr().out)
        assert payload["summary"]["warnings"] >= 1
        assert any(i["code"] == "unknown_language" for i in payload["issues"])
