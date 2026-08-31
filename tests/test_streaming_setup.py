"""Tests for the streaming setup module."""

from hometools.streaming.setup import (
    _PYCHARM_SDK_FALLBACK,
    _build_serve_subprocess_command,
    _detect_pycharm_sdk_name,
    generate_pycharm_configs,
    streaming_config_table,
)


def test_streaming_config_table_contains_ports(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_AUDIO_PORT", "9000")
    monkeypatch.setenv("HOMETOOLS_VIDEO_PORT", "9001")
    table = streaming_config_table()
    assert "9000" in table
    assert "9001" in table


def test_streaming_config_table_contains_urls(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_STREAM_HOST", "0.0.0.0")
    table = streaming_config_table()
    assert "0.0.0.0" in table
    assert "http://" in table


def test_generate_pycharm_configs_creates_files(tmp_path):
    created = generate_pycharm_configs(tmp_path)

    assert len(created) == 5
    for p in created:
        assert p.exists()

    names = {p.name for p in created}
    assert "serve_all.xml" in names
    assert "serve_audio.xml" in names
    assert "serve_video.xml" in names
    assert "serve_channel.xml" in names

    # Individual configs are Python run configurations
    audio_content = (tmp_path / ".idea" / "runConfigurations" / "serve_audio.xml").read_text(encoding="utf-8")
    assert "PythonConfigurationType" in audio_content
    assert "hometools" in audio_content

    # Serve All is a Compound config referencing all three servers
    compound_content = (tmp_path / ".idea" / "runConfigurations" / "serve_all.xml").read_text(encoding="utf-8")
    assert "CompoundRunConfigurationType" in compound_content
    assert "Serve Audio" in compound_content
    assert "Serve Video" in compound_content
    assert "Serve Channel" in compound_content


def test_generate_pycharm_configs_idempotent(tmp_path):
    generate_pycharm_configs(tmp_path)
    first_contents = {p.name: p.read_text(encoding="utf-8") for p in (tmp_path / ".idea" / "runConfigurations").iterdir()}
    generate_pycharm_configs(tmp_path)
    second_contents = {p.name: p.read_text(encoding="utf-8") for p in (tmp_path / ".idea" / "runConfigurations").iterdir()}
    assert first_contents == second_contents


def test_build_serve_subprocess_command_contains_explicit_runtime_values(tmp_path):
    cmd = _build_serve_subprocess_command(
        "serve-video",
        host="0.0.0.0",
        port=8011,
        library_dir=tmp_path,
    )

    assert cmd[0]
    assert cmd[1:4] == ["-m", "hometools", "serve-video"]
    assert "--host" in cmd and "0.0.0.0" in cmd
    assert "--port" in cmd and "8011" in cmd
    assert "--library-dir" in cmd and str(tmp_path) in cmd


def test_build_serve_subprocess_command_appends_safe_mode_flag(tmp_path):
    cmd = _build_serve_subprocess_command(
        "serve-audio",
        host="127.0.0.1",
        port=8010,
        library_dir=tmp_path,
        safe_mode=True,
    )

    assert cmd[-1] == "--safe-mode"


def test_detect_pycharm_sdk_name_reads_iml_jdk_name(tmp_path):
    """Must read the *actual* jdkName PyCharm wrote to the .iml file.

    Regression guard: a previous version hardcoded a fixed SDK name
    constant (e.g. "Python 3.10 (hometools-env)") in generated run
    configurations. That name silently drifted from PyCharm's real,
    per-machine SDK table entry (PyCharm often names path-based
    interpreters after their relative path, e.g.
    "~\\PycharmProjects\\hometools\\.venv") — every generated run
    configuration then failed to resolve its interpreter. Detecting the
    name dynamically from the project's own .iml file keeps this in sync
    automatically, regardless of user/machine/interpreter naming.
    """
    idea_dir = tmp_path / ".idea"
    idea_dir.mkdir()
    (idea_dir / "myproject.iml").write_text(
        '<module type="PYTHON_MODULE" version="4">'
        '<component name="NewModuleRootManager">'
        '<orderEntry type="jdk" jdkName="~\\Some\\Custom\\.venv" jdkType="Python SDK" />'
        "</component></module>",
        encoding="utf-8",
    )
    assert _detect_pycharm_sdk_name(tmp_path) == "~\\Some\\Custom\\.venv"


def test_detect_pycharm_sdk_name_falls_back_when_no_iml(tmp_path):
    assert _detect_pycharm_sdk_name(tmp_path) == _PYCHARM_SDK_FALLBACK


def test_generate_pycharm_configs_uses_detected_sdk_name(tmp_path):
    """Generated configs must reference the real .iml SDK name, not a stale hardcoded one."""
    idea_dir = tmp_path / ".idea"
    idea_dir.mkdir()
    (idea_dir / "myproject.iml").write_text(
        '<module type="PYTHON_MODULE" version="4">'
        '<component name="NewModuleRootManager">'
        '<orderEntry type="jdk" jdkName="~\\Real\\Detected\\.venv" jdkType="Python SDK" />'
        "</component></module>",
        encoding="utf-8",
    )
    generate_pycharm_configs(tmp_path)
    audio_content = (tmp_path / ".idea" / "runConfigurations" / "serve_audio.xml").read_text(encoding="utf-8")
    assert "~\\Real\\Detected\\.venv" in audio_content
    assert "hometools-env" not in audio_content
