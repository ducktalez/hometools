"""Command-line entry points for hometools."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_audio_port,
    get_stream_host,
    get_stream_safe_mode,
    get_video_library_dir,
    get_video_nas_dir,
    get_video_port,
)
from hometools.logging_config import setup_logging


def _add_serve_parser(subparsers, name: str, help_text: str, func):
    """Add a serve-* subcommand with common --library-dir/--host/--port arguments."""
    p = subparsers.add_parser(name, help=help_text)
    p.add_argument("--library-dir", type=Path, default=None, help="Local library directory.")
    p.add_argument("--host", default=None, help="Bind host.")
    p.add_argument("--port", type=int, default=None, help="Bind port.")
    p.add_argument("--safe-mode", action="store_true", help="Disable streaming caches and PWA extras for a minimal fallback mode.")
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
    serve_all.add_argument("--safe-mode", action="store_true", help="Run both servers in minimal no-cache safe mode.")
    serve_all.set_defaults(func=run_serve_all)

    stream_cfg = subparsers.add_parser("streaming-config", help="Show current streaming configuration.")
    stream_cfg.set_defaults(func=run_streaming_config)

    stream_reset = subparsers.add_parser("stream-reset", help="Remove generated streaming artefacts for one server.")
    stream_reset.add_argument("--server", choices=["audio", "video", "all"], required=True)
    stream_reset.add_argument("--hard", action="store_true", help="Also delete thumbnails, metadata caches and failure entries.")
    stream_reset.set_defaults(func=run_stream_reset)

    stream_prewarm = subparsers.add_parser(
        "stream-prewarm",
        help="Build streaming index snapshots and thumbnails without starting the server.",
    )
    stream_prewarm.add_argument("--server", choices=["audio", "video"], required=True)
    stream_prewarm.add_argument("--mode", choices=["missing", "full"], default="missing")
    stream_prewarm.add_argument("--scope", choices=["all", "index", "thumbnails"], default="all")
    stream_prewarm.set_defaults(func=run_stream_prewarm)

    stream_issues = subparsers.add_parser("stream-issues", help="Show currently open irregularities collected from warnings/errors.")
    stream_issues.add_argument("--json", action="store_true", help="Emit machine-readable JSON for schedulers.")
    stream_issues.add_argument(
        "--min-severity",
        choices=["warning", "error", "critical"],
        default="warning",
        help="Only include issues at or above this severity.",
    )
    stream_issues.add_argument("--only-errors", action="store_true", help="Shortcut for --min-severity error.")
    stream_issues.add_argument(
        "--fail-on-match",
        action="store_true",
        help="Return exit code 1 when filtered issues are present (useful for schedulers).",
    )
    stream_issues.set_defaults(func=run_stream_issues)

    stream_todos = subparsers.add_parser("stream-todos", help="Derive TODO candidates from the current open streaming irregularities.")
    stream_todos.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    stream_todos.add_argument(
        "--min-severity",
        choices=["warning", "error", "critical"],
        default="warning",
        help="Only derive TODOs from issues at or above this severity.",
    )
    stream_todos.add_argument("--only-errors", action="store_true", help="Shortcut for --min-severity error.")
    stream_todos.add_argument("--max-items", type=int, default=None, help="Limit the number of generated TODO candidates.")
    stream_todos.add_argument(
        "--fail-on-match",
        action="store_true",
        help="Return exit code 1 when filtered TODO candidates are present.",
    )
    stream_todos.set_defaults(func=run_stream_todos)

    stream_scheduler = subparsers.add_parser("stream-scheduler", help="Run the first scheduler stub once (issues -> TODO candidates).")
    stream_scheduler.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    stream_scheduler.add_argument(
        "--min-severity",
        choices=["warning", "error", "critical"],
        default="warning",
        help="Only process issues at or above this severity.",
    )
    stream_scheduler.add_argument("--only-errors", action="store_true", help="Shortcut for --min-severity error.")
    stream_scheduler.add_argument("--max-items", type=int, default=None, help="Limit the number of generated TODO candidates.")
    stream_scheduler.add_argument(
        "--cooldown-seconds",
        type=int,
        default=3600,
        help="Suppress already emitted TODO tasks for this many seconds unless severity increases.",
    )
    stream_scheduler.add_argument(
        "--fail-on-match",
        action="store_true",
        help="Return exit code 1 when generated TODO candidates are present.",
    )
    stream_scheduler.set_defaults(func=run_stream_scheduler)

    stream_dashboard = subparsers.add_parser(
        "stream-dashboard", help="Show a combined dashboard of open issues, TODO candidates and scheduler state."
    )
    stream_dashboard.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    stream_dashboard.add_argument(
        "--min-severity",
        choices=["warning", "error", "critical"],
        default="warning",
        help="Only include items at or above this severity.",
    )
    stream_dashboard.add_argument("--only-errors", action="store_true", help="Shortcut for --min-severity error.")
    stream_dashboard.add_argument("--max-items", type=int, default=5, help="Max TODO items to display.")
    stream_dashboard.add_argument(
        "--fail-on-match",
        action="store_true",
        help="Return exit code 1 when active TODO candidates are present.",
    )
    stream_dashboard.set_defaults(func=run_stream_dashboard)

    stream_todo_state = subparsers.add_parser(
        "stream-todo-state", help="Acknowledge, snooze or clear the state of a grouped streaming TODO task."
    )
    stream_todo_state.add_argument("--todo-key", required=True, help="Grouped TODO key from stream-todos / stream-scheduler output.")
    stream_todo_state.add_argument("--action", choices=["acknowledge", "snooze", "clear"], required=True)
    stream_todo_state.add_argument("--reason", default="", help="Optional note stored with the state change.")
    stream_todo_state.add_argument("--seconds", type=int, default=3600, help="Snooze duration in seconds (only used with --action snooze).")
    stream_todo_state.add_argument(
        "--min-severity",
        choices=["warning", "error", "critical"],
        default="warning",
        help="Severity threshold used to resolve the current TODO candidate.",
    )
    stream_todo_state.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    stream_todo_state.set_defaults(func=run_stream_todo_state)

    setup_pc = subparsers.add_parser("setup-pycharm", help="Generate PyCharm run configurations for streaming.")
    setup_pc.add_argument("--project-root", type=Path, default=Path.cwd())
    setup_pc.set_defaults(func=run_setup_pycharm)

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
            if (
                ip.startswith("127.")
                or ip.startswith("169.254")
                or ip.startswith("172.")  # Docker/Hyper-V virtual
                or (ip.startswith("10.") and ip not in ips)
            ):  # Private IP, but check duplicates
                continue
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    return ips or ["127.0.0.1"]


def _console_print(text: str = "") -> None:
    """Print text safely even on Windows consoles without full Unicode support."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        sanitized = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)


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
        hosts_to_show = local_ips + ["127.0.0.1"]
    else:
        hosts_to_show = [host]

    _console_print("\n  ╔═ Verbindungsadressen ════════════════════════════╗")

    for _i, h in enumerate(hosts_to_show):
        audio_url = f"http://{h}:{audio_port}/"
        video_url = f"http://{h}:{video_port}/"

        _console_print("  ║                                                  ║")
        _console_print(f"  ║  🎵  {audio_url:<37}")
        _console_print(f"  ║  🎬  {video_url:<37}")

    _console_print("  ╚════════════════════════════════════════════════╝")
    _console_print()


def _check_library_dir(path: Path, label: str) -> None:
    """Print a warning if the library directory is not accessible (with timeout)."""
    from hometools.streaming.core.server_utils import check_library_accessible

    ok, msg = check_library_accessible(path)
    if ok:
        return

    _console_print(f"\n⚠  {label}-Bibliothek: {msg}")
    _console_print("   Server startet trotzdem — die Bibliothek kann später verfügbar werden.\n")


# ---------------------------------------------------------------------------
# Audio handlers
# ---------------------------------------------------------------------------


def run_serve_audio(args: argparse.Namespace) -> int:
    """Start the local audio streaming server."""
    import uvicorn

    from hometools.streaming.audio.server import create_app

    setup_logging(log_file="auto", log_name="audio")
    host = args.host or get_stream_host()
    port = args.port or get_audio_port()
    library = args.library_dir or get_audio_library_dir()
    safe_mode = args.safe_mode or get_stream_safe_mode()
    _check_library_dir(library, "Audio")
    _print_server_banner("audio", host, port)
    app = create_app(library, safe_mode=safe_mode)
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

    setup_logging(log_file="auto", log_name="video")
    host = args.host or get_stream_host()
    port = args.port or get_video_port()
    library = args.library_dir or get_video_library_dir()
    safe_mode = args.safe_mode or get_stream_safe_mode()
    _check_library_dir(library, "Video")
    _print_server_banner("video", host, port)
    app = create_app(library, safe_mode=safe_mode)
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

    setup_logging(log_file="auto", log_name="serve-all")
    serve_all(
        host=args.host or get_stream_host(),
        audio_port=args.audio_port or get_audio_port(),
        video_port=args.video_port or get_video_port(),
        safe_mode=args.safe_mode or get_stream_safe_mode(),
    )
    return 0


def run_stream_reset(args: argparse.Namespace) -> int:
    """Delete generated streaming artefacts for one or both servers."""
    from hometools.streaming.core.maintenance import reset_stream_generated

    setup_logging(log_file=None)
    results = reset_stream_generated(args.server, hard=args.hard)
    for result in results:
        print(f"[{result.server}] removed {len(result.removed_paths)} path(s), failure entries cleared: {result.failure_entries_removed}")
        for path in result.removed_paths:
            print(f"  - {path}")
    return 0


def run_stream_prewarm(args: argparse.Namespace) -> int:
    """Build cache artefacts for one server without starting uvicorn."""
    from hometools.streaming.core.maintenance import prewarm_stream

    setup_logging(log_file=None)
    result = prewarm_stream(args.server, mode=args.mode, scope=args.scope)
    print(
        f"[{result.server}] prewarm complete — mode={result.mode}, scope={result.scope}, "
        f"index_items={result.index_count}, thumbnails_generated={result.thumbnails_generated}, thumbnails_skipped={result.thumbnails_skipped}"
    )
    return 0


def run_stream_issues(args: argparse.Namespace) -> int:
    """Print open irregularities collected from warnings/errors."""
    from hometools.config import get_cache_dir
    from hometools.streaming.core.issue_registry import summarize_open_issues

    setup_logging(log_file=None)
    min_severity = _resolve_min_severity(args)
    summary = summarize_open_issues(get_cache_dir(), min_severity=min_severity)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Open issues >= {summary['min_severity']}: {summary['count']} "
            f"(warnings={summary['warnings']}, errors={summary['errors']}, criticals={summary['criticals']})"
        )
        for item in summary["items"]:
            print(f"- [{item['severity']}] {item['source']}: {item['message']} (count={item['count']})")
    return 1 if args.fail_on_match and summary["count"] else 0


def run_stream_todos(args: argparse.Namespace) -> int:
    """Derive and print TODO candidates from open irregularities."""
    from hometools.config import get_cache_dir
    from hometools.streaming.core.issue_registry import generate_todo_candidates

    setup_logging(log_file=None)
    payload = generate_todo_candidates(
        get_cache_dir(),
        min_severity=_resolve_min_severity(args),
        max_items=args.max_items,
        persist=True,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"TODO candidates >= {payload['min_severity']}: {payload['count']} (from {payload['source_issue_count']} open issue(s))")
        for item in payload["items"]:
            print(f"- [{item['priority']}/{item['severity']}] {item['source']}: {item['message']} (count={item['count']})")
    return 1 if args.fail_on_match and payload["count"] else 0


def run_stream_scheduler(args: argparse.Namespace) -> int:
    """Run the first scheduler stub once and persist TODO candidates."""
    from hometools.config import get_cache_dir
    from hometools.streaming.core.issue_registry import run_scheduler_once

    setup_logging(log_file=None)
    result = run_scheduler_once(
        get_cache_dir(),
        min_severity=_resolve_min_severity(args),
        max_items=args.max_items,
        cooldown_seconds=max(int(getattr(args, "cooldown_seconds", 3600)), 0),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Scheduler run complete: status={result['status']}, open_issues={result['open_issue_count']}, "
            f"todo_candidates={result['todo_count']}, active={result['active_todo_count']}, suppressed={result['suppressed_todo_count']}"
        )
        print(f"TODO file: {result['todo_candidates_path']}")
        top_todo = result.get("top_todo")
        if isinstance(top_todo, dict):
            print(f"Top TODO: [{top_todo.get('priority', '?')}] {top_todo.get('message', '')}")
    return 1 if args.fail_on_match and result["active_todo_count"] else 0


def run_stream_todo_state(args: argparse.Namespace) -> int:
    """Update acknowledge/snooze state for a grouped TODO task."""
    from hometools.config import get_cache_dir
    from hometools.streaming.core.issue_registry import acknowledge_todo, clear_todo_state, snooze_todo

    setup_logging(log_file=None)
    if args.action == "snooze" and int(args.seconds) <= 0:
        print("--seconds must be > 0 for snooze")
        return 2

    if args.action == "acknowledge":
        result = acknowledge_todo(get_cache_dir(), args.todo_key, reason=args.reason, min_severity=_resolve_min_severity(args))
    elif args.action == "snooze":
        result = snooze_todo(
            get_cache_dir(),
            args.todo_key,
            seconds=args.seconds,
            reason=args.reason,
            min_severity=_resolve_min_severity(args),
        )
    else:
        result = clear_todo_state(get_cache_dir(), args.todo_key)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"TODO state update: ok={result.get('ok', False)}, key={result.get('todo_key', '')}, state={result.get('state', '')}")
        if result.get("message"):
            print(result["message"])
        if result.get("snoozed_until"):
            print(f"Snoozed until: {result['snoozed_until']}")
    return 0 if result.get("ok", False) else 1


def run_stream_dashboard(args: argparse.Namespace) -> int:
    """Show a combined dashboard of open issues, TODOs and scheduler state."""
    from hometools.config import get_cache_dir
    from hometools.streaming.core.issue_dashboard import build_dashboard_data, format_dashboard_table

    setup_logging(log_file=None)
    data = build_dashboard_data(
        get_cache_dir(),
        min_severity=_resolve_min_severity(args),
        max_todo_items=max(int(getattr(args, "max_items", 5)), 1),
    )
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_dashboard_table(data))
    active = int((data.get("todos") or {}).get("active_count", 0))
    return 1 if args.fail_on_match and active else 0


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
        _console_print(f"  ✓ {p.name}")
    _console_print(f"\n{len(created)} PyCharm run configuration(s) created. Restart PyCharm to see them.")
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


def _resolve_min_severity(args: argparse.Namespace) -> str:
    """Resolve the effective severity threshold for issue-derived commands."""
    return "error" if getattr(args, "only_errors", False) else args.min_severity


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hometools CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
