"""Command-line entry points for hometools."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_stream_bind,
    get_video_library_dir,
    get_video_nas_dir,
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

    # Maintenance
    update_instructions = subparsers.add_parser(
        "update-instructions",
        help="Regenerate .github/INSTRUCTIONS.md from current repository structure.",
    )
    update_instructions.add_argument("--repo-root", type=Path, default=Path.cwd())
    update_instructions.set_defaults(func=run_update_instructions)

    return parser


# ---------------------------------------------------------------------------
# Audio handlers
# ---------------------------------------------------------------------------


def run_serve_audio(args: argparse.Namespace) -> int:
    """Start the local audio streaming server."""
    import uvicorn
    from hometools.streaming.audio.server import create_app

    setup_logging(log_file=None)
    default_host, default_port = get_stream_bind()
    app = create_app(args.library_dir or get_audio_library_dir())
    uvicorn.run(app, host=args.host or default_host, port=args.port or default_port)
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
    default_host, default_port = get_stream_bind()
    app = create_app(args.library_dir or get_video_library_dir())
    uvicorn.run(app, host=args.host or default_host, port=args.port or default_port)
    return 0


def run_sync_video(args: argparse.Namespace) -> int:
    """Run a manual sync from the NAS video source to the local library."""
    from hometools.streaming.video.sync import sync_video_library

    setup_logging(log_file=None)
    return _run_sync(args, get_video_nas_dir(), get_video_library_dir(), sync_video_library, "video")


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

