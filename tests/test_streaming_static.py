"""Tests for the Vite/TS webui static asset bridge (server_utils/_static.py).

Vite/TS migration Phase 4 (docs/IMPLEMENTATION_PLAN.md): FastAPI StaticFiles
mount for the built player UI bundle. Every scenario here mirrors the
module's core promise — never crash, never block — for both the "bundle
built" and "bundle missing" cases.
"""

from __future__ import annotations

import json

import pytest

from hometools.streaming.core.server_utils import _static


@pytest.fixture(autouse=True)
def _reset_static_module_state(monkeypatch):
    """Every test gets a clean slate for the module-level caches."""
    monkeypatch.setattr(_static, "_manifest_cache", None)
    monkeypatch.setattr(_static, "_warned_missing", False)
    yield


def test_get_static_script_tag_empty_when_static_dir_missing(tmp_path, monkeypatch):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(_static, "STATIC_DIR", missing_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", missing_dir / ".vite" / "manifest.json")
    assert _static.get_static_script_tag() == ""


def test_get_static_script_tag_empty_when_manifest_malformed(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    (static_dir / ".vite" / "manifest.json").write_text("not json", encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")
    assert _static.get_static_script_tag() == ""


def test_get_static_script_tag_returns_script_src_from_manifest(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {"src/main.ts": {"file": "player.ABCDEF.js", "name": "main", "src": "src/main.ts", "isEntry": True}}
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")
    tag = _static.get_static_script_tag()
    assert tag == '<script src="/static/player.ABCDEF.js"></script>'


def test_get_static_script_tag_empty_when_entry_key_absent(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {"some/other.ts": {"file": "other.js"}}
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")
    assert _static.get_static_script_tag() == ""


def test_manifest_is_cached_after_first_read(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest_path = static_dir / ".vite" / "manifest.json"
    manifest = {"src/main.ts": {"file": "player.CACHED.js"}}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", manifest_path)

    first = _static.get_static_script_tag()
    manifest_path.unlink()  # prove the second call uses the cache, not disk
    second = _static.get_static_script_tag()
    assert first == second == '<script src="/static/player.CACHED.js"></script>'


def test_mount_static_assets_returns_false_and_logs_when_dir_missing(tmp_path, monkeypatch, caplog):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(_static, "STATIC_DIR", missing_dir)

    class _FakeApp:
        def mount(self, *args, **kwargs):  # pragma: no cover - must never be called
            raise AssertionError("mount() should not be called when static dir is missing")

    with caplog.at_level("WARNING"):
        result = _static.mount_static_assets(_FakeApp())
    assert result is False
    assert any("Static webui bundle not found" in rec.message for rec in caplog.records)


def test_mount_static_assets_warns_only_once(tmp_path, monkeypatch, caplog):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(_static, "STATIC_DIR", missing_dir)

    class _FakeApp:
        def mount(self, *args, **kwargs):
            raise AssertionError

    with caplog.at_level("WARNING"):
        _static.mount_static_assets(_FakeApp())
        _static.mount_static_assets(_FakeApp())
    warnings = [rec for rec in caplog.records if "Static webui bundle not found" in rec.message]
    assert len(warnings) == 1


def test_mount_static_assets_mounts_real_fastapi_app(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "player.TEST.js").write_text("window.fmtTime = function(){};", encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)

    app = FastAPI()
    assert _static.mount_static_assets(app) is True

    client = TestClient(app)
    resp = client.get("/static/player.TEST.js")
    assert resp.status_code == 200
    assert "fmtTime" in resp.text


def test_render_media_page_omits_static_tag_when_bundle_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_static, "STATIC_DIR", tmp_path / "does-not-exist")
    monkeypatch.setattr(_static, "_MANIFEST_PATH", tmp_path / "does-not-exist" / ".vite" / "manifest.json")

    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="t",
        emoji="x",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
    )
    assert '<script src="/static/' not in page


def test_render_media_page_includes_static_tag_when_bundle_built(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {"src/main.ts": {"file": "player.XYZ.js"}}
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")

    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="t",
        emoji="x",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
    )
    assert '<script src="/static/player.XYZ.js"></script>' in page
    # Must appear before the inline legacy <script>{js}</script> tag so the
    # bridged window.fmtTime/escHtml/formatBytes are defined in time.
    assert page.index('<script src="/static/player.XYZ.js">') < page.rindex("<script>")


def test_get_static_css_tags_reads_top_level_style_entry(tmp_path, monkeypatch):
    """cssCodeSplit: false puts the extracted stylesheet in its own
    top-level "style.css" manifest entry, not under the JS entry."""
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {
        "src/main.ts": {"file": "player.ABC.js", "isEntry": True},
        "style.css": {"file": "player.DEF.css", "src": "style.css"},
    }
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")
    assert _static.get_static_css_tags() == '<link rel="stylesheet" href="/static/player.DEF.css">'


def test_get_static_css_tags_reads_entry_css_list(tmp_path, monkeypatch):
    """With code splitting on, Vite lists CSS under the entry's "css" key —
    both shapes must work so a build-option change can't silently drop the
    stylesheet."""
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {"src/main.ts": {"file": "player.ABC.js", "css": ["player.GHI.css"]}}
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")
    assert _static.get_static_css_tags() == '<link rel="stylesheet" href="/static/player.GHI.css">'


def test_get_static_css_tags_empty_when_bundle_missing(tmp_path, monkeypatch):
    missing = tmp_path / "nope"
    monkeypatch.setattr(_static, "STATIC_DIR", missing)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", missing / ".vite" / "manifest.json")
    assert _static.get_static_css_tags() == ""


def test_render_media_page_links_ported_css_after_inline_style(tmp_path, monkeypatch):
    """Ported CSS must be linked AFTER the inline <style> — at equal
    specificity the later rule wins, so a ported rule always beats a stale
    legacy duplicate during the migration."""
    static_dir = tmp_path / "static"
    (static_dir / ".vite").mkdir(parents=True)
    manifest = {
        "src/main.ts": {"file": "player.XYZ.js"},
        "style.css": {"file": "player.STY.css"},
    }
    (static_dir / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(_static, "STATIC_DIR", static_dir)
    monkeypatch.setattr(_static, "_MANIFEST_PATH", static_dir / ".vite" / "manifest.json")

    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="t",
        emoji="x",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
    )
    assert '<link rel="stylesheet" href="/static/player.STY.css">' in page
    assert page.index("<style>") < page.index('<link rel="stylesheet" href="/static/player.STY.css">')


def test_meta_pill_css_ported_out_of_python():
    """The meta-pill rules moved to webui/src/styles/metaPill.css. Keeping a
    Python copy would silently shadow/duplicate them — render_base_css()
    must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".meta-pill {" not in css
    assert ".bpm-adjust-menu" not in css

    ported = (
        Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "metaPill.css"
    )
    text = ported.read_text(encoding="utf-8")
    assert ".meta-pill {" in text
    assert ".bpm-adjust-menu" in text
