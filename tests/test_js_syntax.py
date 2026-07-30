"""JS syntax safety net for the generated player JavaScript.

`server_utils/player_js/` and `server_utils/_css.py` generate almost all
frontend code as plain Python strings (see docs/architecture.md — "CSS/JS
package split"). There is deliberately no bundler pipeline for *this* code
(Vite/TS migration Phase 5 is porting it module-by-module instead — see
docs/IMPLEMENTATION_PLAN.md; the first ported slice, `fmtTime`/`escHtml`/
`formatBytes`, already lives in `streaming/core/webui/src/main.ts` and was
deleted from `player_js/_core.py`). The one thing a bundler would normally
catch for free — "did this edit produce syntactically broken JS?" — is
covered here instead with a lightweight `esprima` parse check, for
whatever remains un-ported.

This is intentionally NOT a full type-checker or linter: it only proves
the generated JS is parseable, which is exactly the failure mode most
likely to be introduced by editing the split `player_js/*.py` fragment
files (e.g. an unbalanced brace/quote after a manual edit). Once a
fragment is fully ported to `.ts`, `tsc --noEmit` (via `npm run
typecheck` in `webui/`) supersedes this check for that fragment — see
Phase 6 in docs/IMPLEMENTATION_PLAN.md.
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
#
# Vite/TS migration Phase 3 (docs/IMPLEMENTATION_PLAN.md): render_player_js()
# now only accepts `player_bar_style` — every other former parameter
# (api_path, item_noun, enable_*, min_rating, ...) is read at runtime from
# the `#ht-config` JSON blob instead. audio_classic/video_classic (and
# audio_waveform/video_waveform) therefore produce byte-identical output;
# the distinct keys are kept only for readable test IDs / historical parity
# with the render_media_page()-level config that used to vary per key here.
CONFIGS = {
    "audio_classic": dict(player_bar_style="classic"),
    "audio_waveform": dict(player_bar_style="waveform"),
    "video_classic": dict(player_bar_style="classic"),
    "video_waveform": dict(player_bar_style="waveform"),
    "defaults": dict(),
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


@pytest.mark.parametrize("config_name", sorted(CONFIGS))
def test_ic_star_and_edit_match_svg_py(config_name):
    """The `IC_STAR`/`IC_STAR_FILLED`/`IC_STAR_EMPTY`/`IC_EDIT` JS variables
    must embed the exact markup of `_svg.py`'s `SVG_STAR`/`SVG_STAR_EMPTY`/
    `SVG_EDIT` constants.

    `_player_js.py`'s header used to hardcode a *second*, independent copy
    of this markup instead of referencing the already-imported `SVG_*`
    constants. Both copies were valid JS, so no syntax/leak test caught it
    — editing `_svg.py` silently had zero effect on the rendered icon. This
    test locks the two together so any future edit to `_svg.py` is
    guaranteed to reach the browser.
    """
    from hometools.streaming.core.server_utils._svg import (
        SVG_EDIT,
        SVG_STAR,
        SVG_STAR_EMPTY,
    )

    js = render_player_js(**CONFIGS[config_name])
    assert SVG_STAR.replace("'", "\\'") in js, "IC_STAR/IC_STAR_FILLED out of sync with SVG_STAR in _svg.py"
    assert SVG_STAR_EMPTY.replace("'", "\\'") in js, "IC_STAR_EMPTY out of sync with SVG_STAR_EMPTY in _svg.py"
    assert SVG_EDIT.replace("'", "\\'") in js, "IC_EDIT out of sync with SVG_EDIT in _svg.py"


def test_audit_panel_star_matches_svg_py():
    """Same guarantee as above for the standalone audit-panel script."""
    from hometools.streaming.core.server_utils._audit import render_audit_panel_html
    from hometools.streaming.core.server_utils._svg import SVG_STAR, SVG_STAR_EMPTY

    html = render_audit_panel_html(server="hometools audio", media_type="audio", title="Audit")
    assert SVG_STAR.replace("'", "\\'") in html
    assert SVG_STAR_EMPTY.replace("'", "\\'") in html
