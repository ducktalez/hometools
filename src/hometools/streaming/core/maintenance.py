"""Shared streaming maintenance helpers.

Provides server-specific cleanup and prewarm operations that can be reused by
CLI commands and repository-level automation such as the Makefile.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hometools.config import get_audio_library_dir, get_cache_dir, get_video_library_dir
from hometools.logging_config import get_log_dir
from hometools.streaming.core.index_cache import IndexCache
from hometools.streaming.core.thumbnailer import (
    FAILURE_FILE,
    check_thumbnail_cached,
    ensure_thumbnail,
    load_failures,
    save_failures,
)


@dataclass(frozen=True, slots=True)
class StreamMaintenanceSpec:
    """Runtime description for one streaming server."""

    server: str
    library_dir: Path
    cache_dir: Path
    media_cache_dir: Path
    index_label: str
    metadata_cache_path: Path | None
    build_index: object
    collect_thumbnail_work: object


@dataclass(frozen=True, slots=True)
class StreamResetResult:
    """Summary of removed generated artefacts for one server."""

    server: str
    removed_paths: tuple[Path, ...]
    failure_entries_removed: int


@dataclass(frozen=True, slots=True)
class StreamPrewarmResult:
    """Summary of a synchronous prewarm run."""

    server: str
    mode: str
    scope: str
    index_count: int
    thumbnails_generated: int
    thumbnails_skipped: int


def get_stream_maintenance_spec(server: str) -> StreamMaintenanceSpec:
    """Return the maintenance spec for ``audio`` or ``video``."""
    cache_dir = get_cache_dir()

    if server == "audio":
        from hometools.streaming.audio.catalog import build_audio_index, collect_thumbnail_work

        return StreamMaintenanceSpec(
            server="audio",
            library_dir=get_audio_library_dir(),
            cache_dir=cache_dir,
            media_cache_dir=cache_dir / "audio",
            index_label="audio-index",
            metadata_cache_path=None,
            build_index=build_audio_index,
            collect_thumbnail_work=collect_thumbnail_work,
        )

    if server == "video":
        from hometools.streaming.video.catalog import build_video_index, collect_thumbnail_work

        return StreamMaintenanceSpec(
            server="video",
            library_dir=get_video_library_dir(),
            cache_dir=cache_dir,
            media_cache_dir=cache_dir / "video",
            index_label="video-index",
            metadata_cache_path=cache_dir / "video_metadata_cache.json",
            build_index=build_video_index,
            collect_thumbnail_work=collect_thumbnail_work,
        )

    raise ValueError(f"Unsupported server: {server!r}")


def _remove_path(path: Path, removed: list[Path]) -> None:
    """Remove a file or directory if it exists, never raising."""
    try:
        if path.is_dir():
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    child.rmdir()
            path.rmdir()
            removed.append(path)
        elif path.exists():
            path.unlink(missing_ok=True)
            removed.append(path)
    except Exception:
        return


def _remove_failure_entries(cache_dir: Path, server: str) -> int:
    """Remove server-specific thumbnail failure entries from the shared registry."""
    try:
        failures = load_failures(cache_dir)
        original_count = len(failures)
        kept = {k: v for k, v in failures.items() if not k.startswith(f"{server}::")}
        if kept:
            save_failures(cache_dir, kept)
        else:
            failure_file = cache_dir / FAILURE_FILE
            failure_file.unlink(missing_ok=True)
        return original_count - len(kept)
    except Exception:
        return 0


def _iter_server_logs(server: str) -> list[Path]:
    """Return log files belonging to one server."""
    log_dir = get_log_dir()
    logs = sorted(log_dir.glob(f"{server}-*.log"))
    legacy = log_dir / "hometools.log"
    if legacy.exists() and server in {"audio", "video"}:
        logs.append(legacy)
    return logs


def reset_stream_generated(server: str, *, hard: bool = False) -> tuple[StreamResetResult, ...]:
    """Remove generated files for one server or for ``all`` servers.

    ``hard=False`` removes lightweight generated state such as snapshot indexes
    and server-specific logs.

    ``hard=True`` additionally removes shadow-cache thumbnails, video metadata
    cache, and server-specific thumbnail failure entries.
    """
    servers = ("audio", "video") if server == "all" else (server,)
    results: list[StreamResetResult] = []

    for name in servers:
        spec = get_stream_maintenance_spec(name)
        removed: list[Path] = []
        failure_entries_removed = 0

        _remove_path(spec.cache_dir / "indexes" / f"{spec.index_label}.json", removed)
        # Also remove hash-based snapshot files (library-dir-specific)
        indexes_dir = spec.cache_dir / "indexes"
        if indexes_dir.is_dir():
            for p in indexes_dir.glob(f"{spec.index_label}-*.json"):
                _remove_path(p, removed)
        for log_path in _iter_server_logs(name):
            _remove_path(log_path, removed)

        if hard:
            _remove_path(spec.media_cache_dir, removed)
            if spec.metadata_cache_path is not None:
                _remove_path(spec.metadata_cache_path, removed)
            failure_entries_removed = _remove_failure_entries(spec.cache_dir, name)

        results.append(
            StreamResetResult(
                server=name,
                removed_paths=tuple(removed),
                failure_entries_removed=failure_entries_removed,
            )
        )

    return tuple(results)


def _build_snapshot(spec: StreamMaintenanceSpec) -> int:
    """Build and persist a fresh index snapshot synchronously."""
    cache = IndexCache(spec.build_index, ttl=0.0, label=spec.index_label)
    items = cache.get(spec.library_dir, cache_dir=spec.cache_dir)
    return len(items)


def _prewarm_missing_thumbnails(spec: StreamMaintenanceSpec) -> tuple[int, int]:
    """Generate missing thumbnails synchronously for one server."""
    generated = 0
    skipped = 0
    for media_path, cache_dir, media_type, relative_path in spec.collect_thumbnail_work(spec.library_dir, spec.cache_dir):
        if check_thumbnail_cached(cache_dir, media_type, relative_path) is not None:
            skipped += 1
            continue
        thumb = ensure_thumbnail(media_path, cache_dir, media_type, relative_path)
        if thumb is not None:
            generated += 1
        else:
            skipped += 1
    return generated, skipped


def prewarm_stream(server: str, *, mode: str = "missing", scope: str = "all") -> StreamPrewarmResult:
    """Synchronously build cache artefacts for one server.

    Parameters
    ----------
    mode:
        ``missing`` keeps existing artefacts and only fills gaps.
        ``full`` deletes generated artefacts for the server first.
    scope:
        ``all`` builds the snapshot index and thumbnails.
        ``index`` only builds the snapshot index.
        ``thumbnails`` only generates thumbnails.
    """
    if server not in {"audio", "video"}:
        raise ValueError(f"Unsupported server: {server!r}")
    if mode not in {"missing", "full"}:
        raise ValueError(f"Unsupported mode: {mode!r}")
    if scope not in {"all", "index", "thumbnails"}:
        raise ValueError(f"Unsupported scope: {scope!r}")

    spec = get_stream_maintenance_spec(server)
    if mode == "full":
        reset_stream_generated(server, hard=True)

    index_count = 0
    generated = 0
    skipped = 0

    if scope in {"all", "index"}:
        index_count = _build_snapshot(spec)

    if scope in {"all", "thumbnails"}:
        generated, skipped = _prewarm_missing_thumbnails(spec)

    return StreamPrewarmResult(
        server=server,
        mode=mode,
        scope=scope,
        index_count=index_count,
        thumbnails_generated=generated,
        thumbnails_skipped=skipped,
    )
