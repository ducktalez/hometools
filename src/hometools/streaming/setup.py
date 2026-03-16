"""Unified streaming setup — configure, inspect and launch both servers.

Run ``hometools serve-all`` to start audio + video on separate ports.
Run ``hometools streaming-config`` to see the current configuration.
Run ``hometools setup-pycharm`` to generate PyCharm run configurations.
"""

from __future__ import annotations

import logging
import textwrap
import threading
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from hometools.config import (
    get_audio_library_dir,
    get_audio_port,
    get_player_bar_style,
    get_stream_host,
    get_video_library_dir,
    get_video_port,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config overview
# ---------------------------------------------------------------------------


def streaming_config_table() -> str:
    """Return a human-readable table of the current streaming configuration."""
    host = get_stream_host()
    audio_port = get_audio_port()
    video_port = get_video_port()
    audio_dir = str(get_audio_library_dir())
    video_dir = str(get_video_library_dir())
    audio_url = f"http://{host}:{audio_port}/"
    video_url = f"http://{host}:{video_port}/"
    bar_style = get_player_bar_style()

    # Adapt column width to longest value
    values = [host, f"port {audio_port}", audio_dir, f"port {video_port}", video_dir, audio_url, video_url, bar_style]
    w = max(len(v) for v in values) + 2

    def row(label: str, value: str) -> str:
        return f"│  {label:<8s}│  {value:<{w}s}│"

    sep = f"├──────────┼{'─' * (w + 2)}┤"
    top = f"┌──────────┬{'─' * (w + 2)}┐"
    bot = f"└──────────┴{'─' * (w + 2)}┘"
    title = f"│  {'hometools streaming configuration':<{w + 8}s}│"

    lines = [
        top, title, sep,
        row("Host", host), sep,
        row("Audio", f"port {audio_port}"),
        row("", audio_dir), sep,
        row("Video", f"port {video_port}"),
        row("", video_dir), sep,
        row("Player", bar_style), sep,
        row("URLs", audio_url),
        row("", video_url),
        bot,
    ]
    return "\n".join(lines)


def print_streaming_config() -> None:
    """Print the current streaming configuration to stdout."""
    print(streaming_config_table())


# ---------------------------------------------------------------------------
# Dual-server launcher
# ---------------------------------------------------------------------------


def serve_all(
    audio_dir: Path | None = None,
    video_dir: Path | None = None,
    host: str | None = None,
    audio_port: int | None = None,
    video_port: int | None = None,
) -> None:
    """Start audio and video streaming servers on separate ports.

    Blocks until interrupted (Ctrl+C).
    """
    import uvicorn

    resolved_host = host or get_stream_host()
    resolved_audio_port = audio_port or get_audio_port()
    resolved_video_port = video_port or get_video_port()
    resolved_audio_dir = audio_dir or get_audio_library_dir()
    resolved_video_dir = video_dir or get_video_library_dir()

    # Lazy imports to keep startup fast
    from hometools.streaming.audio.server import create_app as create_audio_app
    from hometools.streaming.video.server import create_app as create_video_app

    audio_app = create_audio_app(resolved_audio_dir)
    video_app = create_video_app(resolved_video_dir)

    audio_cfg = uvicorn.Config(audio_app, host=resolved_host, port=resolved_audio_port)
    video_cfg = uvicorn.Config(video_app, host=resolved_host, port=resolved_video_port)

    audio_server = uvicorn.Server(audio_cfg)
    video_server = uvicorn.Server(video_cfg)

    print(f"🎵  Audio server → http://{resolved_host}:{resolved_audio_port}/")
    print(f"🎬  Video server → http://{resolved_host}:{resolved_video_port}/")
    print("Press Ctrl+C to stop both servers.\n")

    # Run video in a daemon thread, audio on the main thread so Ctrl+C works.
    video_thread = threading.Thread(target=video_server.run, daemon=True)
    video_thread.start()

    try:
        audio_server.run()
    finally:
        video_server.should_exit = True
        video_thread.join(timeout=3)


# ---------------------------------------------------------------------------
# PyCharm run-configuration generator
# ---------------------------------------------------------------------------

_PYCHARM_SDK = "Python 3.10 (hometools-env)"


def _make_python_config(
    name: str,
    module: str,
    parameters: str,
    *,
    env_vars: dict[str, str] | None = None,
) -> Element:
    """Build an XML element for a PyCharm Python run configuration."""
    root = Element("component", attrib={"name": "ProjectRunConfigurationManager"})
    cfg = SubElement(root, "configuration", attrib={
        "default": "false",
        "name": name,
        "type": "PythonConfigurationType",
        "factoryName": "Python",
    })
    SubElement(cfg, "module", attrib={"name": "hometools"})

    SubElement(cfg, "option", attrib={"name": "INTERPRETER_OPTIONS", "value": ""})
    SubElement(cfg, "option", attrib={"name": "PARENT_ENVS", "value": "true"})

    if env_vars:
        envs = SubElement(cfg, "envs")
        for k, v in env_vars.items():
            SubElement(envs, "env", attrib={"name": k, "value": v})

    SubElement(cfg, "option", attrib={"name": "SDK_HOME", "value": ""})
    SubElement(cfg, "option", attrib={"name": "SDK_NAME", "value": _PYCHARM_SDK})
    SubElement(cfg, "option", attrib={"name": "WORKING_DIRECTORY", "value": "$PROJECT_DIR$"})
    SubElement(cfg, "option", attrib={"name": "IS_MODULE_SDK", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_CONTENT_ROOTS", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "ADD_SOURCE_ROOTS", "value": "true"})

    SubElement(cfg, "option", attrib={"name": "SCRIPT_NAME", "value": "hometools"})
    SubElement(cfg, "option", attrib={"name": "PARAMETERS", "value": parameters})
    SubElement(cfg, "option", attrib={"name": "SHOW_COMMAND_LINE", "value": "false"})
    SubElement(cfg, "option", attrib={"name": "EMULATE_TERMINAL", "value": "true"})
    SubElement(cfg, "option", attrib={"name": "MODULE_MODE", "value": "true"})

    method = SubElement(cfg, "method", attrib={"v": "2"})
    SubElement(method, "option", attrib={
        "name": "RunConfigurationTask",
        "enabled": "true",
        "run_configuration_name": "",
        "run_configuration_type": "PythonConfigurationType",
    })

    return root


def _make_compound_config(name: str, child_configs: list[tuple[str, str]]) -> Element:
    """Build an XML element for a PyCharm Compound run configuration.

    Each entry in *child_configs* is ``(name, type)`` — e.g.
    ``("Serve Audio", "PythonConfigurationType")``.
    """
    root = Element("component", attrib={"name": "ProjectRunConfigurationManager"})
    cfg = SubElement(root, "configuration", attrib={
        "default": "false",
        "name": name,
        "type": "CompoundRunConfigurationType",
    })
    for child_name, child_type in child_configs:
        SubElement(cfg, "toRun", attrib={"name": child_name, "type": child_type})
    return root


def generate_pycharm_configs(project_root: Path) -> list[Path]:
    """Write PyCharm run configurations for streaming commands.

    ``Serve All`` is a **Compound** configuration so that PyCharm runs
    audio and video as separate processes — each with its own Stop button.

    Returns the list of created files.
    """
    run_cfg_dir = project_root / ".idea" / "runConfigurations"
    run_cfg_dir.mkdir(parents=True, exist_ok=True)

    # Individual Python run configurations
    python_configs = [
        ("Serve Audio", "hometools", "serve-audio", "serve_audio.xml"),
        ("Serve Video", "hometools", "serve-video", "serve_video.xml"),
        ("Streaming Config", "hometools", "streaming-config", "streaming_config.xml"),
    ]

    created: list[Path] = []
    for name, module, params, filename in python_configs:
        xml_root = _make_python_config(name, module, params)
        target = run_cfg_dir / filename
        tree = ElementTree(xml_root)
        indent(tree, space="  ")
        tree.write(str(target), encoding="UTF-8", xml_declaration=True)
        created.append(target)
        logger.info("Created run configuration: %s", target)

    # Compound configuration: starts both servers as separate processes
    compound_root = _make_compound_config("Serve All", [
        ("Serve Audio", "PythonConfigurationType"),
        ("Serve Video", "PythonConfigurationType"),
    ])
    compound_target = run_cfg_dir / "serve_all.xml"
    compound_tree = ElementTree(compound_root)
    indent(compound_tree, space="  ")
    compound_tree.write(str(compound_target), encoding="UTF-8", xml_declaration=True)
    created.append(compound_target)
    logger.info("Created compound run configuration: %s", compound_target)

    return created


