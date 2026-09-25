"""Tests for the webui bundle build helper (`streaming/webui_build.py`).

The staleness check is what makes `hometools build-webui` cheap enough to
wire in as a PyCharm before-launch task, so it needs to be correct in both
directions: never skip a needed rebuild, never rebuild without reason.
"""

from __future__ import annotations

import os

from hometools.streaming.webui_build import build_webui, is_bundle_stale


def _make_webui(tmp_path, *, source_mtime: float):
    """Create a minimal webui source tree with a fixed mtime."""
    webui = tmp_path / "webui"
    (webui / "src").mkdir(parents=True)
    (webui / "package.json").write_text("{}", encoding="utf-8")
    (webui / "src" / "main.ts").write_text("export {};", encoding="utf-8")
    for rel in ("package.json", "src/main.ts"):
        os.utime(webui / rel, (source_mtime, source_mtime))
    return webui


def _make_static(tmp_path, *, bundle_mtime: float):
    """Create a minimal built-bundle directory with a fixed mtime."""
    static = tmp_path / "static"
    static.mkdir(parents=True)
    (static / "player.js").write_text("// built", encoding="utf-8")
    os.utime(static / "player.js", (bundle_mtime, bundle_mtime))
    return static


def test_bundle_missing_is_stale(tmp_path):
    """No static/ directory at all → must rebuild."""
    webui = _make_webui(tmp_path, source_mtime=1000)
    assert is_bundle_stale(webui, tmp_path / "does-not-exist") is True


def test_bundle_older_than_sources_is_stale(tmp_path):
    """Sources touched after the last build → must rebuild (this is the
    case that silently broke the UI: ported CSS/TS missing from /static)."""
    webui = _make_webui(tmp_path, source_mtime=2000)
    static = _make_static(tmp_path, bundle_mtime=1000)
    assert is_bundle_stale(webui, static) is True


def test_bundle_newer_than_sources_is_fresh(tmp_path):
    """Built after the last source change → skip the rebuild."""
    webui = _make_webui(tmp_path, source_mtime=1000)
    static = _make_static(tmp_path, bundle_mtime=2000)
    assert is_bundle_stale(webui, static) is False


def test_empty_static_dir_is_stale(tmp_path):
    """An existing but empty static/ dir has no artefacts → rebuild."""
    webui = _make_webui(tmp_path, source_mtime=1000)
    static = tmp_path / "static"
    static.mkdir()
    assert is_bundle_stale(webui, static) is True


def test_partially_stale_bundle_is_stale(tmp_path):
    """One outdated artefact makes the whole bundle stale — the check uses
    the OLDEST bundle mtime, not the newest."""
    webui = _make_webui(tmp_path, source_mtime=2000)
    static = _make_static(tmp_path, bundle_mtime=3000)
    old = static / "player.css"
    old.write_text("/* old */", encoding="utf-8")
    os.utime(old, (1000, 1000))
    assert is_bundle_stale(webui, static) is True


def test_build_webui_without_package_json_returns_false(tmp_path):
    """Never raises on a missing/!invalid webui dir — returns False so the
    caller can decide whether to continue (project rule: no crashes)."""
    assert build_webui(tmp_path / "nope") is False


def test_build_webui_skips_when_fresh(tmp_path, monkeypatch):
    """A fresh bundle must not shell out to npm at all."""
    webui = _make_webui(tmp_path, source_mtime=1000)
    _make_static(tmp_path, bundle_mtime=2000)

    import hometools.streaming.webui_build as wb

    monkeypatch.setattr(wb, "STATIC_DIR", tmp_path / "static")
    called = []
    monkeypatch.setattr(wb, "_run", lambda cmd, cwd: called.append(cmd) or True)

    assert build_webui(webui) is True
    assert called == []


def test_build_webui_reports_failure_when_npm_missing(tmp_path, monkeypatch):
    """No npm on PATH → log + return False, never raise."""
    webui = _make_webui(tmp_path, source_mtime=1000)

    import hometools.streaming.webui_build as wb

    monkeypatch.setattr(wb, "STATIC_DIR", tmp_path / "no-static")
    monkeypatch.setattr(wb.shutil, "which", lambda _: None)

    assert build_webui(webui) is False
