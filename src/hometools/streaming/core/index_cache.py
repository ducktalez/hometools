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
_SNAPSHOT_VERSION = 7


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
                # Mark snapshot data as stale so ensure_background_refresh()
                # always triggers a rebuild after loading from disk.  The
                # snapshot is still served instantly (fast startup), but the
                # filesystem is rescanned in the background to pick up any
                # changes that happened while the server was offline.
                self._built_at = 0.0
                self._library_dir = library_dir
                self._cache_dir = cache_dir
                logger.info(
                    "Index cache snapshot loaded: %s => %d items (snapshot_age=%.0fs, marked stale for refresh)",
                    self._label,
                    len(items),
                    max(0.0, now - built_at),
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
        logger.info(
            "Index cache rebuild started: %s (reason=%s, library=%s, cache=%s)",
            self._label,
            reason,
            library_dir,
            cache_dir,
        )
        try:
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
        self._save_snapshot(library_dir, cache_dir, items)
        logger.info(
            "Index cache rebuilt: %s => %d items in %.1fs (ttl=%.0fs)",
            self._label,
            len(items),
            elapsed,
            self._ttl,
        )
        return items

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
