"""Persistent registry for open streaming irregularities.

Stores current open issues in JSON and appends every observation to a JSONL
file so a future scheduler can derive tasks or alerts from it.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

_LOCK = threading.Lock()
_VERSION = 1
_DEFAULT_SEVERITY = "WARNING"
_DEFAULT_TODO_COOLDOWN_SECONDS = 3600
_DEFAULT_TODO_UI_LIMIT = 3

# ---------------------------------------------------------------------------
# Action hints — structured CLI recommendations per category
# ---------------------------------------------------------------------------

_ACTION_HINT_MAP: dict[str, list[dict[str, str]]] = {
    "thumbnail": [
        {
            "action_id": "prewarm-thumbnails",
            "label": "Thumbnail-Prewarm ausführen",
            "cli_command": "hometools stream-prewarm --server {server} --mode missing --scope thumbnails",
            "make_target": "{server}-prewarm",
        },
    ],
    "metadata": [
        {
            "action_id": "check-metadata",
            "label": "Metadaten der betroffenen Dateien prüfen",
            "cli_command": "hometools stream-issues --min-severity error --json",
            "make_target": "issues-errors",
        },
    ],
    "sync": [
        {
            "action_id": "check-nas",
            "label": "NAS-Erreichbarkeit und Sync-Status prüfen",
            "cli_command": "hometools sync-{server} --dry-run",
            "make_target": "",
        },
    ],
    "cache": [
        {
            "action_id": "reindex",
            "label": "Index neu aufbauen",
            "cli_command": "hometools stream-prewarm --server {server} --mode full --scope index",
            "make_target": "{server}-reindex",
        },
    ],
    "streaming": [
        {
            "action_id": "check-server-status",
            "label": "Server-Status prüfen",
            "cli_command": "hometools stream-dashboard --json",
            "make_target": "dashboard-json",
        },
    ],
}


def _derive_action_hints(category: str, source: str) -> list[dict[str, str]]:
    """Return structured action hints for a task category.

    Placeholders like ``{server}`` are resolved from the source string.
    """
    templates = _ACTION_HINT_MAP.get(category, [])
    if not templates:
        return []
    server = "audio" if "audio" in source.lower() else "video"
    hints: list[dict[str, str]] = []
    for tpl in templates:
        hints.append({k: v.replace("{server}", server) for k, v in tpl.items()})
    return hints


# ---------------------------------------------------------------------------
# Noise rules — source-specific thresholds to suppress low-signal task candidates
# ---------------------------------------------------------------------------

_NOISE_RULES: list[dict[str, Any]] = [
    {
        "source_prefix": "hometools.streaming.core.thumbnailer",
        "category": "thumbnail",
        "min_severity_for_todo": "ERROR",
        "min_count_for_todo": 1,
    },
    {
        "source_prefix": "hometools.streaming",
        "category": "streaming",
        "min_severity_for_todo": "ERROR",
        "min_count_for_todo": 2,
    },
]


def _apply_noise_rules(candidate: dict[str, Any]) -> bool:
    """Return ``True`` if *candidate* passes noise filtering.

    CRITICAL issues always pass.  Otherwise the first matching rule
    determines whether the candidate's severity and count are high enough.
    """
    severity = normalize_severity(str(candidate.get("severity", _DEFAULT_SEVERITY)))
    if severity == "CRITICAL":
        return True
    source = str(candidate.get("source", ""))
    category = str(candidate.get("category", ""))
    count = int(candidate.get("count", 1))
    for rule in _NOISE_RULES:
        prefix = str(rule.get("source_prefix", ""))
        rule_cat = str(rule.get("category", ""))
        if not (source.startswith(prefix) and (not rule_cat or rule_cat == category)):
            continue
        min_sev = normalize_severity(str(rule.get("min_severity_for_todo", _DEFAULT_SEVERITY)))
        min_count = int(rule.get("min_count_for_todo", 1))
        if _severity_rank(severity) < _severity_rank(min_sev):
            return False
        return count >= min_count
    return True


# ---------------------------------------------------------------------------
# Root-cause deduplication — cross-source grouping by message patterns
# ---------------------------------------------------------------------------

_ROOT_CAUSE_PATTERNS: dict[str, list[str]] = {
    "library-unreachable": [
        "library not accessible",
        "nas offline",
        "connection refused",
        "network is unreachable",
        "timed out",
    ],
    "ffmpeg-missing": [
        "filenotfounderror",
        "ffmpeg",
        "ffprobe",
        "no such file or directory",
    ],
    "permission-denied": [
        "permission denied",
        "access denied",
        "errno 13",
    ],
}


def _derive_root_cause(item: dict[str, Any]) -> str | None:
    """Return a root-cause ID when the item's message matches a known pattern."""
    text = f"{item.get('source', '')} {item.get('message', '')}".lower()
    for root_cause, patterns in _ROOT_CAUSE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                return root_cause
    return None


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def get_issue_dir(cache_dir: Path) -> Path:
    """Return the directory containing issue registry files."""
    return cache_dir / "issues"


def get_open_issues_path(cache_dir: Path) -> Path:
    """Return the JSON file that stores currently open issues."""
    return get_issue_dir(cache_dir) / "open_issues.json"


def get_issue_events_path(cache_dir: Path) -> Path:
    """Return the JSONL file containing all recorded issue observations."""
    return get_issue_dir(cache_dir) / "issue_events.jsonl"


def get_todo_candidates_path(cache_dir: Path) -> Path:
    """Return the JSON file containing derived scheduler task candidates."""
    return get_issue_dir(cache_dir) / "todo_candidates.json"


def get_scheduler_runs_path(cache_dir: Path) -> Path:
    """Return the JSONL file containing scheduler stub run summaries."""
    return get_issue_dir(cache_dir) / "scheduler_runs.jsonl"


def get_todo_state_path(cache_dir: Path) -> Path:
    """Return the JSON file storing scheduler task cooldown state."""
    return get_issue_dir(cache_dir) / "todo_state.json"


def _normalize_message(message: str) -> str:
    """Return a normalized one-line issue message."""
    return " ".join(str(message).strip().split())[:500]


def build_issue_key(source: str, severity: str, message: str, *, issue_key: str | None = None) -> str:
    """Return a stable issue key.

    Callers may provide an explicit ``issue_key`` when a domain-specific key is
    preferable (e.g. one key per media file). Otherwise a hash of source,
    severity and normalized message is used.
    """
    if issue_key:
        return issue_key
    raw = f"{source}|{severity.upper()}|{_normalize_message(message)}"
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()[:20]


def _severity_rank(severity: str) -> int:
    ranking = {"WARNING": 1, "ERROR": 2, "CRITICAL": 3}
    return ranking.get(severity.upper(), 0)


def normalize_severity(severity: str | None) -> str:
    """Return a canonical severity string."""
    value = str(severity or _DEFAULT_SEVERITY).strip().upper()
    if value not in {"WARNING", "ERROR", "CRITICAL"}:
        return _DEFAULT_SEVERITY
    return value


def _load_open_issues_unlocked(cache_dir: Path) -> dict[str, Any]:
    path = get_open_issues_path(cache_dir)
    try:
        if not path.exists():
            return {"version": _VERSION, "items": {}}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"version": _VERSION, "items": {}}
        items = payload.get("items")
        if not isinstance(items, dict):
            items = {}
        return {"version": payload.get("version", _VERSION), "items": items}
    except Exception:
        return {"version": _VERSION, "items": {}}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _append_event_unlocked(cache_dir: Path, event: dict[str, Any]) -> None:
    path = get_issue_events_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _append_scheduler_run_unlocked(cache_dir: Path, event: dict[str, Any]) -> None:
    path = get_scheduler_runs_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _load_todo_state_unlocked(cache_dir: Path) -> dict[str, Any]:
    path = get_todo_state_path(cache_dir)
    try:
        if not path.exists():
            return {"version": _VERSION, "items": {}}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"version": _VERSION, "items": {}}
        items = payload.get("items")
        if not isinstance(items, dict):
            items = {}
        return {"version": payload.get("version", _VERSION), "items": items}
    except Exception:
        return {"version": _VERSION, "items": {}}


def _parse_utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _derive_category(source: str, message: str) -> str:
    text = f"{source} {message}".lower()
    if "thumbnail" in text or "thumb" in text:
        return "thumbnail"
    if "metadata" in text or "mutagen" in text or "ffprobe" in text:
        return "metadata"
    if "sync" in text or "nas" in text:
        return "sync"
    if "cache" in text or "index" in text:
        return "cache"
    if "server" in text or "stream" in text:
        return "streaming"
    return "general"


def _suggested_action(category: str, item: dict[str, Any]) -> str:
    detail_keys = sorted((item.get("details") or {}).keys())
    details_hint = f" Details: {', '.join(detail_keys)}." if detail_keys else ""
    if category == "thumbnail":
        return "ffmpeg/ffprobe, Quelldatei und Schatten-Cache prüfen; Thumbnail-Prewarm nur bei Bedarf erneut ausführen." + details_hint
    if category == "metadata":
        return "Metadaten-Fallbacks und problematische Datei prüfen; Fehler sollte für den Aufrufer weich bleiben." + details_hint
    if category == "sync":
        return "NAS-/Sync-Konfiguration, Pfad-Erreichbarkeit und manuelle Sync-Ausführung prüfen." + details_hint
    if category == "cache":
        return "Index-/Cache-Zustand prüfen, ggf. gezielten Reset oder Prewarm für den betroffenen Server ausführen." + details_hint
    if category == "streaming":
        return "Server-Logs, Status-Endpunkte und letzte Änderungen im Shared Core prüfen." + details_hint
    return "Logs und betroffene Quelle prüfen; falls reproduzierbar, in eine konkrete Implementierungsaufgabe überführen." + details_hint


def _priority_from_issue(item: dict[str, Any]) -> str:
    return _priority_from_values(
        normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY))),
        int(item.get("count", 1)),
    )


def _priority_from_values(severity: str, count: int) -> str:
    severity = normalize_severity(severity)
    if severity == "CRITICAL":
        return "P1"
    if severity == "ERROR":
        return "P1" if count >= 5 else "P2"
    return "P2" if count >= 10 else "P3"


def _message_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    return (
        _severity_rank(str(item.get("severity", _DEFAULT_SEVERITY))),
        int(item.get("count", 1)),
        str(item.get("last_seen", "")),
    )


def _score_issue(item: dict[str, Any]) -> int:
    severity = normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY)))
    severity_score = {"WARNING": 10, "ERROR": 20, "CRITICAL": 30}[severity]
    count_bonus = min(int(item.get("count", 1)), 20)
    return severity_score + count_bonus


def _todo_candidate_from_issue(item: dict[str, Any]) -> dict[str, Any]:
    category = _derive_category(str(item.get("source", "")), str(item.get("message", "")))
    return {
        "todo_key": f"todo::{item.get('issue_key', '')}",
        "issue_key": item.get("issue_key", ""),
        "source": item.get("source", ""),
        "severity": normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY))),
        "priority": _priority_from_issue(item),
        "score": _score_issue(item),
        "category": category,
        "message": item.get("message", ""),
        "count": int(item.get("count", 1)),
        "status": "candidate",
        "first_seen": item.get("first_seen", ""),
        "last_seen": item.get("last_seen", ""),
        "suggested_action": _suggested_action(category, item),
        "details": item.get("details", {}) or {},
    }


def _build_todo_family_key(item: dict[str, Any], category: str) -> str:
    source = str(item.get("source", "")).strip() or "unknown"
    details = item.get("details") or {}
    explicit_family = details.get("issue_family") or details.get("family")
    if explicit_family:
        return f"{category}|{source}|{explicit_family}"
    root_cause = _derive_root_cause(item)
    if root_cause:
        return f"root-cause|{root_cause}"
    return f"{category}|{source}"


def _pick_group_representative(items: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(items, key=_message_sort_key, reverse=True)
    return ranked[0] if ranked else {}


def _aggregate_todo_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in items:
        category = _derive_category(str(item.get("source", "")), str(item.get("message", "")))
        family_key = _build_todo_family_key(item, category)
        group = groups.setdefault(
            family_key,
            {
                "category": category,
                "family_key": family_key,
                "source": str(item.get("source", "")),
                "issues": [],
                "messages": [],
                "issue_keys": [],
                "count": 0,
                "source_issue_count": 0,
                "first_seen": None,
                "last_seen": None,
                "severity": "WARNING",
            },
        )
        group["issues"].append(item)
        group["issue_keys"].append(str(item.get("issue_key", "")))
        message = str(item.get("message", "")).strip()
        if message and message not in group["messages"]:
            group["messages"].append(message)
        group["count"] += int(item.get("count", 1))
        group["source_issue_count"] += 1
        first_seen = str(item.get("first_seen", ""))
        last_seen = str(item.get("last_seen", ""))
        if first_seen and (group["first_seen"] is None or first_seen < group["first_seen"]):
            group["first_seen"] = first_seen
        if last_seen and (group["last_seen"] is None or last_seen > group["last_seen"]):
            group["last_seen"] = last_seen
        if _severity_rank(str(item.get("severity", _DEFAULT_SEVERITY))) >= _severity_rank(str(group["severity"])):
            group["severity"] = normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY)))

    candidates: list[dict[str, Any]] = []
    for family_key, group in groups.items():
        representative = _pick_group_representative(group["issues"])
        representative_key = str(representative.get("issue_key", ""))
        count = int(group["count"])
        severity = normalize_severity(str(group["severity"]))
        category = str(group["category"])
        unique_messages = list(group["messages"])[:3]
        summary_message = (
            unique_messages[0]
            if len(unique_messages) == 1
            else (f"{int(group['source_issue_count'])} similar {category} issue(s); latest: {unique_messages[0]}")
        )
        todo_key = build_issue_key(
            str(group["source"]),
            severity,
            family_key,
            issue_key=f"todo::{build_issue_key(str(group['source']), severity, family_key)}",
        )
        candidate = {
            "todo_key": todo_key,
            "issue_key": representative_key,
            "issue_keys": list(group["issue_keys"]),
            "family_key": family_key,
            "source": str(group["source"]),
            "severity": severity,
            "priority": _priority_from_values(severity, count),
            "score": {"WARNING": 10, "ERROR": 20, "CRITICAL": 30}[severity] + min(count, 20) + min(int(group["source_issue_count"]), 10),
            "category": category,
            "message": summary_message,
            "messages": unique_messages,
            "count": count,
            "source_issue_count": int(group["source_issue_count"]),
            "status": "candidate",
            "first_seen": group["first_seen"] or "",
            "last_seen": group["last_seen"] or "",
            "suggested_action": _suggested_action(category, representative),
            "action_hints": _derive_action_hints(category, str(group["source"])),
            "details": representative.get("details", {}) or {},
        }
        candidates.append(candidate)
    return candidates


def _should_emit_todo(todo_state: dict[str, Any], candidate: dict[str, Any], cooldown_seconds: int) -> bool:
    return _todo_runtime_state(todo_state, candidate, cooldown_seconds) == "active"


def _todo_runtime_state(todo_state: dict[str, Any], candidate: dict[str, Any], cooldown_seconds: int) -> str:
    items = todo_state.get("items") if isinstance(todo_state, dict) else None
    if not isinstance(items, dict):
        return "active"
    previous = items.get(str(candidate.get("todo_key", "")))
    if not isinstance(previous, dict):
        return "active"
    previous_severity = normalize_severity(str(previous.get("severity", _DEFAULT_SEVERITY)))
    current_severity = normalize_severity(str(candidate.get("severity", _DEFAULT_SEVERITY)))
    if _severity_rank(current_severity) > _severity_rank(previous_severity):
        return "active"
    state = str(previous.get("state", "active")).strip().lower()
    if state == "acknowledged":
        return "acknowledged"
    if state == "snoozed":
        snoozed_until = _parse_utc_timestamp(str(previous.get("snoozed_until", "")))
        if snoozed_until is not None and snoozed_until > datetime.now(timezone.utc):
            return "snoozed"
    previous_time = _parse_utc_timestamp(str(previous.get("last_emitted_at", "")))
    if previous_time is None:
        return "active"
    elapsed_seconds = (datetime.now(timezone.utc) - previous_time).total_seconds()
    if elapsed_seconds >= max(int(cooldown_seconds), 0):
        return "active"
    return "cooldown"


def _update_todo_state_unlocked(todo_state: dict[str, Any], active_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    items = todo_state.get("items") if isinstance(todo_state, dict) else None
    if not isinstance(items, dict):
        items = {}
    for candidate in active_candidates:
        updated_at = _utc_now()
        items[str(candidate.get("todo_key", ""))] = {
            "last_emitted_at": updated_at,
            "severity": normalize_severity(str(candidate.get("severity", _DEFAULT_SEVERITY))),
            "score": int(candidate.get("score", 0)),
            "message": str(candidate.get("message", "")),
            "state": "active",
            "updated_at": updated_at,
            "acknowledged_at": None,
            "snoozed_until": None,
            "reason": "",
        }
    return {"version": _VERSION, "items": items}


def _filter_items_by_severity(items: list[dict[str, Any]], min_severity: str) -> list[dict[str, Any]]:
    threshold = _severity_rank(normalize_severity(min_severity))
    return [item for item in items if _severity_rank(str(item.get("severity", _DEFAULT_SEVERITY))) >= threshold]


def _build_issue_summary_from_items(items: list[dict[str, Any]], min_severity: str) -> dict[str, Any]:
    summary = {
        "min_severity": normalize_severity(min_severity),
        "count": len(items),
        "warnings": 0,
        "errors": 0,
        "criticals": 0,
        "items": items,
        "top_issue": None,
    }
    for item in items:
        severity = normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY)))
        if severity == "CRITICAL":
            summary["criticals"] += 1
        elif severity == "ERROR":
            summary["errors"] += 1
        else:
            summary["warnings"] += 1

    if items:
        ranked = sorted(
            items,
            key=lambda item: (
                _severity_rank(str(item.get("severity", _DEFAULT_SEVERITY))),
                int(item.get("count", 1)),
                str(item.get("last_seen", "")),
            ),
            reverse=True,
        )
        top = ranked[0]
        summary["top_issue"] = {
            "issue_key": top.get("issue_key", ""),
            "source": top.get("source", ""),
            "severity": normalize_severity(str(top.get("severity", _DEFAULT_SEVERITY))),
            "message": top.get("message", ""),
            "count": int(top.get("count", 1)),
        }
    return summary


def _build_todo_payload_from_items(items: list[dict[str, Any]], min_severity: str, max_items: int | None = None) -> dict[str, Any]:
    ranked_issues = sorted(
        items,
        key=lambda item: (_score_issue(item), str(item.get("last_seen", "")), str(item.get("issue_key", ""))),
        reverse=True,
    )
    all_candidates = _aggregate_todo_candidates(ranked_issues)
    candidates = [c for c in all_candidates if _apply_noise_rules(c)]
    noise_suppressed_count = len(all_candidates) - len(candidates)
    candidates.sort(
        key=lambda item: (int(item.get("score", 0)), str(item.get("last_seen", "")), str(item.get("todo_key", ""))),
        reverse=True,
    )
    if max_items is not None and max_items > 0:
        candidates = candidates[:max_items]
    return {
        "version": _VERSION,
        "generated_at": _utc_now(),
        "min_severity": normalize_severity(min_severity),
        "source_issue_count": len(items),
        "count": len(candidates),
        "noise_suppressed_count": noise_suppressed_count,
        "items": candidates,
        "top_todo": candidates[0] if candidates else None,
    }


def _build_todo_summary_from_payload(payload: dict[str, Any], todo_state: dict[str, Any], cooldown_seconds: int) -> dict[str, Any]:
    items = list(payload.get("items", []))
    active_items: list[dict[str, Any]] = []
    acknowledged_items: list[dict[str, Any]] = []
    snoozed_items: list[dict[str, Any]] = []
    cooldown_items: list[dict[str, Any]] = []
    for item in items:
        state = _todo_runtime_state(todo_state, item, cooldown_seconds)
        if state == "acknowledged":
            acknowledged_items.append(item)
        elif state == "snoozed":
            snoozed_items.append(item)
        elif state == "cooldown":
            cooldown_items.append(item)
        else:
            active_items.append(item)
    top_todo = active_items[0] if active_items else (items[0] if items else None)
    state_items = todo_state.get("items") if isinstance(todo_state, dict) else None
    if not isinstance(state_items, dict):
        state_items = {}

    def _public_item(item: dict[str, Any]) -> dict[str, Any]:
        todo_key = str(item.get("todo_key", ""))
        persisted = state_items.get(todo_key)
        persisted_dict = persisted if isinstance(persisted, dict) else {}
        runtime_state = _todo_runtime_state(todo_state, item, cooldown_seconds)
        return {
            "todo_key": todo_key,
            "severity": normalize_severity(str(item.get("severity", _DEFAULT_SEVERITY))),
            "priority": str(item.get("priority", "P3")),
            "category": str(item.get("category", "general")),
            "message": str(item.get("message", "")),
            "suggested_action": str(item.get("suggested_action", "")),
            "action_hints": list(item.get("action_hints") or []),
            "state": runtime_state,
            "reason": str(persisted_dict.get("reason", "")),
            "snoozed_until": persisted_dict.get("snoozed_until"),
            "count": int(item.get("count", 0)),
        }

    public_items = [_public_item(item) for item in items[:_DEFAULT_TODO_UI_LIMIT]]
    return {
        "min_severity": payload.get("min_severity", normalize_severity(_DEFAULT_SEVERITY)),
        "count": len(items),
        "source_issue_count": int(payload.get("source_issue_count", 0)),
        "noise_suppressed_count": int(payload.get("noise_suppressed_count", 0)),
        "active_count": len(active_items),
        "acknowledged_count": len(acknowledged_items),
        "snoozed_count": len(snoozed_items),
        "cooldown_count": len(cooldown_items),
        "items": public_items,
        "top_todo": top_todo,
    }


def _find_todo_candidate_by_key(cache_dir: Path, todo_key: str, *, min_severity: str = _DEFAULT_SEVERITY) -> dict[str, Any] | None:
    payload = generate_todo_candidates(cache_dir, min_severity=min_severity, persist=False)
    for item in payload.get("items", []):
        if str(item.get("todo_key", "")) == str(todo_key):
            return item
    return None


def _write_todo_state_item(
    cache_dir: Path,
    todo_key: str,
    *,
    state: str,
    reason: str = "",
    snooze_seconds: int | None = None,
    min_severity: str = _DEFAULT_SEVERITY,
) -> dict[str, Any]:
    candidate = _find_todo_candidate_by_key(cache_dir, todo_key, min_severity=min_severity)
    if candidate is None and state != "cleared":
        return {"ok": False, "todo_key": todo_key, "state": "missing", "message": "Task candidate not found"}

    try:
        with _LOCK:
            payload = _load_todo_state_unlocked(cache_dir)
            items = payload.get("items")
            if not isinstance(items, dict):
                items = {}
            if state == "cleared":
                removed = items.pop(str(todo_key), None)
                _atomic_write_json(get_todo_state_path(cache_dir), {"version": _VERSION, "items": items})
                return {
                    "ok": bool(removed is not None),
                    "todo_key": todo_key,
                    "state": "cleared",
                    "message": "Task state cleared" if removed is not None else "Task state not found",
                }

            updated_at = _utc_now()
            entry = dict(items.get(str(todo_key), {})) if isinstance(items.get(str(todo_key)), dict) else {}
            entry.update(
                {
                    "severity": normalize_severity(str(candidate.get("severity", _DEFAULT_SEVERITY))),
                    "score": int(candidate.get("score", 0)),
                    "message": str(candidate.get("message", "")),
                    "updated_at": updated_at,
                    "reason": str(reason or "").strip(),
                    "state": state,
                }
            )
            if state == "acknowledged":
                entry["acknowledged_at"] = updated_at
                entry["snoozed_until"] = None
            elif state == "snoozed":
                snooze_for = max(int(snooze_seconds or 0), 1)
                entry["snoozed_until"] = (datetime.now(timezone.utc) + timedelta(seconds=snooze_for)).isoformat()
            items[str(todo_key)] = entry
            _atomic_write_json(get_todo_state_path(cache_dir), {"version": _VERSION, "items": items})
        return {
            "ok": True,
            "todo_key": todo_key,
            "state": state,
            "message": str(candidate.get("message", "")),
            "reason": str(reason or "").strip(),
            "snoozed_until": entry.get("snoozed_until"),
        }
    except Exception:
        return {"ok": False, "todo_key": todo_key, "state": state, "message": "Failed to update task state"}


def acknowledge_todo(cache_dir: Path, todo_key: str, *, reason: str = "", min_severity: str = _DEFAULT_SEVERITY) -> dict[str, Any]:
    """Acknowledge a grouped task so it stays suppressed until severity escalates."""
    return _write_todo_state_item(cache_dir, todo_key, state="acknowledged", reason=reason, min_severity=min_severity)


def snooze_todo(
    cache_dir: Path,
    todo_key: str,
    *,
    seconds: int,
    reason: str = "",
    min_severity: str = _DEFAULT_SEVERITY,
) -> dict[str, Any]:
    """Snooze a grouped task for a bounded duration."""
    return _write_todo_state_item(cache_dir, todo_key, state="snoozed", reason=reason, snooze_seconds=seconds, min_severity=min_severity)


def clear_todo_state(cache_dir: Path, todo_key: str) -> dict[str, Any]:
    """Clear any persisted acknowledge/snooze state for a grouped task."""
    return _write_todo_state_item(cache_dir, todo_key, state="cleared")


def update_todo_state_action(
    cache_dir: Path,
    *,
    todo_key: str,
    action: str,
    reason: str = "",
    seconds: int = _DEFAULT_TODO_COOLDOWN_SECONDS,
    min_severity: str = _DEFAULT_SEVERITY,
) -> dict[str, Any]:
    """Apply a UI/API friendly task state action and return the operation result."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action == "acknowledge":
        return acknowledge_todo(cache_dir, todo_key, reason=reason, min_severity=min_severity)
    if normalized_action == "snooze":
        return snooze_todo(cache_dir, todo_key, seconds=max(int(seconds), 1), reason=reason, min_severity=min_severity)
    if normalized_action == "clear":
        return clear_todo_state(cache_dir, todo_key)
    return {
        "ok": False,
        "todo_key": todo_key,
        "state": "invalid",
        "message": f"Unsupported action: {action}",
    }


def summarize_todos(
    cache_dir: Path,
    *,
    min_severity: str = _DEFAULT_SEVERITY,
    cooldown_seconds: int = _DEFAULT_TODO_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    """Return a compact summary of grouped tasks and their current runtime state."""
    normalized_min_severity = normalize_severity(min_severity)
    try:
        all_items = load_open_issues(cache_dir)
        filtered_items = _filter_items_by_severity(all_items, normalized_min_severity)
        payload = _build_todo_payload_from_items(filtered_items, normalized_min_severity)
        with _LOCK:
            todo_state = _load_todo_state_unlocked(cache_dir)
        return _build_todo_summary_from_payload(payload, todo_state, cooldown_seconds)
    except Exception:
        return {
            "min_severity": normalized_min_severity,
            "count": 0,
            "source_issue_count": 0,
            "active_count": 0,
            "acknowledged_count": 0,
            "snoozed_count": 0,
            "cooldown_count": 0,
            "items": [],
            "top_todo": None,
        }


def summarize_issue_and_todos(
    cache_dir: Path,
    *,
    min_severity: str = _DEFAULT_SEVERITY,
    cooldown_seconds: int = _DEFAULT_TODO_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    """Return issue and task summaries using a single open-issue load."""
    normalized_min_severity = normalize_severity(min_severity)
    try:
        all_items = load_open_issues(cache_dir)
        filtered_items = _filter_items_by_severity(all_items, normalized_min_severity)
        issue_summary = _build_issue_summary_from_items(filtered_items, normalized_min_severity)
        todo_payload = _build_todo_payload_from_items(filtered_items, normalized_min_severity)
        with _LOCK:
            todo_state = _load_todo_state_unlocked(cache_dir)
        todo_summary = _build_todo_summary_from_payload(todo_payload, todo_state, cooldown_seconds)
        return {"issues": issue_summary, "todos": todo_summary}
    except Exception:
        return {
            "issues": _build_issue_summary_from_items([], normalized_min_severity),
            "todos": {
                "min_severity": normalized_min_severity,
                "count": 0,
                "source_issue_count": 0,
                "active_count": 0,
                "acknowledged_count": 0,
                "snoozed_count": 0,
                "cooldown_count": 0,
                "items": [],
                "top_todo": None,
            },
        }


def load_open_issues(cache_dir: Path) -> list[dict[str, Any]]:
    """Return all open issues as a stable list.

    Never raises. Returns an empty list on failure.
    """
    with _LOCK:
        payload = _load_open_issues_unlocked(cache_dir)
    items = payload.get("items", {})
    result = [dict(value, issue_key=key) for key, value in items.items() if isinstance(value, dict)]
    result.sort(key=lambda item: (item.get("source", ""), item.get("first_seen", ""), item.get("issue_key", "")))
    return result


def filter_open_issues(cache_dir: Path, *, min_severity: str = _DEFAULT_SEVERITY) -> list[dict[str, Any]]:
    """Return open issues at or above the given severity threshold."""
    return _filter_items_by_severity(load_open_issues(cache_dir), min_severity)


def record_issue(
    cache_dir: Path,
    *,
    source: str,
    severity: str,
    message: str,
    issue_key: str | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    """Record or update an open irregularity.

    Returns the effective issue key. Never raises.
    """
    normalized_message = _normalize_message(message)
    normalized_severity = normalize_severity(severity)
    effective_key = build_issue_key(source, normalized_severity, normalized_message, issue_key=issue_key)
    event = {
        "timestamp": _utc_now(),
        "issue_key": effective_key,
        "source": source,
        "severity": normalized_severity,
        "message": normalized_message,
        "details": details or {},
    }

    try:
        with _LOCK:
            payload = _load_open_issues_unlocked(cache_dir)
            items = payload["items"]
            current = items.get(effective_key)
            if isinstance(current, dict):
                current["last_seen"] = event["timestamp"]
                current["count"] = int(current.get("count", 1)) + 1
                if _severity_rank(event["severity"]) >= _severity_rank(str(current.get("severity", "WARNING"))):
                    current["severity"] = event["severity"]
                current["message"] = normalized_message or str(current.get("message", ""))
                current["details"] = details or current.get("details", {})
                current["status"] = "open"
                items[effective_key] = current
            else:
                items[effective_key] = {
                    "source": source,
                    "severity": event["severity"],
                    "message": normalized_message,
                    "details": details or {},
                    "status": "open",
                    "count": 1,
                    "first_seen": event["timestamp"],
                    "last_seen": event["timestamp"],
                }
            _atomic_write_json(get_open_issues_path(cache_dir), payload)
            _append_event_unlocked(cache_dir, {**event, "action": "recorded"})
    except Exception:
        return effective_key

    return effective_key


def resolve_issue(cache_dir: Path, issue_key: str, *, resolution: str = "resolved") -> bool:
    """Mark an issue as resolved by removing it from the open registry.

    Returns ``True`` when an open issue was removed. Never raises.
    """
    try:
        with _LOCK:
            payload = _load_open_issues_unlocked(cache_dir)
            items = payload["items"]
            existing = items.pop(issue_key, None)
            if existing is None:
                return False
            _atomic_write_json(get_open_issues_path(cache_dir), payload)
            _append_event_unlocked(
                cache_dir,
                {
                    "timestamp": _utc_now(),
                    "issue_key": issue_key,
                    "source": existing.get("source", ""),
                    "severity": existing.get("severity", "WARNING"),
                    "message": existing.get("message", ""),
                    "details": {"resolution": resolution},
                    "action": "resolved",
                },
            )
            return True
    except Exception:
        return False


def summarize_open_issues(cache_dir: Path, *, min_severity: str = _DEFAULT_SEVERITY) -> dict[str, Any]:
    """Return a compact scheduler-friendly summary of current open issues."""
    items = filter_open_issues(cache_dir, min_severity=min_severity)
    return _build_issue_summary_from_items(items, min_severity)


def generate_todo_candidates(
    cache_dir: Path,
    *,
    min_severity: str = _DEFAULT_SEVERITY,
    max_items: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Derive scheduler task candidates from the current open issues.

    Never raises. Optionally persists the generated payload to
    ``todo_candidates.json`` for later scheduler/dashboard use.
    """
    normalized_min_severity = normalize_severity(min_severity)
    if max_items is not None and max_items <= 0:
        max_items = None

    try:
        source_items = filter_open_issues(cache_dir, min_severity=normalized_min_severity)
        payload = _build_todo_payload_from_items(source_items, normalized_min_severity, max_items=max_items)
        if persist:
            _atomic_write_json(get_todo_candidates_path(cache_dir), payload)
        return payload
    except Exception:
        return {
            "version": _VERSION,
            "generated_at": _utc_now(),
            "min_severity": normalized_min_severity,
            "source_issue_count": 0,
            "count": 0,
            "items": [],
            "top_todo": None,
        }


def run_scheduler_once(
    cache_dir: Path,
    *,
    min_severity: str = _DEFAULT_SEVERITY,
    max_items: int | None = None,
    cooldown_seconds: int = _DEFAULT_TODO_COOLDOWN_SECONDS,
) -> dict[str, Any]:
    """Run the first scheduler stub once and persist derived task candidates.

    This intentionally does not execute any maintenance action yet. It only
    translates current open issues into a stable task candidate file and appends
    a compact scheduler-run event for automation.
    """
    normalized_min_severity = normalize_severity(min_severity)
    try:
        todos = generate_todo_candidates(cache_dir, min_severity=normalized_min_severity, max_items=max_items, persist=True)
        with _LOCK:
            todo_state = _load_todo_state_unlocked(cache_dir)
            active_items = [item for item in todos.get("items", []) if _should_emit_todo(todo_state, item, cooldown_seconds)]
            suppressed_items = [item for item in todos.get("items", []) if item not in active_items]
            new_state = _update_todo_state_unlocked(todo_state, active_items)
            _atomic_write_json(get_todo_state_path(cache_dir), new_state)
        # Collect deduplicated action hints from active tasks
        seen_action_ids: set[str] = set()
        action_hints: list[dict[str, str]] = []
        for item in active_items:
            for hint in item.get("action_hints") or []:
                aid = str(hint.get("action_id", ""))
                if aid and aid not in seen_action_ids:
                    seen_action_ids.add(aid)
                    action_hints.append(hint)
        result = {
            "timestamp": _utc_now(),
            "status": "ok",
            "min_severity": normalized_min_severity,
            "cooldown_seconds": max(int(cooldown_seconds), 0),
            "open_issue_count": int(todos.get("source_issue_count", 0)),
            "todo_count": int(todos.get("count", 0)),
            "noise_suppressed_count": int(todos.get("noise_suppressed_count", 0)),
            "active_todo_count": len(active_items),
            "suppressed_todo_count": len(suppressed_items),
            "active_items": active_items,
            "suppressed_keys": [str(item.get("todo_key", "")) for item in suppressed_items],
            "action_hints": action_hints,
            "todo_candidates_path": str(get_todo_candidates_path(cache_dir)),
            "top_todo": active_items[0] if active_items else todos.get("top_todo"),
        }
        with _LOCK:
            _append_scheduler_run_unlocked(cache_dir, result)
        return result
    except Exception:
        return {
            "timestamp": _utc_now(),
            "status": "error",
            "min_severity": normalized_min_severity,
            "cooldown_seconds": max(int(cooldown_seconds), 0),
            "open_issue_count": 0,
            "todo_count": 0,
            "noise_suppressed_count": 0,
            "active_todo_count": 0,
            "suppressed_todo_count": 0,
            "active_items": [],
            "suppressed_keys": [],
            "action_hints": [],
            "todo_candidates_path": str(get_todo_candidates_path(cache_dir)),
            "top_todo": None,
        }
