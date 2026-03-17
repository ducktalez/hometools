"""Tests for hometools.utils – file and path utilities."""

import subprocess
from unittest.mock import patch

from hometools.utils import (
    fix_spaces,
    get_file_size,
    get_files_in_folder,
    path_make_dir,
    remove_ugly_spaces,
    repath_fix_spaces,
    run_text_subprocess,
)


class TestFixSpaces:
    def test_collapses_double_spaces(self):
        assert fix_spaces("hello  world") == "hello world"

    def test_collapses_many_spaces(self):
        assert fix_spaces("a    b     c") == "a b c"

    def test_strips_leading(self):
        assert fix_spaces("  hello") == "hello"

    def test_strips_trailing(self):
        assert fix_spaces("hello  ") == "hello"

    def test_strips_both(self):
        assert fix_spaces("  hello  world  ") == "hello world"

    def test_no_change_needed(self):
        assert fix_spaces("already clean") == "already clean"

    def test_empty_string(self):
        assert fix_spaces("") == ""

    def test_only_spaces(self):
        assert fix_spaces("     ") == ""

    def test_aliases_work(self):
        """repath_fix_spaces and remove_ugly_spaces should behave identically."""
        test = "  hello   world  "
        assert repath_fix_spaces(test) == fix_spaces(test)
        assert remove_ugly_spaces(test) == fix_spaces(test)


class TestGetFilesInFolder:
    def test_finds_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.mp3").write_text("b")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("c")

        result = get_files_in_folder(tmp_path)
        assert len(result) == 3

    def test_filters_by_suffix(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.mp3").write_text("b")
        (tmp_path / "c.mp3").write_text("c")

        result = get_files_in_folder(tmp_path, suffix_accepted=[".mp3"])
        assert len(result) == 2
        assert all(f.suffix == ".mp3" for f in result)

    def test_empty_folder(self, tmp_path):
        result = get_files_in_folder(tmp_path)
        assert result == []

    def test_sorted_by_stem(self, tmp_path):
        (tmp_path / "zebra.txt").write_text("")
        (tmp_path / "alpha.txt").write_text("")
        (tmp_path / "middle.txt").write_text("")

        result = get_files_in_folder(tmp_path)
        stems = [f.stem for f in result]
        assert stems == sorted(stems)


class TestPathMakeDir:
    def test_creates_directory(self, tmp_path):
        new_dir = tmp_path / "new" / "nested"
        path_make_dir(new_dir)
        assert new_dir.exists()

    def test_creates_parent_for_file(self, tmp_path):
        file_path = tmp_path / "new" / "file.txt"
        result = path_make_dir(file_path)
        assert file_path.parent.exists()
        assert result == file_path


class TestGetFileSize:
    def test_returns_size(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        size = get_file_size(f)
        assert size == len("hello world")


class TestRunTextSubprocess:
    def test_forces_utf8_text_defaults(self):
        expected = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

        with patch("hometools.utils.subprocess.run", return_value=expected) as mocked_run:
            result = run_text_subprocess(["ffprobe", "-version"], capture_output=True)

        assert result is expected
        _args, kwargs = mocked_run.call_args
        assert kwargs["text"] is True
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        assert kwargs["capture_output"] is True
