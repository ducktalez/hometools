"""Tests for the persistent open-issues registry and logging integration."""

from __future__ import annotations

import json
import logging
from argparse import Namespace

from hometools.cli import run_stream_issues, run_stream_scheduler, run_stream_todo_state, run_stream_todos
from hometools.logging_config import OpenIssuesHandler
from hometools.streaming.core.issue_registry import (
    acknowledge_todo,
    clear_todo_state,
    filter_open_issues,
    generate_todo_candidates,
    get_scheduler_runs_path,
    get_todo_candidates_path,
    get_todo_state_path,
    load_open_issues,
    record_issue,
    resolve_issue,
    run_scheduler_once,
    snooze_todo,
    summarize_issue_and_todos,
    summarize_open_issues,
    summarize_todos,
)


def test_record_issue_updates_open_issue_count(tmp_path):
    record_issue(tmp_path, source="hometools.test", severity="WARNING", message="NAS slow")
    record_issue(tmp_path, source="hometools.test", severity="WARNING", message="NAS slow")

    items = load_open_issues(tmp_path)

    assert len(items) == 1
    assert items[0]["count"] == 2
    assert items[0]["severity"] == "WARNING"
    assert (tmp_path / "issues" / "issue_events.jsonl").exists()


def test_resolve_issue_removes_open_issue(tmp_path):
    issue_key = record_issue(tmp_path, source="hometools.test", severity="ERROR", message="Index failed")

    assert resolve_issue(tmp_path, issue_key, resolution="fixed") is True
    assert load_open_issues(tmp_path) == []


def test_summarize_open_issues_counts_severity(tmp_path):
    record_issue(tmp_path, source="hometools.a", severity="WARNING", message="warn")
    record_issue(tmp_path, source="hometools.b", severity="ERROR", message="err")
    record_issue(tmp_path, source="hometools.c", severity="CRITICAL", message="boom")

    summary = summarize_open_issues(tmp_path)

    assert summary["count"] == 3
    assert summary["warnings"] == 1
    assert summary["errors"] == 1
    assert summary["criticals"] == 1
    assert summary["top_issue"]["severity"] == "CRITICAL"


def test_filter_open_issues_respects_min_severity(tmp_path):
    record_issue(tmp_path, source="hometools.a", severity="WARNING", message="warn")
    record_issue(tmp_path, source="hometools.b", severity="ERROR", message="err")

    items = filter_open_issues(tmp_path, min_severity="error")

    assert len(items) == 1
    assert items[0]["severity"] == "ERROR"


def test_summarize_open_issues_respects_min_severity(tmp_path):
    record_issue(tmp_path, source="hometools.a", severity="WARNING", message="warn")
    record_issue(tmp_path, source="hometools.b", severity="ERROR", message="err")

    summary = summarize_open_issues(tmp_path, min_severity="error")

    assert summary["min_severity"] == "ERROR"
    assert summary["count"] == 1
    assert summary["warnings"] == 0
    assert summary["errors"] == 1


def test_open_issues_handler_records_warning(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    logger = logging.getLogger("hometools.test.logger")
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(OpenIssuesHandler())

    logger.warning("Something odd happened")

    items = load_open_issues(tmp_path)
    assert len(items) == 1
    assert items[0]["message"] == "Something odd happened"
    assert items[0]["source"] == "hometools.test.logger"


def test_open_issues_handler_ignores_non_hometools_logger(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    logger = logging.getLogger("external.test.logger")
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(OpenIssuesHandler())

    logger.error("Should be ignored")

    assert load_open_issues(tmp_path) == []


def test_thumbnail_failure_registry_also_records_open_issue(tmp_path):
    from hometools.streaming.core.thumbnailer import record_failure

    failures: dict[str, dict] = {}
    record_failure(
        failures,
        "audio",
        "Artist/Song.mp3",
        "cover missing",
        123.0,
        tmp_path,
    )

    items = load_open_issues(tmp_path)
    assert len(items) == 1
    assert items[0]["issue_key"] == "thumbnail::audio::Artist/Song.mp3"
    assert "Thumbnail generation failed" in items[0]["message"]

    payload = json.loads((tmp_path / "issues" / "open_issues.json").read_text(encoding="utf-8"))
    assert "thumbnail::audio::Artist/Song.mp3" in payload["items"]


def test_stream_issues_returns_nonzero_when_filtered_match_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.test", severity="ERROR", message="boom")

    rc = run_stream_issues(
        Namespace(
            json=True,
            min_severity="warning",
            only_errors=True,
            fail_on_match=True,
        )
    )

    assert rc == 1


def test_generate_todo_candidates_prioritizes_critical_and_persists(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.cache", severity="WARNING", message="cache stale")
    record_issue(tmp_path, source="hometools.streaming.metadata", severity="CRITICAL", message="metadata parser crashed")

    payload = generate_todo_candidates(tmp_path)

    assert payload["count"] == 2
    assert payload["top_todo"]["severity"] == "CRITICAL"
    assert payload["top_todo"]["priority"] == "P1"
    assert payload["top_todo"]["category"] == "metadata"
    saved = json.loads(get_todo_candidates_path(tmp_path).read_text(encoding="utf-8"))
    assert saved["items"][0]["issue_key"] == payload["top_todo"]["issue_key"]


def test_generate_todo_candidates_groups_similar_issues_by_family(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="WARNING", message="thumbnail failed for A")
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed for B")

    payload = generate_todo_candidates(tmp_path)

    assert payload["source_issue_count"] == 2
    assert payload["count"] == 1
    assert payload["items"][0]["source_issue_count"] == 2
    assert len(payload["items"][0]["issue_keys"]) == 2
    assert payload["items"][0]["category"] == "thumbnail"


def test_generate_todo_candidates_respects_max_items(tmp_path):
    record_issue(tmp_path, source="hometools.a", severity="WARNING", message="warn-a")
    record_issue(tmp_path, source="hometools.a", severity="WARNING", message="warn-a-2")
    record_issue(tmp_path, source="hometools.b", severity="ERROR", message="warn-b")

    payload = generate_todo_candidates(tmp_path, max_items=1)

    assert payload["source_issue_count"] == 3
    assert payload["count"] == 1


def test_run_scheduler_once_writes_run_log_and_todo_file(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")

    result = run_scheduler_once(tmp_path, min_severity="warning", cooldown_seconds=3600)

    assert result["status"] == "ok"
    assert result["todo_count"] == 1
    assert result["active_todo_count"] == 1
    assert get_todo_candidates_path(tmp_path).exists()
    run_lines = get_scheduler_runs_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(run_lines) == 1
    event = json.loads(run_lines[0])
    assert event["todo_count"] == 1


def test_run_scheduler_once_suppresses_repeat_within_cooldown(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")

    first = run_scheduler_once(tmp_path, cooldown_seconds=3600)
    second = run_scheduler_once(tmp_path, cooldown_seconds=3600)

    assert first["active_todo_count"] == 1
    assert second["todo_count"] == 1
    assert second["active_todo_count"] == 0
    assert second["suppressed_todo_count"] == 1
    assert get_todo_state_path(tmp_path).exists()


def test_run_scheduler_once_emits_again_on_severity_escalation(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="WARNING", message="thumbnail failed")
    first = run_scheduler_once(tmp_path, cooldown_seconds=3600)
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="CRITICAL", message="thumbnail failed harder")

    second = run_scheduler_once(tmp_path, cooldown_seconds=3600)

    assert first["active_todo_count"] == 1
    assert second["active_todo_count"] == 1
    assert second["top_todo"]["severity"] == "CRITICAL"


def test_run_scheduler_once_handles_invalid_todo_state_file(tmp_path):
    record_issue(tmp_path, source="hometools.test", severity="ERROR", message="boom")
    path = get_todo_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")

    result = run_scheduler_once(tmp_path, cooldown_seconds=3600)

    assert result["status"] == "ok"
    assert result["active_todo_count"] == 1


def test_acknowledge_todo_suppresses_active_summary(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    todo_key = generate_todo_candidates(tmp_path)["items"][0]["todo_key"]

    result = acknowledge_todo(tmp_path, todo_key, reason="known flake")
    summary = summarize_todos(tmp_path)

    assert result["ok"] is True
    assert summary["active_count"] == 0
    assert summary["acknowledged_count"] == 1


def test_snooze_todo_marks_summary_until_expiry(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    todo_key = generate_todo_candidates(tmp_path)["items"][0]["todo_key"]

    result = snooze_todo(tmp_path, todo_key, seconds=600, reason="later")
    summary = summarize_todos(tmp_path)

    assert result["ok"] is True
    assert result["snoozed_until"] is not None
    assert summary["active_count"] == 0
    assert summary["snoozed_count"] == 1


def test_clear_todo_state_reactivates_summary(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    todo_key = generate_todo_candidates(tmp_path)["items"][0]["todo_key"]
    acknowledge_todo(tmp_path, todo_key)

    cleared = clear_todo_state(tmp_path, todo_key)
    summary = summarize_todos(tmp_path)

    assert cleared["ok"] is True
    assert summary["active_count"] == 1
    assert summary["acknowledged_count"] == 0


def test_summarize_issue_and_todos_returns_both_sections(tmp_path):
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")

    result = summarize_issue_and_todos(tmp_path)

    assert result["issues"]["count"] == 1
    assert result["todos"]["count"] == 1
    assert result["todos"]["active_count"] == 1


def test_stream_todos_returns_nonzero_when_candidates_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.test", severity="ERROR", message="boom")

    rc = run_stream_todos(
        Namespace(
            json=True,
            min_severity="warning",
            only_errors=True,
            max_items=None,
            fail_on_match=True,
        )
    )

    assert rc == 1


def test_stream_scheduler_returns_nonzero_when_todos_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.test", severity="ERROR", message="boom")

    rc = run_stream_scheduler(
        Namespace(
            json=True,
            min_severity="warning",
            only_errors=True,
            max_items=None,
            cooldown_seconds=3600,
            fail_on_match=True,
        )
    )

    assert rc == 1


def test_stream_scheduler_returns_zero_when_only_suppressed_todos_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.test", severity="ERROR", message="boom")
    run_scheduler_once(tmp_path, cooldown_seconds=3600)

    rc = run_stream_scheduler(
        Namespace(
            json=True,
            min_severity="warning",
            only_errors=True,
            max_items=None,
            cooldown_seconds=3600,
            fail_on_match=True,
        )
    )

    assert rc == 0


def test_stream_todo_state_acknowledges_existing_todo(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    todo_key = generate_todo_candidates(tmp_path)["items"][0]["todo_key"]

    rc = run_stream_todo_state(
        Namespace(
            todo_key=todo_key,
            action="acknowledge",
            reason="known",
            seconds=3600,
            min_severity="warning",
            only_errors=False,
            json=True,
        )
    )

    assert rc == 0
    assert summarize_todos(tmp_path)["acknowledged_count"] == 1


def test_stream_todo_state_clear_reactivates_todo(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMETOOLS_CACHE_DIR", str(tmp_path))
    record_issue(tmp_path, source="hometools.streaming.core.thumbnailer", severity="ERROR", message="thumbnail failed")
    todo_key = generate_todo_candidates(tmp_path)["items"][0]["todo_key"]
    acknowledge_todo(tmp_path, todo_key)

    rc = run_stream_todo_state(
        Namespace(
            todo_key=todo_key,
            action="clear",
            reason="",
            seconds=3600,
            min_severity="warning",
            only_errors=False,
            json=True,
        )
    )

    assert rc == 0
    assert summarize_todos(tmp_path)["active_count"] == 1
