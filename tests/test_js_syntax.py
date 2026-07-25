"""JS syntax safety net for the generated player JavaScript.

`server_utils/player_js/` and `server_utils/_css.py` generate all frontend
code as plain Python strings (see docs/architecture.md — "CSS/JS package
split"). There is deliberately no TypeScript/bundler pipeline (no Node
toolchain in this repo, no separate frontend build step, instant server
startup — see docs/IMPLEMENTATION_PLAN.md "Agent-friendly codebase
cleanup" for the full trade-off discussion). The one thing a bundler would
normally catch for free — "did this edit produce syntactically broken
JS?" — is covered here instead with a lightweight `esprima` parse check.

This is intentionally NOT a full type-checker or linter: it only proves
the generated JS is parseable, which is exactly the failure mode most
likely to be introduced by editing the split `player_js/*.py` fragment
files (e.g. an unbalanced brace/quote after a manual edit).
"""

from __future__ import annotations

import esprima
import pytest

from hometools.streaming.core.server_utils import render_player_js

# Representative parameter combinations mirroring the real audio/video
# server configs (see streaming/audio/server.py:render_audio_index_html and
# streaming/video/server.py:render_video_index_html) plus the two
# `player_bar_style` branches, which are the only branches that actually
# change the generated JS structure (waveform setup vs. none).
CONFIGS = {
    "audio_classic": dict(
        api_path="/api/audio/tracks",
        item_noun="track",
        file_emoji="\U0001f3b5",
        player_bar_style="classic",
        enable_shuffle=True,
        enable_repeat=True,
        enable_rating_write=True,
        enable_metadata_edit=True,
        enable_recent=False,
        enable_auto_resume=False,
        enable_lyrics=True,
        enable_playlists=True,
        playlist_sync_interval_ms=30000,
        min_rating=2,
        crossfade_duration=3,
        debug_filter=False,
    ),
    "audio_waveform": dict(
        api_path="/api/audio/tracks",
        item_noun="track",
        player_bar_style="waveform",
        enable_shuffle=True,
        enable_repeat=True,
        enable_playlists=True,
        crossfade_duration=3,
    ),
    "video_classic": dict(
        api_path="/api/video/items",
        item_noun="video",
        file_emoji="\U0001f3ac",
        player_bar_style="classic",
        enable_repeat=True,
        enable_playlists=True,
        playlist_sync_interval_ms=30000,
        min_rating=0,
        debug_filter=False,
        language_groups_json='{"de": ["de", "de-DE"]}',
        default_language="de",
        enable_skip_intro=True,
    ),
    "video_waveform": dict(
        api_path="/api/video/items",
        item_noun="video",
        player_bar_style="waveform",
        enable_repeat=True,
        enable_playlists=True,
        enable_skip_intro=True,
    ),
    "defaults": dict(api_path="/api/audio/tracks"),
}


@pytest.mark.parametrize("config_name", sorted(CONFIGS))
def test_render_player_js_is_syntactically_valid(config_name):
    """The full concatenated player JS must always be parseable JS.

    Catches unbalanced braces/quotes/parens introduced by editing one of
    the split `player_js/_*.py` fragment files without needing a
    JS toolchain (esprima is a pure-Python JS parser).
    """
    js = render_player_js(**CONFIGS[config_name])
    assert js.strip(), "render_player_js() returned empty output"
    try:
        esprima.parseScript(js)
    except esprima.Error as exc:
        pytest.fail(f"Generated player JS for config {config_name!r} is not valid JS: {exc}")


def _top_level_function_names(js: str) -> list[str]:
    """Return the names of every top-level `function foo() {}` declaration.

    "Top-level" means directly inside the outer `(function () { ... }())`
    IIFE body — i.e. shared helpers like `showToast`/`formatBytes` — not
    functions nested inside another function (those are legitimately
    allowed to share a name across independent closures, see Rule 14 in
    copilot-instructions.md, e.g. `initPlaylistDragDrop`'s local `startDrag`
    vs. `initQueueDragDrop`'s own `startDrag`).
    """
    program = esprima.parseScript(js)
    outer = program.body[0]
    # (function () { ... }()) -> ExpressionStatement > CallExpression > FunctionExpression
    fn_expr = outer.expression.callee
    names = [stmt.id.name for stmt in fn_expr.body.body if stmt.type == "FunctionDeclaration"]
    return names


@pytest.mark.parametrize("config_name", sorted(CONFIGS))
def test_no_duplicate_top_level_function_declarations(config_name):
    """Two top-level `function foo() {}` with the same name silently shadow
    each other (the later one in source order wins) — no SyntaxError, no
    crash, just quietly wrong behavior at runtime.

    This exact bug happened when `_player_js.py` was split into the
    `player_js/*.py` fragments: `showToast`/`formatBytes` ended up defined
    in two fragment files. The duplicate in `_core.py` was fully shadowed
    by a later one, so any caller relying on `showToast(msg, durationMs)`
    silently had the custom duration ignored. `esprima.parseScript()` alone
    (see test above) does NOT catch this — the JS is perfectly valid syntax.
    """
    js = render_player_js(**CONFIGS[config_name])
    names = _top_level_function_names(js)
    seen = set()
    dupes = set()
    for n in names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    assert not dupes, f"Duplicate top-level function declaration(s) in config {config_name!r}: {sorted(dupes)}"


def test_render_base_css_fragments_concatenate_without_gaps():
    """Sanity check for the CSS split: braces stay balanced end-to-end.

    esprima only parses JS, so this is a minimal structural check (not a
    full CSS parser) — it still catches the most likely breakage from
    editing one of the split `css/_*.py` fragment files: an unbalanced
    `{`/`}` pair at a fragment boundary.
    """
    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert css.count("{") == css.count("}")


@pytest.mark.parametrize("config_name", sorted(CONFIGS))
def test_no_leaked_python_svg_constant_names(config_name):
    """Generated JS must never reference a bare `SVG_*` identifier.

    `SVG_*` (e.g. `SVG_EDIT`) are Python-only constants in `_svg.py`, meant
    to be interpolated into JS string literals at render time (producing
    inline `<svg>...</svg>` markup) or assigned to a JS variable with the
    `IC_*` naming convention (e.g. `var IC_EDIT = '<svg>...`). If a fragment
    file accidentally writes JS source that does `+ SVG_EDIT +` instead of
    `+ IC_EDIT +`, esprima still parses it fine (it's a syntactically valid
    identifier reference) but the browser throws
    `ReferenceError: SVG_EDIT is not defined` at render time, because no
    such JS variable was ever declared.

    This exact bug broke both plain and smart playlist creation: creating
    a smart playlist directly hit the broken `SVG_EDIT` reference in the
    playlist-folder-card renderer; creating a *plain* playlist called
    `showFolderView()` afterwards to refresh the view, which re-rendered
    every existing smart playlist card (if any existed) and threw the same
    ReferenceError — caught by the surrounding `.catch()` and shown as the
    generic "Fehler beim Erstellen" toast, masking the real cause.
    """
    js = render_player_js(**CONFIGS[config_name])
    import re

    leaked = set(re.findall(r"\bSVG_[A-Z_]+\b", js))
    assert not leaked, (
        f"Bare Python SVG_* constant name(s) leaked into generated JS for {config_name!r}: {sorted(leaked)} (should be IC_* JS variables instead)"
    )
