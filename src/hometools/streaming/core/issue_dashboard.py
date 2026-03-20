"""CLI dashboard for streaming issues and task candidates.

Combines issue summaries, task state and last scheduler run into a single
compact table view. Data retrieval is delegated to :mod:`issue_registry`;
this module handles only presentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hometools.streaming.core.issue_registry import (
    _DEFAULT_SEVERITY,
    _DEFAULT_TODO_COOLDOWN_SECONDS,
    get_scheduler_runs_path,
    normalize_severity,
    summarize_issue_and_todos,
)


def _load_last_scheduler_run(cache_dir: Path) -> dict[str, Any] | None:
    """Return the most recent scheduler run event, or *None*."""
    path = get_scheduler_runs_path(cache_dir)
    try:
        if not path.exists():
            return None
        last_line = ""
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return None
        return json.loads(last_line)
    except Exception:
        return None


def build_dashboard_data(
    cache_dir: Path,
    *,
    min_severity: str = _DEFAULT_SEVERITY,
    cooldown_seconds: int = _DEFAULT_TODO_COOLDOWN_SECONDS,
    max_todo_items: int = 5,
) -> dict[str, Any]:
    """Return a combined dashboard payload (issues + TODOs + last scheduler run).

    Never raises — returns sensible empty defaults on failure.
    """
    normalized = normalize_severity(min_severity)
    try:
        combined = summarize_issue_and_todos(
            cache_dir,
            min_severity=normalized,
            cooldown_seconds=cooldown_seconds,
        )
        issues = combined["issues"]
        todos = combined["todos"]

        # Re-limit items for dashboard context (may differ from API limit)
        all_todo_items = list(todos.get("items", []))
        todos["items"] = all_todo_items[:max_todo_items]

        last_run = _load_last_scheduler_run(cache_dir)

        return {
            "cache_dir": str(cache_dir),
            "min_severity": normalized,
            "issues": issues,
            "todos": todos,
            "last_scheduler_run": last_run,
        }
    except Exception:
        return {
            "cache_dir": str(cache_dir),
            "min_severity": normalized,
            "issues": {
                "min_severity": normalized,
                "count": 0,
                "warnings": 0,
                "errors": 0,
                "criticals": 0,
                "items": [],
                "top_issue": None,
            },
            "todos": {
                "min_severity": normalized,
                "count": 0,
                "source_issue_count": 0,
                "active_count": 0,
                "acknowledged_count": 0,
                "snoozed_count": 0,
                "cooldown_count": 0,
                "items": [],
                "top_todo": None,
            },
            "last_scheduler_run": None,
        }


def format_dashboard_table(data: dict[str, Any]) -> str:
    """Render the dashboard payload as a compact box-drawing table."""
    issues = data.get("issues") or {}
    todos = data.get("todos") or {}
    last_run = data.get("last_scheduler_run")

    # --- determine column width ---
    value_strings: list[str] = []
    value_strings.append(str(data.get("cache_dir", "")))
    value_strings.append(str(data.get("min_severity", "")))
    value_strings.append(
        f"{issues.get('count', 0)} total  (W={issues.get('warnings', 0)} E={issues.get('errors', 0)} C={issues.get('criticals', 0)})"
    )
    top_issue = issues.get("top_issue")
    if isinstance(top_issue, dict):
        value_strings.append(f"[{top_issue.get('severity', '?')}] {top_issue.get('source', '?')}: {top_issue.get('message', '')}")
    value_strings.append(
        f"active={todos.get('active_count', 0)} ack={todos.get('acknowledged_count', 0)} "
        f"snoozed={todos.get('snoozed_count', 0)} cooldown={todos.get('cooldown_count', 0)}"
    )
    for item in todos.get("items", []):
        value_strings.append(f"[{item.get('priority', '?')}/{item.get('severity', '?')}] {item.get('message', '')}")
    if isinstance(last_run, dict):
        value_strings.append(str(last_run.get("timestamp", "")))
        value_strings.append(
            f"status={last_run.get('status', '?')} active={last_run.get('active_todo_count', 0)} "
            f"suppressed={last_run.get('suppressed_todo_count', 0)}"
        )
    for item in todos.get("items", []):
        for hint in item.get("action_hints") or []:
            cmd = str(hint.get("cli_command", ""))
            label = str(hint.get("label", ""))
            value_strings.append(f"→ {label}: {cmd}" if label else f"→ {cmd}")

    label_width = 12
    min_value_width = 40
    w = max(min_value_width, *(len(v) for v in value_strings)) + 2

    def row(label: str, value: str) -> str:
        return f"│  {label:<{label_width}s}│  {value:<{w}s}│"

    sep = f"├{'─' * (label_width + 2)}┼{'─' * (w + 2)}┤"
    top = f"┌{'─' * (label_width + 2)}┬{'─' * (w + 2)}┐"
    bot = f"└{'─' * (label_width + 2)}┴{'─' * (w + 2)}┘"

    title_text = "hometools streaming dashboard"
    title = f"│  {title_text:<{label_width + w + 3}s}│"

    lines: list[str] = [top, title, sep]

    # Issues section
    lines.append(
        row(
            "Issues",
            f"{issues.get('count', 0)} total  (W={issues.get('warnings', 0)} E={issues.get('errors', 0)} C={issues.get('criticals', 0)})",
        )
    )
    if isinstance(top_issue, dict):
        lines.append(
            row(
                "",
                f"Top: [{top_issue.get('severity', '?')}] {top_issue.get('source', '?')}: {top_issue.get('message', '')}",
            )
        )

    lines.append(sep)

    # TODOs section
    noise_suppressed = int(todos.get("noise_suppressed_count", 0))
    todo_summary_parts = [
        f"active={todos.get('active_count', 0)}",
        f"ack={todos.get('acknowledged_count', 0)}",
        f"snoozed={todos.get('snoozed_count', 0)}",
        f"cooldown={todos.get('cooldown_count', 0)}",
    ]
    if noise_suppressed:
        todo_summary_parts.append(f"noise={noise_suppressed}")
    lines.append(row("TODOs", " ".join(todo_summary_parts)))
    todo_items = todos.get("items", [])
    for item in todo_items:
        state_tag = f" ({item.get('state', 'active')})" if item.get("state", "active") != "active" else ""
        lines.append(
            row(
                "",
                f"[{item.get('priority', '?')}/{item.get('severity', '?')}] {item.get('message', '')}{state_tag}",
            )
        )
    if not todo_items:
        lines.append(row("", "No task candidates."))

    lines.append(sep)

    # Scheduler section
    if isinstance(last_run, dict):
        lines.append(row("Scheduler", str(last_run.get("timestamp", "—"))))
        lines.append(
            row(
                "",
                f"status={last_run.get('status', '?')} active={last_run.get('active_todo_count', 0)} "
                f"suppressed={last_run.get('suppressed_todo_count', 0)}",
            )
        )
    else:
        lines.append(row("Scheduler", "No runs recorded."))

    lines.append(sep)

    # Action hints section
    all_hints: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in todos.get("items", []):
        for hint in item.get("action_hints") or []:
            aid = str(hint.get("action_id", ""))
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                all_hints.append(hint)
    if isinstance(last_run, dict):
        for hint in last_run.get("action_hints") or []:
            aid = str(hint.get("action_id", ""))
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                all_hints.append(hint)
    if all_hints:
        lines.append(row("Actions", f"{len(all_hints)} recommended"))
        for hint in all_hints:
            cmd = str(hint.get("cli_command", ""))
            label = str(hint.get("label", ""))
            lines.append(row("", f"→ {label}: {cmd}" if label else f"→ {cmd}"))
    else:
        lines.append(row("Actions", "No action hints."))

    lines.append(sep)

    # Footer
    lines.append(row("Filter", f">= {data.get('min_severity', 'WARNING')}"))
    lines.append(row("Cache dir", str(data.get("cache_dir", ""))))

    lines.append(bot)

    return "\n".join(lines)
