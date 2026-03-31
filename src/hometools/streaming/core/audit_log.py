"""Append-only audit log for all filesystem modifications.

Every write operation (rating changes, tag edits, future renames) is logged as
an immutable JSONL entry.  Each entry carries an ``undo_payload`` so that the
inverse operation can be replayed later.

Storage: ``<audit_dir>/audit.jsonl``  (default: ``.hometools-audit/audit.jsonl``)

The audit log is permanent data and intentionally lives **outside** the
disposable shadow cache (``get_cache_dir()``).  See :func:`hometools.config.get_audit_dir`.

Typical callers
---------------
- ``streaming/audio/server.py`` → ``POST /api/audio/rating``
- Future: tag-write, rename endpoints

Typical readers
---------------
- ``GET /api/<media>/audit`` — JSON API for the control panel
- ``GET /audit`` — control panel HTML page
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_AUDIT_FILE = "audit.jsonl"

# Legacy sub-path used before the audit log was moved out of the cache dir.
_LEGACY_CACHE_SUBDIR = "audit"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

VALID_ACTIONS = {
    "rating_write",
    "tag_write",
    "file_rename",
}


@dataclass(frozen=True)
class AuditEntry:
    """One immutable record of a filesystem change."""

    entry_id: str  # UUID — used to reference this entry for undo
    timestamp: str  # ISO 8601 UTC
    action: str  # one of VALID_ACTIONS
    server: str  # "audio" | "video"
    path: str  # relative file path inside the library
    field: str  # which field was changed ("rating", "title", …)
    old_value: Any  # previous value (None if unknown / first write)
    new_value: Any  # value after the write
    undo_payload: dict  # body for POST /api/<server>/audit/undo to reverse
    undone: bool = False
    undone_at: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _audit_path(audit_dir: Path) -> Path:
    """Return the JSONL audit log file path, creating the directory if needed."""
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir / _AUDIT_FILE


def _migrate_from_cache(audit_dir: Path, cache_dir: Path | None) -> None:
    """One-time migration: copy legacy ``<cache_dir>/audit/audit.jsonl`` to *audit_dir*.

    Only copies when:
    - *cache_dir* is given and the old file exists,
    - the new destination does **not** already exist (idempotent).

    Never raises — migration failure is logged and silently tolerated.
    """
    if cache_dir is None:
        return
    old_file = cache_dir / _LEGACY_CACHE_SUBDIR / _AUDIT_FILE
    new_file = _audit_path(audit_dir)
    if new_file.exists() or not old_file.exists():
        return
    try:
        import shutil

        shutil.copy2(old_file, new_file)
        logger.info(
            "audit_log: migrated %s → %s",
            old_file,
            new_file,
        )
    except Exception:
        logger.exception("audit_log: failed to migrate legacy audit log")


# ---------------------------------------------------------------------------
# Public write API
# ---------------------------------------------------------------------------


def new_entry(
    *,
    action: str,
    server: str,
    path: str,
    field: str,
    old_value: Any,
    new_value: Any,
    undo_payload: dict,
) -> AuditEntry:
    """Create a new :class:`AuditEntry` with a fresh UUID and current timestamp."""
    return AuditEntry(
        entry_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action,
        server=server,
        path=path,
        field=field,
        old_value=old_value,
        new_value=new_value,
        undo_payload=undo_payload,
    )


def append_entry(audit_dir: Path, entry: AuditEntry) -> None:
    """Atomically append *entry* to the JSONL audit log.

    Never raises — failures are logged but silently swallowed so they don't
    interrupt the caller's primary operation.
    """
    audit_path = _audit_path(audit_dir)
    line = json.dumps(asdict(entry), ensure_ascii=False)
    with _LOCK:
        try:
            with audit_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            logger.exception("audit_log: failed to write entry for %s", entry.path)


# ---------------------------------------------------------------------------
# Public read API
# ---------------------------------------------------------------------------


def load_entries(
    audit_dir: Path,
    *,
    limit: int = 200,
    path_filter: str = "",
    action_filter: str = "",
    include_undone: bool = True,
) -> list[dict]:
    """Return audit entries as plain dicts, newest first.

    Parameters
    ----------
    limit:
        Maximum number of entries to return.
    path_filter:
        Case-insensitive substring match on ``path``.
    action_filter:
        Exact match on ``action`` (e.g. ``"rating_write"``).
    include_undone:
        When *False*, entries that have already been undone are excluded.
    """
    audit_path = _audit_path(audit_dir)
    if not audit_path.exists():
        return []
    try:
        with _LOCK:
            raw = audit_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        logger.exception("audit_log: failed to read audit log")
        return []

    entries: list[dict] = []
    for line in reversed(raw):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not include_undone and e.get("undone"):
            continue
        if path_filter and path_filter.lower() not in e.get("path", "").lower():
            continue
        if action_filter and e.get("action") != action_filter:
            continue
        entries.append(e)
        if len(entries) >= limit:
            break
    return entries


def get_entry(audit_dir: Path, entry_id: str) -> dict | None:
    """Return a single entry by its UUID, or *None* if not found."""
    audit_path = _audit_path(audit_dir)
    if not audit_path.exists():
        return None
    try:
        with _LOCK:
            lines = audit_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if e.get("entry_id") == entry_id:
                return e
        except json.JSONDecodeError:
            continue
    return None


def mark_undone(audit_dir: Path, entry_id: str) -> bool:
    """Rewrite the JSONL log marking *entry_id* as undone.

    Returns *True* when the entry was found and updated, *False* otherwise.
    Uses an atomic tmp-rename write to avoid partial corruption.
    """
    audit_path = _audit_path(audit_dir)
    if not audit_path.exists():
        return False
    undone_at = datetime.now(timezone.utc).isoformat()
    found = False
    with _LOCK:
        try:
            lines = audit_path.read_text(encoding="utf-8").splitlines()
            new_lines: list[str] = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    if e.get("entry_id") == entry_id:
                        e["undone"] = True
                        e["undone_at"] = undone_at
                        found = True
                    new_lines.append(json.dumps(e, ensure_ascii=False))
                except json.JSONDecodeError:
                    new_lines.append(line)
            tmp = audit_path.with_suffix(".tmp")
            tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            tmp.replace(audit_path)
        except Exception:
            logger.exception("audit_log: failed to mark entry %s as undone", entry_id)
            return False
    return found


# ---------------------------------------------------------------------------
# Rating-specific helpers
# ---------------------------------------------------------------------------


def log_rating_write(
    audit_dir: Path,
    *,
    server: str,
    path: str,
    old_stars: float,
    new_stars: float,
    old_raw: int,
    new_raw: int,
) -> AuditEntry:
    """Create, append, and return an audit entry for a POPM rating write."""
    entry = new_entry(
        action="rating_write",
        server=server,
        path=path,
        field="rating",
        old_value=old_stars,
        new_value=new_stars,
        undo_payload={
            "entry_id": "",  # filled in after creation
            "path": path,
            "rating": old_stars,
            "raw": old_raw,
        },
    )
    # Patch undo_payload with the real entry_id (frozen dataclass → rebuild)
    entry = AuditEntry(**{**asdict(entry), "undo_payload": {**entry.undo_payload, "entry_id": entry.entry_id}})
    append_entry(audit_dir, entry)
    logger.info(
        "audit: %s rating %s → %s (entry %s)",
        path,
        old_stars,
        new_stars,
        entry.entry_id,
    )
    return entry


def log_tag_write(
    audit_dir: Path,
    *,
    server: str,
    path: str,
    field: str,
    old_value: str,
    new_value: str,
) -> AuditEntry:
    """Create, append, and return an audit entry for a text-tag write (title/artist/album).

    The undo_payload contains a ``POST /api/<server>/metadata/edit`` body
    that restores the previous value.
    """
    entry = new_entry(
        action="tag_write",
        server=server,
        path=path,
        field=field,
        old_value=old_value,
        new_value=new_value,
        undo_payload={
            "entry_id": "",
            "path": path,
            "field": field,
            "value": old_value,
        },
    )
    entry = AuditEntry(**{**asdict(entry), "undo_payload": {**entry.undo_payload, "entry_id": entry.entry_id}})
    append_entry(audit_dir, entry)
    logger.info(
        "audit: %s %s %r → %r (entry %s)",
        path,
        field,
        old_value,
        new_value,
        entry.entry_id,
    )
    return entry
