"""Tests for instruction file generation helpers."""

from hometools.instructions import render_instructions, update_instructions_file


def test_render_instructions_contains_tree_and_commands(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# demo")

    content = render_instructions(tmp_path)

    assert "Project Structure" in content
    assert "hometools update-instructions" in content
    assert "README.md" in content


def test_update_instructions_file_writes_to_github_path(tmp_path):
    target = update_instructions_file(tmp_path)

    assert target.exists()
    assert target.name == "INSTRUCTIONS.md"
    assert "Last updated:" in target.read_text(encoding="utf-8")

