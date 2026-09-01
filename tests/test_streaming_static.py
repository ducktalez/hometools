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


def test_root_css_ported_out_of_python():
    """The root/header rules moved to webui/src/styles/root.css. Keeping a
    Python copy would silently shadow/duplicate them — render_base_css()
    must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ":root {" not in css
    assert "\nheader {" not in css
    assert ".logo-home-btn" not in css

    ported = Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "root.css"
    text = ported.read_text(encoding="utf-8")
    assert ":root {" in text
    assert "header {" in text
    assert ".logo-home-btn" in text


def test_tools_panel_css_ported_out_of_python():
    """The tools-pill/panel rules moved to webui/src/styles/toolsPanel.css.
    Keeping a Python copy would silently shadow/duplicate them —
    render_base_css() must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".tools-pill-wrap" not in css
    assert ".tools-panel {" not in css
    assert ".tools-activate-all" not in css

    ported = (
        Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "toolsPanel.css"
    )
    text = ported.read_text(encoding="utf-8")
    assert ".tools-pill-wrap" in text
    assert ".tools-panel {" in text
    assert ".tools-activate-all" in text


def test_modals_css_ported_out_of_python():
    """The edit/playlist modal rules moved to webui/src/styles/modals.css.
    Keeping a Python copy would silently shadow/duplicate them —
    render_base_css() must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".edit-modal {" not in css
    assert ".playlist-modal {" not in css
    assert ".playlist-drag-ghost {" not in css

    ported = Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "modals.css"
    text = ported.read_text(encoding="utf-8")
    assert ".edit-modal {" in text
    assert ".playlist-modal {" in text
    assert ".playlist-drag-ghost {" in text


def test_playlist_cards_css_ported_out_of_python():
    """The playlist pseudo-folder card / smart-editor rules moved to
    webui/src/styles/playlistCards.css. Keeping a Python copy would silently
    shadow/duplicate them — render_base_css() must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".playlist-folder-card {" not in css
    assert ".smart-editor-modal {" not in css
    assert ".playlist-cover-play-btn {" not in css

    ported = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "hometools"
        / "streaming"
        / "core"
        / "webui"
        / "src"
        / "styles"
        / "playlistCards.css"
    )
    text = ported.read_text(encoding="utf-8")
    assert ".playlist-folder-card {" in text
    assert ".smart-editor-modal {" in text
    assert ".playlist-cover-play-btn {" in text


def test_player_bar_css_ported_out_of_python():
    """The bottom player-bar rules (classic + waveform layouts, transport
    controls) moved to webui/src/styles/playerBar.css. Keeping a Python copy
    would silently shadow/duplicate them — render_base_css() must no longer
    emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".player-bar-move-select {" not in css
    assert ".ctrl-btn.play-pause {" not in css
    assert ".player-bar.waveform {" not in css

    ported = (
        Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "playerBar.css"
    )
    text = ported.read_text(encoding="utf-8")
    assert ".player-bar-move-select {" in text
    assert ".ctrl-btn.play-pause {" in text
    assert ".player-bar.waveform {" in text


def test_table_view_css_ported_out_of_python():
    """The track detail/table view + kebab-menu/path-modal rules moved to
    webui/src/styles/tableView.css. Keeping a Python copy would silently
    shadow/duplicate them — render_base_css() must no longer emit them."""
    from pathlib import Path

    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert ".track-table-header {" not in css
    assert ".ht-ctx-menu {" not in css
    assert ".path-modal-overlay {" not in css

    ported = (
        Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "styles" / "tableView.css"
    )
    text = ported.read_text(encoding="utf-8")
    assert ".track-table-header {" in text
    assert ".ht-ctx-menu {" in text
    assert ".path-modal-overlay {" in text
