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

    assert len(created) == 10
    for p in created:
        assert p.exists()

    names = {p.name for p in created}
    # Servers + webui build
    assert "serve_all.xml" in names
    assert "serve_audio.xml" in names
    assert "serve_video.xml" in names
    assert "serve_channel.xml" in names
    assert "build_webui.xml" in names
    # Dev helpers — the README's config table promises these too, so the
    # generator must produce the full set (.idea/ is git-ignored, a fresh
    # clone has nothing until 'hometools setup-pycharm' runs).
    assert "streaming_config.xml" in names
    assert "dashboard.xml" in names
    assert "ruff_check.xml" in names
    assert "run_tests.xml" in names
    assert "feature_parity_tests.xml" in names

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


def test_serve_configs_build_webui_before_launch(tmp_path):
    """Every server config must run 'Build WebUI' first — a stale/missing
    streaming/core/static/ bundle silently drops all ported TS/CSS modules
    from the player UI (see streaming/webui_build.py)."""
    generate_pycharm_configs(tmp_path)
    cfg_dir = tmp_path / ".idea" / "runConfigurations"
    for filename in ("serve_audio.xml", "serve_video.xml", "serve_channel.xml"):
        content = (cfg_dir / filename).read_text(encoding="utf-8")
        assert 'run_configuration_name="Build WebUI"' in content, filename

    build_content = (cfg_dir / "build_webui.xml").read_text(encoding="utf-8")
    assert 'value="build-webui"' in build_content


def test_generated_configs_have_no_empty_before_launch_task(tmp_path):
    """An empty run_configuration_name is a no-op before-launch task that
    PyCharm renders as a broken '<none>' entry — never emit one."""
    generate_pycharm_configs(tmp_path)
    for path in (tmp_path / ".idea" / "runConfigurations").iterdir():
        assert 'run_configuration_name=""' not in path.read_text(encoding="utf-8"), path.name


def test_test_configs_use_pytest_factory(tmp_path):
    """Run Tests / Feature Parity Tests must be pytest configurations, not
    plain Python module runs (PyCharm needs the test-runner integration)."""
    generate_pycharm_configs(tmp_path)
    cfg_dir = tmp_path / ".idea" / "runConfigurations"
    for filename in ("run_tests.xml", "feature_parity_tests.xml"):
        content = (cfg_dir / filename).read_text(encoding="utf-8")
        assert 'factoryName="py.test"' in content, filename


def test_ruff_config_runs_ruff_not_hometools(tmp_path):
    """The lint config must invoke the 'ruff' module, not the hometools CLI."""
    generate_pycharm_configs(tmp_path)
    content = (tmp_path / ".idea" / "runConfigurations" / "ruff_check.xml").read_text(encoding="utf-8")
    assert '<option name="SCRIPT_NAME" value="ruff" />' in content


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
