"""Command-line entry points for hometools."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_audio_port,
    get_stream_host,
    get_video_library_dir,
    get_video_nas_dir,
    get_video_port,
)
from hometools.instructions import update_instructions_file
from hometools.logging_config import setup_logging


def _add_serve_parser(subparsers, name: str, help_text: str, func):
    """Add a serve-* subcommand with common --library-dir/--host/--port arguments."""
    p = subparsers.add_parser(name, help=help_text)
    p.add_argument("--library-dir", type=Path, default=None, help="Local library directory.")
    p.add_argument("--host", default=None, help="Bind host.")
    p.add_argument("--port", type=int, default=None, help="Bind port.")
    p.set_defaults(func=func)
    return p


def _add_sync_parser(subparsers, name: str, help_text: str, func):
    """Add a sync-* subcommand with common --source/--target/--dry-run arguments."""
    p = subparsers.add_parser(name, help=help_text)
    p.add_argument("--source", type=Path, default=None, help="Mounted NAS source directory.")
    p.add_argument("--target", type=Path, default=None, help="Local library directory.")
    p.add_argument("--dry-run", action="store_true", help="Show what would be copied.")
    p.set_defaults(func=func)
    return p


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="hometools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audio
    _add_serve_parser(subparsers, "serve-audio", "Start the local audio streaming web UI.", run_serve_audio)
    _add_sync_parser(subparsers, "sync-audio", "Copy new/changed audio files from NAS to library.", run_sync_audio)

    # Video
    _add_serve_parser(subparsers, "serve-video", "Start the local video streaming web UI.", run_serve_video)
    _add_sync_parser(subparsers, "sync-video", "Copy new/changed video files from NAS to library.", run_sync_video)

    # Combined streaming
    serve_all = subparsers.add_parser("serve-all", help="Start audio + video servers on separate ports.")
    serve_all.add_argument("--host", default=None, help="Bind host.")
    serve_all.add_argument("--audio-port", type=int, default=None, help="Audio server port.")
    serve_all.add_argument("--video-port", type=int, default=None, help="Video server port.")
    serve_all.set_defaults(func=run_serve_all)

    stream_cfg = subparsers.add_parser("streaming-config", help="Show current streaming configuration.")
    stream_cfg.set_defaults(func=run_streaming_config)

    setup_pc = subparsers.add_parser("setup-pycharm", help="Generate PyCharm run configurations for streaming.")
    setup_pc.add_argument("--project-root", type=Path, default=Path.cwd())
    setup_pc.set_defaults(func=run_setup_pycharm)

    # Maintenance
    update_instructions = subparsers.add_parser(
        "update-instructions",
        help="Regenerate .github/INSTRUCTIONS.md from current repository structure.",
    )
    update_instructions.add_argument("--repo-root", type=Path, default=Path.cwd())
    update_instructions.set_defaults(func=run_update_instructions)

    return parser


# ---------------------------------------------------------------------------
# Server banner & library pre-check
# ---------------------------------------------------------------------------


def _get_local_ips() -> list[str]:
    """Return a list of local IPv4 addresses this machine has.
    
    Filters out loopback (127.x), auto-config (169.254.x), and virtual
    network adapters (172.x for Docker/Hyper-V).
    """
    import socket
    
    ips = []
    try:
        # Create a socket connection to a non-routable address to find the primary local IP
        # This doesn't actually send any data
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        primary_ip = sock.getsockname()[0]
        sock.close()
        ips.append(primary_ip)
    except Exception:
        pass
    
    # Also try to get all IPv4 addresses from network interfaces
    try:
        import socket as socket_module
        hostname = socket_module.gethostname()
        all_ips = socket_module.gethostbyname_ex(hostname)[2]
        for ip in all_ips:
            # Filter: skip loopback, auto-config, and virtual networks
            if (ip.startswith("127.") or 
                ip.startswith("169.254") or 
                ip.startswith("172.") or  # Docker/Hyper-V virtual
                ip.startswith("10.") and ip not in ips):  # Private IP, but check duplicates
                continue
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    
    return ips or ["127.0.0.1"]


def _print_server_banner(current: str, host: str, port: int) -> None:
    """Print a banner showing both configured server URLs.

    *current* should be ``"audio"`` or ``"video"`` — the one being started
    will be highlighted with an arrow.
    
    If host is 0.0.0.0 (all interfaces), show available network IPs.
    """
    audio_port = get_audio_port()
    video_port = get_video_port()
    
    # If binding to all interfaces, show network IPs
    if host == "0.0.0.0":
        local_ips = _get_local_ips()
        hosts_to_show = local_ips + ["localhost", "127.0.0.1"]
    else:
        hosts_to_show = [host]
    
    a_mark = "  ← dieser Server" if current == "audio" else ""
    v_mark = "  ← dieser Server" if current == "video" else ""

    print()
    print("  ╔═ Verbindungsadressen ════════════════════════════╗")
    
    for i, h in enumerate(hosts_to_show):
        audio_url = f"http://{h}:{audio_port}/"
        video_url = f"http://{h}:{video_port}/"
        
        if i > 0:
            print("  ║                                                  ║")
        
        print(f"  ║  🎵  {audio_url:<37}{a_mark}")
        print(f"  ║  🎬  {video_url:<37}{v_mark}")
    
    print("  ╚════════════════════════════════════════════════╝")
    print()


def _check_library_dir(path: Path, label: str) -> None:
    """Print a warning if the library directory is not accessible (with timeout)."""
    from hometools.streaming.core.server_utils import check_library_accessible

    ok, msg = check_library_accessible(path)
    if ok:
        return

    print(f"\n⚠  {label}-Bibliothek: {msg}")
    print(f"   Server startet trotzdem — die Bibliothek kann später verfügbar werden.\n")


# ---------------------------------------------------------------------------
# Audio handlers
# ---------------------------------------------------------------------------


def run_serve_audio(args: argparse.Namespace) -> int:
    """Start the local audio streaming server."""
    import uvicorn
    from hometools.streaming.audio.server import create_app

    setup_logging(log_file=None)
    host = args.host or get_stream_host()
    port = args.port or get_audio_port()
    library = args.library_dir or get_audio_library_dir()
    _check_library_dir(library, "Audio")
    _print_server_banner("audio", host, port)
    app = create_app(library)
    uvicorn.run(app, host=host, port=port)
    return 0


def run_sync_audio(args: argparse.Namespace) -> int:
    """Run a manual sync from the NAS audio source to the local library."""
    from hometools.streaming.audio.sync import sync_audio_library

    setup_logging(log_file=None)
    return _run_sync(args, get_audio_nas_dir(), get_audio_library_dir(), sync_audio_library, "audio")


# ---------------------------------------------------------------------------
# Video handlers
# ---------------------------------------------------------------------------


def run_serve_video(args: argparse.Namespace) -> int:
    """Start the local video streaming server."""
    import uvicorn
    from hometools.streaming.video.server import create_app

    setup_logging(log_file=None)
    host = args.host or get_stream_host()
    port = args.port or get_video_port()
    library = args.library_dir or get_video_library_dir()
    _check_library_dir(library, "Video")
    _print_server_banner("video", host, port)
    app = create_app(library)
    uvicorn.run(app, host=host, port=port)
    return 0


def run_sync_video(args: argparse.Namespace) -> int:
    """Run a manual sync from the NAS video source to the local library."""
    from hometools.streaming.video.sync import sync_video_library

    setup_logging(log_file=None)
    return _run_sync(args, get_video_nas_dir(), get_video_library_dir(), sync_video_library, "video")


# ---------------------------------------------------------------------------
# Combined streaming handlers
# ---------------------------------------------------------------------------


def run_serve_all(args: argparse.Namespace) -> int:
    """Start both streaming servers on separate ports."""
    from hometools.streaming.setup import serve_all

    setup_logging(log_file=None)
    serve_all(
        host=args.host or get_stream_host(),
        audio_port=args.audio_port or get_audio_port(),
        video_port=args.video_port or get_video_port(),
    )
    return 0


def run_streaming_config(args: argparse.Namespace) -> int:
    """Print the current streaming configuration."""
    from hometools.streaming.setup import print_streaming_config

    print_streaming_config()
    return 0


def run_setup_pycharm(args: argparse.Namespace) -> int:
    """Generate PyCharm run configurations."""
    from hometools.streaming.setup import generate_pycharm_configs

    created = generate_pycharm_configs(args.project_root.resolve())
    for p in created:
        print(f"  ✓ {p.name}")
    print(f"\n{len(created)} PyCharm run configuration(s) created. Restart PyCharm to see them.")
    return 0


# ---------------------------------------------------------------------------
# Shared sync helper
# ---------------------------------------------------------------------------


def _run_sync(args, default_source, default_target, sync_fn, label: str) -> int:
    """Shared sync runner for audio and video."""
    source = args.source or default_source
    target = args.target or default_target
    operations = sync_fn(source, target, dry_run=args.dry_run)

    if not operations:
        print(f"No {label} files need syncing.")
        return 0

    for op in operations:
        print(f"{op.reason}: {op.source} -> {op.destination}")

    if args.dry_run:
        print(f"Dry run complete: {len(operations)} {label} file(s) would be copied.")
    else:
        print(f"Sync complete: {len(operations)} {label} file(s) copied.")
    return 0


# ---------------------------------------------------------------------------
# Maintenance handlers
# ---------------------------------------------------------------------------


def run_update_instructions(args: argparse.Namespace) -> int:
    """Regenerate the project instructions file."""
    repo_root = args.repo_root.resolve()
    target = update_instructions_file(repo_root)
    print(f"Updated instructions: {target}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hometools CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

