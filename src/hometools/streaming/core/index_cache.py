"""In-memory index cache for media catalogs.

Avoids re-scanning the filesystem and re-reading metadata on every API
request.  Uses a simple TTL (time-to-live) approach: the index is rebuilt
at most once per ``ttl`` seconds.  A forced refresh is possible via
``invalidate()``.

Both the audio and video servers share this module so the caching strategy
is consistent.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from hometools.streaming.core.models import MediaItem

logger = logging.getLogger(__name__)

__all__ = ["IndexCache"]

# Bump this when the data format changes (e.g. POPM mapping) so stale
# snapshots are discarded and rebuilt from the filesystem.
# History: 1 = initial, 2 = WMP-standard POPM mapping (2026-04-10),
#          3 = M4A / FLAC / Vorbis rating support,
#          4 = M4A rating read fix (force rebuild after race-condition fix)
#          8 = added file_size, duration, bitrate fields to MediaItem
_SNAPSHOT_VERSION = 8


class IndexCache:
    """Thread-safe, TTL-based in-memory cache for a ``list[MediaItem]``.

    Parameters
    ----------
    builder:
        A callable ``(library_dir, *, cache_dir) -> list[MediaItem]`` that
        produces the full index.  Called at most once per *ttl* seconds.
    ttl:
        Maximum age in seconds before the cached index is considered stale.
        Defaults to 30 s — a good balance between freshness and performance.
    """

    def __init__(
        self,
        builder: Callable[..., list[MediaItem]],
        *,
        ttl: float = 30.0,
        label: str | None = None,
    ) -> None:
        self._builder = builder
        self._ttl = ttl
        self._label = label or getattr(builder, "__name__", "index-builder")
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._items: list[MediaItem] = []
        self._built_at: float = 0.0
        self._library_dir: Path | None = None
        self._cache_dir: Path | None = None
        self._building = False
        self._last_build_started_at: float = 0.0
        self._last_build_finished_at: float = 0.0
        self._last_build_duration: float = 0.0
        self._last_build_reason: str = ""
        self._last_error: str = ""
        # Live build progress (updated by the builder via the progress callback)
        self._build_total: int = 0
        self._build_processed: int = 0
        self._build_phase: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        library_dir: Path,
        *,
        cache_dir: Path | None = None,
    ) -> list[MediaItem]:
        """Return the cached index.

        Uses an in-memory cache first, then a persisted snapshot from the shadow
        cache directory. When stale data already exists, it is returned
        immediately and a refresh is started in the background.
        """
        now = time.monotonic()
        if self._is_fresh(now, library_dir, cache_dir):
            logger.debug(
                "Index cache hit: %s (items=%d, age=%.2fs)",
                self._label,
                len(self._items),
                now - self._built_at,
            )
            return self._items

        cached_items = self.get_cached(library_dir, cache_dir=cache_dir)
        if cached_items:
            self.ensure_background_refresh(library_dir, cache_dir=cache_dir)
            logger.info(
                "Index cache serving cached snapshot: %s (items=%d, age=%.2fs)",
                self._label,
                len(cached_items),
                max(0.0, now - self._built_at),
            )
            return cached_items

        with self._condition:
            wait_t0 = time.monotonic()
            if self._building:
                logger.info("Index cache waiting: %s rebuild already in progress", self._label)
                while self._building:
                    self._condition.wait(timeout=0.25)
                if self._items and self._library_dir == library_dir and self._cache_dir == cache_dir:
                    waited = time.monotonic() - wait_t0
                    logger.info("Index cache received freshly built data: %s after %.2fs", self._label, waited)
                    return self._items

            self._building = True

        try:
            return self._rebuild_now(library_dir, cache_dir=cache_dir, reason="cold-cache")
        finally:
            with self._condition:
                self._building = False
                self._condition.notify_all()

    def get_cached(
        self,
        library_dir: Path,
        *,
        cache_dir: Path | None = None,
    ) -> list[MediaItem]:
        """Return cached items or a persisted snapshot without blocking on rebuild."""
        now = time.monotonic()
        if self._items and self._library_dir == library_dir and self._cache_dir == cache_dir:
            return self._items

        snapshot = self._load_snapshot(library_dir, cache_dir)
        if snapshot is None:
            return []

        items, built_at = snapshot
        with self._lock:
            if not self._items or self._library_dir != library_dir or self._cache_dir != cache_dir:
                self._items = items
                # Preserve the snapshot's *real* age instead of forcing a full
                # rebuild on every server start.  A snapshot saved recently
                # (younger than the TTL) is treated as fresh, so the server does
                # NOT rescan the whole library again just because it restarted.
                # Only snapshots older than the TTL fall through to a background
                # rescan (picking up files added while offline).  The manual
                # "Katalog neu laden" button forces an immediate full refresh.
                self._built_at = built_at
                self._library_dir = library_dir
                self._cache_dir = cache_dir
                snapshot_age = max(0.0, now - built_at)
                logger.info(
                    "Index cache snapshot loaded: %s => %d items (snapshot_age=%.0fs, ttl=%.0fs, %s)",
                    self._label,
                    len(items),
                    snapshot_age,
                    self._ttl,
                    "fresh — no rebuild" if snapshot_age < self._ttl else "stale — background refresh",
                )
        return self._items

    def ensure_background_refresh(
        self,
        library_dir: Path,
        *,
        cache_dir: Path | None = None,
    ) -> bool:
        """Start a background rebuild when the cache is stale or empty.

        Returns ``True`` when a new background refresh was started.
        """
        self.get_cached(library_dir, cache_dir=cache_dir)

        with self._condition:
            if self._is_fresh(time.monotonic(), library_dir, cache_dir):
                return False
            if self._building:
                return False
            self._building = True

        def _worker() -> None:
            try:
                self._rebuild_now(library_dir, cache_dir=cache_dir, reason="background-refresh")
            finally:
                with self._condition:
                    self._building = False
                    self._condition.notify_all()

        thread = threading.Thread(target=_worker, daemon=True, name=f"{self._label}-refresh")
        thread.start()
        logger.info("Index cache background refresh scheduled: %s", self._label)
        return True

    def is_building(self) -> bool:
        """Return whether an index rebuild is currently in progress."""
        with self._lock:
            return self._building

    def _report_progress(self, processed: int, total: int, phase: str = "") -> None:
        """Update live build progress.  Called by the builder during a rebuild.

        Cheap and thread-safe.  ``processed``/``total`` count media files;
        ``phase`` is a short label such as ``"scanning"`` or ``"metadata"``.
        """
        with self._lock:
            self._build_processed = max(0, int(processed))
            self._build_total = max(0, int(total))
            if phase:
                self._build_phase = phase

    def progress(self) -> dict[str, object]:
        """Return the current build progress as a small dict.

        ``percent`` is ``None`` while the total is still unknown (scanning).
        """
        with self._lock:
            total = self._build_total
            processed = self._build_processed
            building = self._building
            phase = self._build_phase
        percent = round(processed / total * 100) if total > 0 else None
        return {
            "building": building,
            "processed": processed,
            "total": total,
            "percent": percent,
            "phase": phase,
        }

    def status(
        self,
        library_dir: Path,
        *,
        cache_dir: Path | None = None,
    ) -> dict[str, object]:
        """Return diagnostic status information for this cache instance."""
        snapshot_path = self._snapshot_path(cache_dir, library_dir)
        now = time.monotonic()
        with self._lock:
            cache_age = max(0.0, now - self._built_at) if self._built_at else None
            build_running_for = max(0.0, now - self._last_build_started_at) if self._building and self._last_build_started_at else None
            build_total = self._build_total
            build_processed = self._build_processed
            build_phase = self._build_phase
            build_percent = round(build_processed / build_total * 100) if build_total > 0 else None
            return {
                "label": self._label,
                "building": self._building,
                "cached_count": len(self._items),
                "fresh": self._is_fresh(now, library_dir, cache_dir),
                "ttl_seconds": self._ttl,
                "cache_age_seconds": cache_age,
                "library_dir": str(library_dir),
                "snapshot_path": str(snapshot_path) if snapshot_path is not None else "",
                "snapshot_exists": bool(snapshot_path and snapshot_path.exists()),
                "build_running_for_seconds": build_running_for,
                "build_total": build_total,
                "build_processed": build_processed,
                "build_percent": build_percent,
                "build_phase": build_phase,
                "last_build_started_at": self._last_build_started_at or None,
                "last_build_finished_at": self._last_build_finished_at or None,
                "last_build_duration_seconds": self._last_build_duration or None,
                "last_build_reason": self._last_build_reason,
                "last_error": self._last_error,
            }

    def _is_fresh(self, now: float, library_dir: Path, cache_dir: Path | None) -> bool:
        return (
            bool(self._items) and (now - self._built_at) < self._ttl and self._library_dir == library_dir and self._cache_dir == cache_dir
        )

    def _rebuild_now(
        self,
        library_dir: Path,
        *,
        cache_dir: Path | None,
        reason: str,
    ) -> list[MediaItem]:
        """Rebuild the full index immediately and persist a snapshot."""
        t0 = time.monotonic()
        with self._lock:
            self._last_build_started_at = t0
            self._last_build_reason = reason
            self._last_error = ""
            self._build_total = 0
            self._build_processed = 0
            self._build_phase = "scanning"
        logger.info(
            "Index cache rebuild started: %s (reason=%s, library=%s, cache=%s)",
            self._label,
            reason,
            library_dir,
            cache_dir,
        )
        try:
            if self._builder_supports_progress():
                items = self._builder(library_dir, cache_dir=cache_dir, progress=self._report_progress)
            else:
                items = self._builder(library_dir, cache_dir=cache_dir)
        except Exception:
            with self._lock:
                self._last_error = "builder failed"
            logger.warning("Index build failed for %s, returning stale cache", self._label, exc_info=True)
            return self.get_cached(library_dir, cache_dir=cache_dir)

        elapsed = time.monotonic() - t0
        with self._lock:
            self._items = items
            self._built_at = time.monotonic()
            self._library_dir = library_dir
            self._cache_dir = cache_dir
            self._last_build_finished_at = time.monotonic()
            self._last_build_duration = elapsed
            # Mark progress as complete so a final poll shows 100 %.
            self._build_total = len(items) if items else self._build_total
            self._build_processed = self._build_total
            self._build_phase = "done"
        self._save_snapshot(library_dir, cache_dir, items)
        logger.info(
            "Index cache rebuilt: %s => %d items in %.1fs (ttl=%.0fs)",
            self._label,
            len(items),
            elapsed,
            self._ttl,
        )
        return items

    def _builder_supports_progress(self) -> bool:
        """Return whether the builder accepts a ``progress`` keyword argument."""
        cached = getattr(self, "_progress_supported", None)
        if cached is not None:
            return cached
        supported = False
        try:
            import inspect

            params = inspect.signature(self._builder).parameters
            supported = "progress" in params or any(p.kind == p.VAR_KEYWORD for p in params.values())
        except (TypeError, ValueError):
            supported = False
        self._progress_supported = supported
        return supported

    def _snapshot_path(self, cache_dir: Path | None, library_dir: Path | None = None) -> Path | None:
        if cache_dir is None:
            return None
        if library_dir is not None:
            # Include a short hash of the library_dir so that different
            # libraries (and test tmp_paths) get independent snapshots.
            import hashlib

            dir_hash = hashlib.md5(str(library_dir).encode()).hexdigest()[:8]
            return cache_dir / "indexes" / f"{self._label}-{dir_hash}.json"
        return cache_dir / "indexes" / f"{self._label}.json"

    def _load_snapshot(
        self,
        library_dir: Path,
        cache_dir: Path | None,
    ) -> tuple[list[MediaItem], float] | None:
        path = self._snapshot_path(cache_dir, library_dir)
        if path is None:
            return None
        if not path.exists():
            # Fall back to legacy path (without hash) for one-time migration
            legacy = self._snapshot_path(cache_dir)
            if legacy is not None and legacy.exists():
                path = legacy
            else:
                return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("version", 0) < _SNAPSHOT_VERSION:
                logger.info(
                    "Index cache snapshot outdated (v%s < v%s), discarding: %s",
                    payload.get("version"),
                    _SNAPSHOT_VERSION,
                    self._label,
                )
                return None
            if payload.get("library_dir") != str(library_dir):
                return None
            raw_items = payload.get("items")
            if not isinstance(raw_items, list):
                return None
            items = [MediaItem(**item) for item in raw_items if isinstance(item, dict)]
            saved_at = float(payload.get("saved_at", 0.0))
            snapshot_age = max(0.0, time.time() - saved_at) if saved_at else self._ttl
            built_at = time.monotonic() - snapshot_age
            return items, built_at
        except Exception:
            logger.debug("Index cache snapshot load failed for %s", self._label, exc_info=True)
            return None

    def _save_snapshot(
        self,
        library_dir: Path,
        cache_dir: Path | None,
        items: list[MediaItem],
    ) -> None:
        path = self._snapshot_path(cache_dir, library_dir)
        if path is None:
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": _SNAPSHOT_VERSION,
                "label": self._label,
                "library_dir": str(library_dir),
                "saved_at": time.time(),
                "items": [item.to_dict() for item in items],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            logger.debug("Index cache snapshot save failed for %s", self._label, exc_info=True)

    def patch_items(self, updates: dict[str, dict[str, object]]) -> int:
        """Replace fields on specific cached items without a full rebuild.

        Useful for lazy per-item refreshes (e.g. re-reading POPM ratings for
        only the tracks the user is currently viewing).

        Parameters
        ----------
        updates:
            Mapping of ``relative_path`` → dict of field overrides.
            Example: ``{"folder/song.mp3": {"rating": 5.0}}``

        Returns the number of items that were actually modified.
        """
        from dataclasses import replace

        if not updates:
            return 0
        with self._lock:
            if not self._items:
                return 0
            changed = 0
            new_items: list[MediaItem] = []
            for item in self._items:
                if item.relative_path in updates:
                    overrides = updates[item.relative_path]
                    try:
                        new_item = replace(item, **overrides)
                        if new_item != item:
                            changed += 1
                        new_items.append(new_item)
                    except Exception:
                        new_items.append(item)
                else:
                    new_items.append(item)
            if changed:
                self._items = new_items
                logger.info(
                    "Index cache patched: %s — %d/%d items updated",
                    self._label,
                    changed,
                    len(updates),
                )
        return changed

    def invalidate(self) -> None:
        """Force the next ``get()`` call to rebuild the index."""
        logger.info("Index cache invalidated: %s", self._label)
        with self._lock:
            self._built_at = 0.0
