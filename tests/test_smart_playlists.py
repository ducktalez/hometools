"""Tests for smart playlists (rule evaluation, storage, API)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hometools.streaming.core.playlists import (
    add_item,
    create_playlist,
    get_playlist,
    load_playlists,
    update_smart_rules,
)
from hometools.streaming.core.smart_playlists import (
    evaluate_smart,
    is_smart,
    validate_smart_rules,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mk(rp: str, **kw) -> dict:
    """Build a MediaItem-shaped dict with sensible defaults."""
    base = {
        "relative_path": rp,
        "title": rp.rsplit("/", 1)[-1],
        "artist": "",
        "stream_url": "",
        "media_type": "audio",
        "rating": 0.0,
        "genre": "",
        "language": "",
        "duration": 0.0,
        "mtime": 0.0,
    }
    base.update(kw)
    return base


@pytest.fixture
def library() -> list[dict]:
    now = time.time()
    return [
        _mk("Rock/Queen - We Will Rock You.mp3", artist="Queen", genre="Rock", rating=5, mtime=now - 10 * 86400),
        _mk("Rock/AC-DC - TNT.mp3", artist="AC-DC", genre="Rock", rating=4, mtime=now - 200 * 86400),
        _mk("Pop/Abba - Mamma Mia.mp3", artist="Abba", genre="Pop", rating=3, mtime=now - 30 * 86400),
        _mk("Pop/New Track.mp3", artist="New", genre="Pop", rating=0, mtime=now - 5 * 86400),
        _mk("Jazz/Cool.mp3", artist="Miles", genre="Jazz", rating=4, mtime=now - 400 * 86400),
    ]


# ---------------------------------------------------------------------------
# is_smart
# ---------------------------------------------------------------------------


class TestIsSmart:
    def test_regular_playlist_is_not_smart(self):
        assert is_smart({"id": "x", "items": []}) is False

    def test_smart_playlist_is_smart(self):
        assert is_smart({"id": "x", "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}}) is True

    def test_none_is_not_smart(self):
        assert is_smart(None) is False

    def test_empty_smart_block_without_rules_is_not_smart(self):
        assert is_smart({"id": "x", "smart": {}}) is False


# ---------------------------------------------------------------------------
# Operator coverage
# ---------------------------------------------------------------------------


class TestRuleEvaluation:
    def test_rating_gte(self, library):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}
        out = evaluate_smart(smart, library)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Rock/AC-DC - TNT.mp3",
                "Jazz/Cool.mp3",
            ]
        )

    def test_rating_between(self, library):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "between", "value": [3, 4]}]}
        out = evaluate_smart(smart, library)
        assert "Pop/Abba - Mamma Mia.mp3" in out
        assert "Rock/AC-DC - TNT.mp3" in out
        assert "Rock/Queen - We Will Rock You.mp3" not in out

    def test_genre_contains_case_insensitive(self, library):
        smart = {"match": "all", "rules": [{"field": "genre", "op": "contains", "value": "ROC"}]}
        out = evaluate_smart(smart, library)
        assert all(rp.startswith("Rock/") for rp in out)
        assert len(out) == 2

    def test_genre_eq_exact(self, library):
        smart = {"match": "all", "rules": [{"field": "genre", "op": "eq", "value": "Pop"}]}
        out = evaluate_smart(smart, library)
        assert all(rp.startswith("Pop/") for rp in out)

    def test_regex_matches(self, library):
        smart = {"match": "all", "rules": [{"field": "title", "op": "matches", "value": "(We Will|TNT)"}]}
        out = evaluate_smart(smart, library)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Rock/AC-DC - TNT.mp3",
            ]
        )

    def test_invalid_regex_matches_nothing(self, library):
        smart = {"match": "all", "rules": [{"field": "title", "op": "matches", "value": "([invalid"}]}
        out = evaluate_smart(smart, library)
        assert out == []

    def test_added_at_within_days(self, library):
        smart = {"match": "all", "rules": [{"field": "added_at", "op": "within_days", "value": 60}]}
        out = evaluate_smart(smart, library)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Pop/Abba - Mamma Mia.mp3",
                "Pop/New Track.mp3",
            ]
        )

    def test_in_op(self, library):
        smart = {"match": "all", "rules": [{"field": "language", "op": "in", "value": ["de", "en"]}]}
        # all empty -> none
        assert evaluate_smart(smart, library) == []

    def test_starts_with(self, library):
        smart = {"match": "all", "rules": [{"field": "relative_path", "op": "starts_with", "value": "Rock/"}]}
        out = evaluate_smart(smart, library)
        assert len(out) == 2

    def test_unknown_op_excludes_item(self, library):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "wat", "value": 4}]}
        assert evaluate_smart(smart, library) == []


# ---------------------------------------------------------------------------
# AND / OR
# ---------------------------------------------------------------------------


class TestMatchModes:
    def test_match_all(self, library):
        smart = {
            "match": "all",
            "rules": [
                {"field": "genre", "op": "eq", "value": "Rock"},
                {"field": "rating", "op": "gte", "value": 5},
            ],
        }
        out = evaluate_smart(smart, library)
        assert out == ["Rock/Queen - We Will Rock You.mp3"]

    def test_match_any(self, library):
        smart = {
            "match": "any",
            "rules": [
                {"field": "genre", "op": "eq", "value": "Jazz"},
                {"field": "rating", "op": "gte", "value": 5},
            ],
        }
        out = evaluate_smart(smart, library)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Jazz/Cool.mp3",
            ]
        )


# ---------------------------------------------------------------------------
# in_playlist
# ---------------------------------------------------------------------------


class TestInPlaylist:
    def test_any_of(self, library):
        playlists = [
            {"id": "p1", "name": "Rock", "items": ["Rock/Queen - We Will Rock You.mp3"]},
            {"id": "p2", "name": "Rock-Alt", "items": ["Rock/AC-DC - TNT.mp3"]},
        ]
        smart = {
            "match": "all",
            "rules": [
                {"field": "in_playlist", "op": "any_of", "value": ["p1", "p2"]},
            ],
        }
        out = evaluate_smart(smart, library, all_playlists=playlists)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Rock/AC-DC - TNT.mp3",
            ]
        )

    def test_best_of_rock_combined(self, library):
        """Real-world: in Rock-Playlists AND rating >= 4."""
        playlists = [
            {
                "id": "p1",
                "name": "Rock",
                "items": [
                    "Rock/Queen - We Will Rock You.mp3",
                    "Rock/AC-DC - TNT.mp3",
                    "Pop/Abba - Mamma Mia.mp3",
                ],
            },
        ]
        smart = {
            "match": "all",
            "rules": [
                {"field": "in_playlist", "op": "any_of", "value": ["p1"]},
                {"field": "rating", "op": "gte", "value": 4},
            ],
        }
        out = evaluate_smart(smart, library, all_playlists=playlists)
        assert sorted(out) == sorted(
            [
                "Rock/Queen - We Will Rock You.mp3",
                "Rock/AC-DC - TNT.mp3",
            ]
        )

    def test_none_of(self, library):
        playlists = [{"id": "p1", "items": ["Rock/Queen - We Will Rock You.mp3"]}]
        smart = {
            "match": "all",
            "rules": [
                {"field": "in_playlist", "op": "none_of", "value": ["p1"]},
            ],
        }
        out = evaluate_smart(smart, library, all_playlists=playlists)
        assert "Rock/Queen - We Will Rock You.mp3" not in out
        assert len(out) == 4

    def test_smart_playlists_are_skipped_when_referenced(self, library):
        """Phase 1: smart playlists referenced via in_playlist resolve to empty."""
        playlists = [
            {"id": "smart1", "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}},
        ]
        smart = {
            "match": "all",
            "rules": [
                {"field": "in_playlist", "op": "any_of", "value": ["smart1"]},
            ],
        }
        out = evaluate_smart(smart, library, all_playlists=playlists)
        assert out == []


# ---------------------------------------------------------------------------
# Sort + limit
# ---------------------------------------------------------------------------


class TestSortAndLimit:
    def test_sort_rating_desc(self, library):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 3}], "sort": "rating_desc"}
        out = evaluate_smart(smart, library)
        # First should be rating-5 track
        assert out[0] == "Rock/Queen - We Will Rock You.mp3"

    def test_limit(self, library):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 0}], "limit": 2}
        out = evaluate_smart(smart, library)
        assert len(out) == 2


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_valid(self):
        ok, _ = validate_smart_rules({"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]})
        assert ok

    def test_missing_rules(self):
        ok, _ = validate_smart_rules({"match": "all", "rules": []})
        assert not ok

    def test_bad_match(self):
        ok, _ = validate_smart_rules({"match": "maybe", "rules": [{"field": "rating", "op": "gte", "value": 4}]})
        assert not ok

    def test_missing_field(self):
        ok, _ = validate_smart_rules({"match": "all", "rules": [{"op": "gte", "value": 4}]})
        assert not ok


# ---------------------------------------------------------------------------
# Storage integration
# ---------------------------------------------------------------------------


class TestStorage:
    def test_create_smart_playlist_persists(self, tmp_path: Path):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}
        pl = create_playlist(tmp_path, "audio", name="Top Rated", smart=smart)
        assert "smart" in pl
        # Reload from disk
        loaded = load_playlists(tmp_path, "audio")
        assert len(loaded) == 1
        assert loaded[0]["smart"]["rules"][0]["field"] == "rating"

    def test_add_item_on_smart_is_noop(self, tmp_path: Path):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}
        pl = create_playlist(tmp_path, "audio", name="Top", smart=smart)
        # Try to add — should be silently ignored, items stays empty
        result = add_item(tmp_path, "audio", pl["id"], relative_path="foo.mp3")
        assert result is not None
        assert result["items"] == []
        loaded = get_playlist(tmp_path, "audio", pl["id"])
        assert loaded["items"] == []

    def test_update_smart_rules_promotes_regular_playlist(self, tmp_path: Path):
        pl = create_playlist(tmp_path, "audio", name="Manual")
        assert "smart" not in pl
        new_smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}
        updated = update_smart_rules(tmp_path, "audio", pl["id"], smart=new_smart)
        assert updated is not None
        assert updated["smart"] == new_smart
        assert updated["items"] == []  # smart playlists never persist items

    def test_update_smart_rules_missing_playlist(self, tmp_path: Path):
        smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}
        assert update_smart_rules(tmp_path, "audio", "nope", smart=smart) is None


# ---------------------------------------------------------------------------
# API endpoints (audio + video)
# ---------------------------------------------------------------------------


@pytest.fixture
def audio_client(tmp_path: Path):
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    app = create_app(library_dir=tmp_path, safe_mode=True, cache_dir=tmp_path)
    return TestClient(app)


@pytest.fixture
def video_client(tmp_path: Path):
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    app = create_app(library_dir=tmp_path, safe_mode=True, cache_dir=tmp_path)
    return TestClient(app)


class TestApiAudio:
    def test_create_smart(self, audio_client):
        payload = {
            "name": "Top",
            "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]},
        }
        r = audio_client.post("/api/audio/playlists/smart", json=payload)
        assert r.status_code == 200
        pl = r.json()["playlist"]
        assert "smart" in pl
        # Show up in GET
        r2 = audio_client.get("/api/audio/playlists")
        assert any(p.get("smart") for p in r2.json()["items"])

    def test_create_smart_rejects_invalid(self, audio_client):
        r = audio_client.post(
            "/api/audio/playlists/smart",
            json={"name": "X", "smart": {"match": "x", "rules": []}},
        )
        assert r.status_code == 400

    def test_create_smart_requires_name(self, audio_client):
        r = audio_client.post(
            "/api/audio/playlists/smart",
            json={"name": "", "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}},
        )
        assert r.status_code == 400

    def test_update_smart_rules(self, audio_client):
        r = audio_client.post("/api/audio/playlists", json={"name": "Regular"})
        pl = r.json()["playlist"]
        new_smart = {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 5}]}
        r2 = audio_client.put(
            "/api/audio/playlists/smart",
            json={"playlist_id": pl["id"], "smart": new_smart},
        )
        assert r2.status_code == 200
        assert r2.json()["playlist"]["smart"]["rules"][0]["value"] == 5

    def test_update_smart_404(self, audio_client):
        r = audio_client.put(
            "/api/audio/playlists/smart",
            json={"playlist_id": "nope", "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]}},
        )
        assert r.status_code == 404


class TestApiVideo:
    def test_create_smart(self, video_client):
        payload = {
            "name": "Top",
            "smart": {"match": "all", "rules": [{"field": "rating", "op": "gte", "value": 4}]},
        }
        r = video_client.post("/api/video/playlists/smart", json=payload)
        assert r.status_code == 200
        assert "smart" in r.json()["playlist"]


# ---------------------------------------------------------------------------
# JS injection (badge + evaluator present in rendered JS)
# ---------------------------------------------------------------------------


def _js() -> str:
    from hometools.streaming.core.server_utils import render_player_js

    return render_player_js(api_path="/api/audio/items", enable_playlists=True)


class TestJsInjection:
    def test_evaluator_present(self):
        js = _js()
        assert "_evaluateSmartPlaylist" in js
        assert "_smartEvalRule" in js

    def test_editor_modal_helpers_present(self):
        js = _js()
        assert "openSmartPlaylistEditor" in js
        assert "PLAYLISTS_SMART_PATH" in js

    def test_smart_badge_class_present(self):
        js = _js()
        assert "smart-pl-badge" in js
        assert "IC_SMART_PLAYLIST" in js

    def test_refresh_button_handler_present(self):
        js = _js()
        assert "refreshSmartPlaylist" in js
