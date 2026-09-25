"""Unified streaming setup — configure, inspect and launch all three servers.

Run ``hometools serve-all`` to start audio + video + channel on separate ports.
Run ``hometools streaming-config`` to see the current configuration.
Run ``hometools setup-pycharm`` to generate PyCharm run configurations.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent

from hometools.config import (
    get_audio_library_dir,
    get_audio_port,
    get_channel_port,
    get_channel_schedule_file,
    get_player_bar_style,
    get_stream_host,
    get_video_library_dir,
    get_video_port,
)

logger = logging.getLogger(__name__)


def _console_print(text: str = "") -> None:
    """Print text safely even on consoles without full Unicode support."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        sanitized = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)


# ---------------------------------------------------------------------------
# Config overview
# ---------------------------------------------------------------------------


def streaming_config_table() -> str:
    """Return a human-readable table of the current streaming configuration."""
    host = get_stream_host()
    audio_port = get_audio_port()
    video_port = get_video_port()
    channel_port = get_channel_port()
    audio_dir = str(get_audio_library_dir())
    video_dir = str(get_video_library_dir())
    audio_url = f"http://{host}:{audio_port}/"
    video_url = f"http://{host}:{video_port}/"
    channel_url = f"http://{host}:{channel_port}/"
    bar_style = get_player_bar_style()

    # Adapt column width to longest value
    values = [
        host,
        f"port {audio_port}",
        audio_dir,
        f"port {video_port}",
        video_dir,
        f"port {channel_port}",
        audio_url,
        video_url,
        channel_url,
        bar_style,
    ]
    w = max(len(v) for v in values) + 2

    def row(label: str, value: str) -> str:
        return f"│  {label:<8s}│  {value:<{w}s}│"

    sep = f"├──────────┼{'─' * (w + 2)}┤"
    top = f"┌──────────┬{'─' * (w + 2)}┐"
    bot = f"└──────────┴{'─' * (w + 2)}┘"
    title = f"│  {'hometools streaming configuration':<{w + 8}s}│"

    lines = [
        top,
        title,
        sep,
        row("Host", host),
        sep,
        row("Audio", f"port {audio_port}"),
        row("", audio_dir),
        sep,
        row("Video", f"port {video_port}"),
        row("", video_dir),
        sep,
        row("Channel", f"port {channel_port}"),
        sep,
        row("Player", bar_style),
        sep,
        row("URLs", audio_url),
        row("", video_url),
        row("", channel_url),
        bot,
    ]
    return "\n".join(lines)


def print_streaming_config() -> None:
    """Print the current streaming configuration to stdout."""
    _console_print(streaming_config_table())


# ---------------------------------------------------------------------------
# Dual-server launcher
# ---------------------------------------------------------------------------


def _build_serve_subprocess_command(
    command: str,
    *,
    host: str,
    port: int,
    library_dir: Path,
    safe_mode: bool = False,
    schedule_file: Path | None = None,
) -> list[str]:
    """Return the subprocess command used by ``serve_all``.

    Audio and video are launched as separate Python processes so they do not
    share in-process globals such as thumbnail workers or index caches.
    """
    cmd = [
        sys.executable,
        "-m",
        "hometools",
        command,
        "--host",
        host,
        "--port",
        str(port),
        "--library-dir",
        str(library_dir),
    ]
    if safe_mode:
        cmd.append("--safe-mode")
    if schedule_file is not None:
        cmd.extend(["--schedule", str(schedule_file)])
    return cmd


def serve_all(
    audio_dir: Path | None = None,
    video_dir: Path | None = None,
    host: str | None = None,
    audio_port: int | None = None,
    video_port: int | None = None,
    channel_port: int | None = None,
    safe_mode: bool = False,
    channel_schedule: Path | None = None,
) -> None:
    """Start audio, video and channel streaming servers on separate ports.

    Runs each server in its own subprocess to avoid shared-process coupling
    between audio, video and channel (thumbnail worker globals, index rebuild
    locks, cold-start file scans, etc.).  Blocks until interrupted (Ctrl+C).
    """
    resolved_host = host or get_stream_host()
    resolved_audio_port = audio_port or get_audio_port()
    resolved_video_port = video_port or get_video_port()
    resolved_channel_port = channel_port or get_channel_port()
    resolved_audio_dir = audio_dir or get_audio_library_dir()
    resolved_video_dir = video_dir or get_video_library_dir()
    resolved_schedule = channel_schedule or get_channel_schedule_file()

    audio_cmd = _build_serve_subprocess_command(
        "serve-audio",
        host=resolved_host,
        port=resolved_audio_port,
        library_dir=resolved_audio_dir,
        safe_mode=safe_mode,
    )
    video_cmd = _build_serve_subprocess_command(
        "serve-video",
        host=resolved_host,
        port=resolved_video_port,
        library_dir=resolved_video_dir,
        safe_mode=safe_mode,
    )
    channel_cmd = _build_serve_subprocess_command(
        "serve-channel",
        host=resolved_host,
        port=resolved_channel_port,
        library_dir=resolved_video_dir,
        schedule_file=resolved_schedule,
    )

    logger.info("serve-all launching audio subprocess: %s", audio_cmd)
    logger.info("serve-all launching video subprocess: %s", video_cmd)
    logger.info("serve-all launching channel subprocess: %s", channel_cmd)

    _console_print(f"🎵  Audio server   → http://{resolved_host}:{resolved_audio_port}/")
    _console_print(f"🎬  Video server   → http://{resolved_host}:{resolved_video_port}/")
    _console_print(f"📺  Channel server → http://{resolved_host}:{resolved_channel_port}/")
    _console_print("Press Ctrl+C to stop all servers.\n")

    audio_proc = subprocess.Popen(audio_cmd)
    video_proc = subprocess.Popen(video_cmd)
    channel_proc = subprocess.Popen(channel_cmd)
    logger.info(
        "serve-all subprocesses started: audio pid=%s, video pid=%s, channel pid=%s",
        audio_proc.pid,
        video_proc.pid,
        channel_proc.pid,
    )

    procs = [
        (audio_proc, "audio"),
        (video_proc, "video"),
        (channel_proc, "channel"),
    ]

    try:
        while True:
            for proc, name in procs:
                rc = proc.poll()
                if rc is not None:
                    logger.warning("serve-all child exit detected: %s rc=%s", name, rc)
                    break
            else:
                time.sleep(0.5)
                continue
            break
    except KeyboardInterrupt:
        logger.info("serve-all interrupted by user — stopping child processes")
    finally:
        for proc, name in procs:
            if proc.poll() is None:
                logger.info("Stopping %s subprocess pid=%s", name, proc.pid)
                proc.terminate()
        for proc, name in procs:
            try:
                proc.wait(timeout=5)
                logger.info("%s subprocess exited with rc=%s", name, proc.returncode)
            except subprocess.TimeoutExpired:
                logger.warning("%s subprocess did not exit in time — killing pid=%s", name, proc.pid)
                proc.kill()
                proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# PyCharm run-configuration generator
# ---------------------------------------------------------------------------

_PYCHARM_SDK_FALLBACK = "Python 3 (hometools)"

#: Name of the webui-build configuration — referenced as a before-launch
#: task by every server config, so both sides must use this constant.
_WEBUI_BUILD_CONFIG_NAME = "Build WebUI"


def _detect_pycharm_sdk_name(project_root: Path) -> str:
    """Return the Python SDK name PyCharm currently has bound to this project.

    Reads ``jdkName`` from ``.idea/<module>.iml`` — the same value PyCharm
    itself maintains whenever the interpreter is changed via
    Settings > Project > Python Interpreter. This must match an entry in
    PyCharm's (per-user, per-machine) ``jdk.table.xml`` for a generated run
    configuration's ``SDK_NAME`` to resolve; that table is user/machine-local
    and PyCharm often names path-based interpreters after their relative
    path (e.g. ``~\\PycharmProjects\\hometools\\.venv``), not a friendly
    name — so this must never be hardcoded here. Falls back to a generic
    placeholder (and logs a warning) if no ``.iml`` file is found yet, e.g.
    on a machine that hasn't opened the project in PyCharm at all.
    """
    idea_dir = project_root / ".idea"
    if idea_dir.is_dir():
        for iml_path in idea_dir.glob("*.iml"):
            try:
                import re

                text = iml_path.read_text(encoding="utf-8")
                match = re.search(r'jdkName="([^"]+)"', text)
                if match:
                    return match.group(1)
            except OSError:
                continue
    logger.warning(
        "Could not detect PyCharm SDK name from %s/*.iml — using fallback %r. "
        "Open the project in PyCharm once (so it writes the .iml file), then "
        "re-run 'hometools setup-pycharm'.",
        idea_dir,
        _PYCHARM_SDK_FALLBACK,
    )
    return _PYCHARM_SDK_FALLBACK


def _make_python_config(
    name: str,
    module: str,
    parameters: str,
    *,
    sdk_name: str,
    env_vars: dict[str, str] | None = None,
    before_launch: str | None = None,
) -> Element:
    """Build an XML element for a PyCharm Python run configuration.

    *before_launch* is the name of another run configuration to execute
    first (used to wire the webui build in front of every server start —
    see :func:`generate_pycharm_configs`).
    """
    root = Element("component", attrib={"name": "ProjectRunConfigurationManager"})
    cfg = SubElement(
        root,
        "configuration",
        attrib={
            "default": "false",
            "name": name,
            "type": "PythonConfigurationType",
            "factoryName": "Python",
        },
    )
    SubElement(cfg, "module", attrib={"name": "hometools"})

    SubElement(cfg, "option", attrib={"name": "INTERPRETER_OPTIONS", "value": ""})
    SubElement(cfg, "option", attrib={"name": "PARENT_ENVS", "value": "true"})

    if env_vars:
        envs = SubElement(cfg, "envs")
        for k, v in env_vars.items():
            SubElement(envs, "env", attrib={"name": k, "value": v})

    SubElement(cfg, "option", attrib={"name": "SDK_HOME", "value": ""})
    SubElement(cfg, "option", attrib={"name": "SDK_NAME", "value": sdk_name})
    SubElement(cfg, "option", attrib={"name": "WORKING_DIRECTORY", "value": "$PROJECT_DIR$"})
    SubElement(cfg, "option", attrib={"name": "IS_MODULE_SDK", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_CONTENT_ROOTS", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_SOURCE_ROOTS", "value": "true"})

    SubElement(cfg, "option", attrib={"name": "SCRIPT_NAME", "value": module})
    SubElement(cfg, "option", attrib={"name": "PARAMETERS", "value": parameters})
    SubElement(cfg, "option", attrib={"name": "SHOW_COMMAND_LINE", "value": "false"})
    SubElement(cfg, "option", attrib={"name": "EMULATE_TERMINAL", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "MODULE_MODE", "value": "true"})

    method = SubElement(cfg, "method", attrib={"v": "2"})
    if before_launch:
        # Only emit the before-launch task when it has a real target — an
        # empty run_configuration_name is a no-op task PyCharm shows as a
        # broken "<none>" entry in the run configuration dialog.
        SubElement(
            method,
            "option",
            attrib={
                "name": "RunConfigurationTask",
                "enabled": "true",
                "run_configuration_name": before_launch,
                "run_configuration_type": "PythonConfigurationType",
            },
        )

    return root


def _make_pytest_config(name: str, target: str, *, sdk_name: str, parameters: str = "") -> Element:
    """Build an XML element for a PyCharm pytest run configuration."""
    root = Element("component", attrib={"name": "ProjectRunConfigurationManager"})
    cfg = SubElement(
        root,
        "configuration",
        attrib={
            "default": "false",
            "name": name,
            "type": "tests",
            "factoryName": "py.test",
        },
    )
    SubElement(cfg, "module", attrib={"name": "hometools"})
    SubElement(cfg, "option", attrib={"name": "INTERPRETER_OPTIONS", "value": ""})
    SubElement(cfg, "option", attrib={"name": "PARENT_ENVS", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "SDK_HOME", "value": ""})
    SubElement(cfg, "option", attrib={"name": "SDK_NAME", "value": sdk_name})
    SubElement(cfg, "option", attrib={"name": "WORKING_DIRECTORY", "value": "$PROJECT_DIR$"})
    SubElement(cfg, "option", attrib={"name": "IS_MODULE_SDK", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_CONTENT_ROOTS", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_SOURCE_ROOTS", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "SCRIPT_NAME", "value": target})
    SubElement(cfg, "option", attrib={"name": "PARAMETERS", "value": parameters})
    SubElement(cfg, "option", attrib={"name": "SHOW_COMMAND_LINE", "value": "false"})
    SubElement(cfg, "option", attrib={"name": "EMULATE_TERMINAL", "value": "true"})
    SubElement(cfg, "method", attrib={"v": "2"})
    return root


def _make_compound_config(name: str, child_configs: list[tuple[str, str]]) -> Element:
    """Build an XML element for a PyCharm Compound run configuration.

    Each entry in *child_configs* is ``(name, type)`` — e.g.
    ``("Serve Audio", "PythonConfigurationType")``.
    """
    root = Element("component", attrib={"name": "ProjectRunConfigurationManager"})
    cfg = SubElement(
        root,
        "configuration",
        attrib={
            "default": "false",
            "name": name,
            "type": "CompoundRunConfigurationType",
        },
    )
    for child_name, child_type in child_configs:
        SubElement(cfg, "toRun", attrib={"name": child_name, "type": child_type})
    return root


def generate_pycharm_configs(project_root: Path) -> list[Path]:
    """Write PyCharm run configurations for streaming + dev commands.

    Covers everything the README's "PyCharm Run-Konfigurationen" table
    lists, so a fresh clone gets the full set from one command (``.idea/``
    is git-ignored — these files are never committed).

    ``Serve All`` is a **Compound** configuration so that PyCharm runs
    audio, video and channel as separate processes — each with its own
    Stop button.

    Every ``Serve *`` configuration runs ``Build WebUI`` first: without a
    current ``streaming/core/static/`` bundle the player UI silently loses
    all ported TS/CSS modules (see ``streaming/webui_build.py``). The build
    is a no-op when the bundle is already up to date, so this costs
    nothing on a normal start.

    Returns the list of created files.
    """
    run_cfg_dir = project_root / ".idea" / "runConfigurations"
    run_cfg_dir.mkdir(parents=True, exist_ok=True)
    sdk_name = _detect_pycharm_sdk_name(project_root)

    created: list[Path] = []

    def _write(xml_root: Element, filename: str) -> None:
        target = run_cfg_dir / filename
        tree = ElementTree(xml_root)
        indent(tree, space="  ")
        tree.write(str(target), encoding="UTF-8", xml_declaration=True)
        created.append(target)
        logger.info("Created run configuration: %s", target)

    # Build the webui bundle first — referenced as a before-launch task by
    # every server configuration below.
    _write(
        _make_python_config(_WEBUI_BUILD_CONFIG_NAME, "hometools", "build-webui", sdk_name=sdk_name),
        "build_webui.xml",
    )

    # Server configurations (webui build wired in front of each).
    for name, params, filename in (
        ("Serve Audio", "serve-audio", "serve_audio.xml"),
        ("Serve Video", "serve-video", "serve_video.xml"),
        ("Serve Channel", "serve-channel", "serve_channel.xml"),
    ):
        _write(
            _make_python_config(
                name,
                "hometools",
                params,
                sdk_name=sdk_name,
                before_launch=_WEBUI_BUILD_CONFIG_NAME,
            ),
            filename,
        )

    # Non-server CLI helpers.
    for name, params, filename in (
        ("Streaming Config", "streaming-config", "streaming_config.xml"),
        ("Dashboard", "stream-dashboard", "dashboard.xml"),
    ):
        _write(_make_python_config(name, "hometools", params, sdk_name=sdk_name), filename)

    # Lint/format (ruff is a console script, not the hometools module).
    _write(
        _make_python_config("Ruff Check + Format", "ruff", "check src/ tests/ --fix", sdk_name=sdk_name),
        "ruff_check.xml",
    )

    # Test configurations.
    _write(_make_pytest_config("Run Tests", "$PROJECT_DIR$/tests", sdk_name=sdk_name, parameters="-q"), "run_tests.xml")
    _write(
        _make_pytest_config(
            "Feature Parity Tests",
            "$PROJECT_DIR$/tests/test_feature_parity.py",
            sdk_name=sdk_name,
            parameters="-v",
        ),
        "feature_parity_tests.xml",
    )

    # Compound configuration: starts all three servers as separate processes
    _write(
        _make_compound_config(
            "Serve All",
            [
                ("Serve Audio", "PythonConfigurationType"),
                ("Serve Video", "PythonConfigurationType"),
                ("Serve Channel", "PythonConfigurationType"),
            ],
        ),
        "serve_all.xml",
    )

    return created
