"""Command-line entry points for hometools."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from hometools.config import (
    get_audio_library_dir,
    get_audio_nas_dir,
    get_stream_bind,
)
from hometools.instructions import update_instructions_file
from hometools.logging_config import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="hometools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_audio = subparsers.add_parser(
        "serve-audio",
        help="Start the local audio streaming web UI.",
    )
    serve_audio.add_argument(
        "--library-dir",
        type=Path,
        default=None,
        help="Local audio library directory to browse and stream.",
    )
    serve_audio.add_argument(
        "--host",
        default=None,
        help="Bind host for the local web server.",
    )
    serve_audio.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port for the local web server.",
    )
    serve_audio.set_defaults(func=run_serve_audio)

    sync_audio = subparsers.add_parser(
        "sync-audio",
        help="Copy new or changed audio files from the NAS source into the local library.",
    )
    sync_audio.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Mounted NAS source directory.",
    )
    sync_audio.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Local audio library directory.",
    )
    sync_audio.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which files would be copied without changing anything.",
    )
    sync_audio.set_defaults(func=run_sync_audio)

    update_instructions = subparsers.add_parser(
        "update-instructions",
        help="Regenerate .github/INSTRUCTIONS.md from current repository structure.",
    )
    update_instructions.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root that should be scanned.",
    )
    update_instructions.set_defaults(func=run_update_instructions)

    return parser


def run_serve_audio(args: argparse.Namespace) -> int:
    """Start the local audio streaming server."""
    import uvicorn

    from hometools.streaming.audio.server import create_app

    setup_logging(log_file=None)
    default_host, default_port = get_stream_bind()
    app = create_app(args.library_dir or get_audio_library_dir())
    uvicorn.run(
        app,
        host=args.host or default_host,
        port=args.port or default_port,
    )
    return 0


def run_sync_audio(args: argparse.Namespace) -> int:
    """Run a manual sync from the NAS audio source to the local audio library."""
    from hometools.streaming.audio.sync import sync_audio_library

    setup_logging(log_file=None)
    source = args.source or get_audio_nas_dir()
    target = args.target or get_audio_library_dir()
    operations = sync_audio_library(source, target, dry_run=args.dry_run)

    if not operations:
        print("No audio files need syncing.")
        return 0

    for operation in operations:
        print(f"{operation.reason}: {operation.source} -> {operation.destination}")

    if args.dry_run:
        print(f"Dry run complete: {len(operations)} file(s) would be copied.")
    else:
        print(f"Sync complete: {len(operations)} file(s) copied.")
    return 0


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



