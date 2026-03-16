"""Tests for instruction file generation helpers."""

from pathlib import Path

from hometools.instructions import (
    SUB_INSTRUCTIONS,
    _list_py_modules,
    _list_test_files,
    render_instructions,
    update_instructions_file,
)


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project skeleton for testing."""
    (tmp_path / "src" / "hometools" / "audio").mkdir(parents=True)
    (tmp_path / "src" / "hometools" / "audio" / "__init__.py").write_text("")
    (tmp_path / "src" / "hometools" / "audio" / "sanitize.py").write_text("")
    (tmp_path / "src" / "hometools" / "audio" / "metadata.py").write_text("")
    (tmp_path / "src" / "hometools" / "video").mkdir(parents=True)
    (tmp_path / "src" / "hometools" / "video" / "organizer.py").write_text("")
    (tmp_path / "src" / "hometools" / "streaming" / "core").mkdir(parents=True)
    (tmp_path / "src" / "hometools" / "streaming" / "core" / "models.py").write_text("")
    (tmp_path / "src" / "hometools" / "streaming" / "core" / "catalog.py").write_text("")
    (tmp_path / "src" / "hometools" / "streaming" / "audio").mkdir(parents=True)
    (tmp_path / "src" / "hometools" / "streaming" / "audio" / "server.py").write_text("")
    (tmp_path / "src" / "hometools" / "streaming" / "video").mkdir(parents=True)
    (tmp_path / "src" / "hometools" / "streaming" / "video" / "catalog.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sanitize.py").write_text("")
    (tmp_path / "tests" / "test_streaming_core.py").write_text("")
    (tmp_path / "tests" / "test_streaming_audio_catalog.py").write_text("")
    (tmp_path / "tests" / "test_streaming_video.py").write_text("")
    return tmp_path


def test_list_py_modules(tmp_path):
    root = _make_project(tmp_path)
    modules = _list_py_modules(root, "audio")
    assert "sanitize" in modules
    assert "metadata" in modules
    assert "__init__" not in modules


def test_list_test_files(tmp_path):
    root = _make_project(tmp_path)
    files = _list_test_files(root, "test_streaming_audio")
    assert "test_streaming_audio_catalog.py" in files
    assert "test_streaming_core.py" not in files


def test_render_instructions_contains_architecture_table(tmp_path):
    content = render_instructions(tmp_path)
    assert "streaming.instructions.md" in content
    assert "tools.instructions.md" in content
    assert "Rules (global)" in content
    assert "Keep instructions lean" in content


def test_update_instructions_file_creates_main_and_subs(tmp_path):
    root = _make_project(tmp_path)
    main = update_instructions_file(root)

    assert main.exists()
    assert main.name == "INSTRUCTIONS.md"
    assert "INSTRUCTIONS" in main.read_text(encoding="utf-8")

    # All sub-files must exist
    sub_dir = root / ".github" / "instructions"
    for filename in SUB_INSTRUCTIONS:
        sub = sub_dir / filename
        assert sub.exists(), f"Missing: {sub}"


def test_update_removes_obsolete_files(tmp_path):
    root = _make_project(tmp_path)
    sub_dir = root / ".github" / "instructions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    # Create old files that should be cleaned up
    for old in ("streaming-core.instructions.md", "streaming-audio.instructions.md", "streaming-video.instructions.md"):
        (sub_dir / old).write_text("old")

    update_instructions_file(root)

    for old in ("streaming-core.instructions.md", "streaming-audio.instructions.md", "streaming-video.instructions.md"):
        assert not (sub_dir / old).exists(), f"Obsolete file not removed: {old}"


def test_sub_instructions_list_modules(tmp_path):
    root = _make_project(tmp_path)
    update_instructions_file(root)

    tools = (root / ".github" / "instructions" / "tools.instructions.md").read_text(encoding="utf-8")
    assert "sanitize.py" in tools
    assert "organizer.py" in tools

    streaming = (root / ".github" / "instructions" / "streaming.instructions.md").read_text(encoding="utf-8")
    assert "models.py" in streaming
    assert "catalog.py" in streaming
    assert "server.py" in streaming
