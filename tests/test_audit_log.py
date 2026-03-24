"""Tests for the shared audit/change-log module and related server endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest

from hometools.streaming.core.audit_log import (
    append_entry,
    get_entry,
    load_entries,
    log_rating_write,
    mark_undone,
    new_entry,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_cache(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# new_entry / AuditEntry
# ---------------------------------------------------------------------------


def test_new_entry_has_uuid(tmp_cache):
    e = new_entry(
        action="rating_write",
        server="audio",
        path="a.mp3",
        field="rating",
        old_value=2.0,
        new_value=4.0,
        undo_payload={"path": "a.mp3", "rating": 2.0, "raw": 102},
    )
    assert len(e.entry_id) == 36  # UUID format
    assert "-" in e.entry_id


def test_new_entry_timestamp_is_utc(tmp_cache):
    e = new_entry(action="rating_write", server="audio", path="a.mp3", field="rating", old_value=0.0, new_value=3.0, undo_payload={})
    assert "T" in e.timestamp
    assert "+" in e.timestamp or e.timestamp.endswith("Z") or "+00:00" in e.timestamp


def test_new_entry_is_frozen(tmp_cache):
    import dataclasses

    e = new_entry(action="rating_write", server="audio", path="a.mp3", field="rating", old_value=0.0, new_value=3.0, undo_payload={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.path = "other.mp3"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# append_entry / load_entries round-trip
# ---------------------------------------------------------------------------


def test_append_and_load_single_entry(tmp_cache):
    e = new_entry(
        action="rating_write",
        server="audio",
        path="Artist/Song.mp3",
        field="rating",
        old_value=0.0,
        new_value=5.0,
        undo_payload={"path": "Artist/Song.mp3", "rating": 0.0, "raw": 0},
    )
    append_entry(tmp_cache, e)
    entries = load_entries(tmp_cache)
    assert len(entries) == 1
    assert entries[0]["entry_id"] == e.entry_id
    assert entries[0]["action"] == "rating_write"
    assert entries[0]["new_value"] == 5.0


def test_load_entries_newest_first(tmp_cache):
    for i in range(3):
        e = new_entry(
            action="rating_write",
            server="audio",
            path=f"track{i}.mp3",
            field="rating",
            old_value=float(i),
            new_value=float(i + 1),
            undo_payload={},
        )
        append_entry(tmp_cache, e)
    entries = load_entries(tmp_cache)
    # newest appended last → reversed → first in result
    assert entries[0]["path"] == "track2.mp3"
    assert entries[-1]["path"] == "track0.mp3"


def test_load_entries_limit(tmp_cache):
    for i in range(5):
        e = new_entry(
            action="rating_write", server="audio", path=f"t{i}.mp3", field="rating", old_value=0.0, new_value=1.0, undo_payload={}
        )
        append_entry(tmp_cache, e)
    entries = load_entries(tmp_cache, limit=2)
    assert len(entries) == 2


def test_load_entries_path_filter(tmp_cache):
    for name in ("alpha.mp3", "beta.mp3", "gamma-alpha.mp3"):
        e = new_entry(action="rating_write", server="audio", path=name, field="rating", old_value=0.0, new_value=1.0, undo_payload={})
        append_entry(tmp_cache, e)
    results = load_entries(tmp_cache, path_filter="alpha")
    assert len(results) == 2
    assert all("alpha" in r["path"] for r in results)


def test_load_entries_action_filter(tmp_cache):
    e1 = new_entry(action="rating_write", server="audio", path="a.mp3", field="rating", old_value=0.0, new_value=1.0, undo_payload={})
    e2 = new_entry(action="tag_write", server="audio", path="b.mp3", field="title", old_value="Old", new_value="New", undo_payload={})
    append_entry(tmp_cache, e1)
    append_entry(tmp_cache, e2)
    rating_entries = load_entries(tmp_cache, action_filter="rating_write")
    assert len(rating_entries) == 1
    assert rating_entries[0]["action"] == "rating_write"


def test_load_entries_empty_cache(tmp_cache):
    entries = load_entries(tmp_cache)
    assert entries == []


def test_load_entries_exclude_undone(tmp_cache):
    e = new_entry(
        action="rating_write",
        server="audio",
        path="song.mp3",
        field="rating",
        old_value=3.0,
        new_value=5.0,
        undo_payload={"path": "song.mp3", "rating": 3.0, "raw": 153},
    )
    append_entry(tmp_cache, e)
    mark_undone(tmp_cache, e.entry_id)
    active = load_entries(tmp_cache, include_undone=False)
    assert active == []
    all_entries = load_entries(tmp_cache, include_undone=True)
    assert len(all_entries) == 1


# ---------------------------------------------------------------------------
# get_entry
# ---------------------------------------------------------------------------


def test_get_entry_found(tmp_cache):
    e = new_entry(action="rating_write", server="audio", path="find_me.mp3", field="rating", old_value=1.0, new_value=4.0, undo_payload={})
    append_entry(tmp_cache, e)
    found = get_entry(tmp_cache, e.entry_id)
    assert found is not None
    assert found["path"] == "find_me.mp3"


def test_get_entry_not_found(tmp_cache):
    result = get_entry(tmp_cache, "nonexistent-uuid")
    assert result is None


# ---------------------------------------------------------------------------
# mark_undone
# ---------------------------------------------------------------------------


def test_mark_undone_sets_flag(tmp_cache):
    e = new_entry(action="rating_write", server="audio", path="undo_me.mp3", field="rating", old_value=2.0, new_value=5.0, undo_payload={})
    append_entry(tmp_cache, e)
    result = mark_undone(tmp_cache, e.entry_id)
    assert result is True
    found = get_entry(tmp_cache, e.entry_id)
    assert found["undone"] is True
    assert found["undone_at"] != ""


def test_mark_undone_preserves_other_entries(tmp_cache):
    e1 = new_entry(action="rating_write", server="audio", path="keep.mp3", field="rating", old_value=1.0, new_value=2.0, undo_payload={})
    e2 = new_entry(action="rating_write", server="audio", path="undo.mp3", field="rating", old_value=3.0, new_value=4.0, undo_payload={})
    append_entry(tmp_cache, e1)
    append_entry(tmp_cache, e2)
    mark_undone(tmp_cache, e2.entry_id)
    kept = get_entry(tmp_cache, e1.entry_id)
    assert kept is not None
    assert kept.get("undone") is False


def test_mark_undone_returns_false_for_missing(tmp_cache):
    result = mark_undone(tmp_cache, "no-such-id")
    assert result is False


# ---------------------------------------------------------------------------
# log_rating_write helper
# ---------------------------------------------------------------------------


def test_log_rating_write_appends_entry(tmp_cache):
    entry = log_rating_write(
        tmp_cache,
        server="audio",
        path="Folder/Track.mp3",
        old_stars=2.0,
        new_stars=4.0,
        old_raw=102,
        new_raw=204,
    )
    assert entry.action == "rating_write"
    assert entry.field == "rating"
    assert entry.old_value == 2.0
    assert entry.new_value == 4.0
    assert entry.server == "audio"
    entries = load_entries(tmp_cache)
    assert len(entries) == 1
    assert entries[0]["entry_id"] == entry.entry_id


def test_log_rating_write_undo_payload_contains_old_values(tmp_cache):
    entry = log_rating_write(
        tmp_cache,
        server="audio",
        path="Track.mp3",
        old_stars=3.0,
        new_stars=5.0,
        old_raw=153,
        new_raw=255,
    )
    assert entry.undo_payload["rating"] == 3.0
    assert entry.undo_payload["raw"] == 153
    assert entry.undo_payload["path"] == "Track.mp3"
    assert entry.undo_payload["entry_id"] == entry.entry_id


# ---------------------------------------------------------------------------
# Server endpoints — audio
# ---------------------------------------------------------------------------


def test_audio_audit_endpoint_exists():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.get("/api/audio/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_audio_audit_undo_endpoint_missing_id():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.post("/api/audio/audit/undo", json={})
    assert resp.status_code == 400


def test_audio_audit_undo_endpoint_not_found():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.post("/api/audio/audit/undo", json={"entry_id": "no-such-id"})
    assert resp.status_code == 404


def test_audio_audit_panel_route():
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.get("/audit")
    assert resp.status_code == 200
    assert "Audit-Log" in resp.text
    assert "hometools audio" in resp.text


def test_audio_rating_returns_entry_id():
    """POST /api/audio/rating for non-existent file returns 404 (not 500/200)."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    resp = client.post("/api/audio/rating", json={"path": "ghost.mp3", "rating": 4.0})
    # File not found → 404 (entry_id would be in 200 response for existing file)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Server endpoints — video
# ---------------------------------------------------------------------------


def test_video_audit_endpoint_exists():
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    resp = client.get("/api/video/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_video_audit_undo_returns_422():
    """Video server has no write ops, so undo must return 422."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    resp = client.post("/api/video/audit/undo", json={"entry_id": "any"})
    assert resp.status_code == 422


def test_video_audit_panel_route():
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    resp = client.get("/audit")
    assert resp.status_code == 200
    assert "Audit-Log" in resp.text
    assert "hometools video" in resp.text


# ---------------------------------------------------------------------------
# Control panel HTML
# ---------------------------------------------------------------------------


def test_render_audit_panel_has_filter_form():
    from hometools.streaming.core.server_utils import render_audit_panel_html

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert 'id="f-form"' in html
    assert 'id="f-path"' in html
    assert 'id="f-action"' in html


def test_render_audit_panel_has_table():
    from hometools.streaming.core.server_utils import render_audit_panel_html

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert 'id="log-table"' in html
    assert "<thead>" in html


def test_render_audit_panel_has_media_type_js():
    from hometools.streaming.core.server_utils import render_audit_panel_html

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert "MEDIA_TYPE = 'audio'" in html


def test_render_audit_panel_has_undo_js():
    from hometools.streaming.core.server_utils import render_audit_panel_html

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert "doUndo" in html
    assert "/api/audio/audit/undo" not in html  # URL is built dynamically in JS
    assert "MEDIA_TYPE" in html


def test_render_audit_panel_has_back_link():
    from hometools.streaming.core.server_utils import render_audit_panel_html

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert 'href="/"' in html


# ---------------------------------------------------------------------------
# JS undo in player app
# ---------------------------------------------------------------------------


def test_player_js_has_undo_rating_function():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "undoRating" in js
    assert "showRatingToastWithUndo" in js
    assert "AUDIT_UNDO_PATH" in js


def test_player_js_audit_undo_path_injected():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "AUDIT_UNDO_PATH = '/api/audio/audit/undo'" in js


def test_player_js_rating_toast_uses_entry_id():
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "entry_id" in js
    assert "showRatingToastWithUndo" in js
