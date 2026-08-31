# hometools streaming webui (migration scaffold)

Vite + TypeScript build for the streaming player UI. This directory is
**Phase 1** of the gradual migration away from the Python-string-generated
JS/CSS in `server_utils/_player_js.py` / `_css.py` / `player_js/*.py` /
`css/*.py`.

**Current status (2026-08-06):** Phase 1-4 done, Phase 5 in progress
(opportunistic slices only — see below). A prior attempt to bulk-port all
9 `player_js/*.py` files into one `legacy.ts` via `eval()` caused a real
production outage (catalog never rendered — see `docs/IMPLEMENTATION_PLAN.md`
→ "Vite/TypeScript migration" for the short version). That file has been
deleted; the proven, working ports so far are the small incremental ones
listed below. Don't attempt a bulk `eval()` port again.

## Why this exists

See `docs/IMPLEMENTATION_PLAN.md` → "Vite/TypeScript migration" and
`.github/instructions/streaming.instructions.md` for context. Short version:
the ~8900 lines of generated JS live as Python string concatenation
(`"""..." + value + """..."`), which has no IDE support, no static typing,
and only a parser-level safety net (`tests/test_js_syntax.py` via
`esprima`). The goal is to move this to real `.ts`/`.css` files built by
Vite, served as static assets by FastAPI — **without** touching the backend
(FastAPI/catalog/sync/etc. stay exactly as they are).

## Local usage

```bash
cd src/hometools/streaming/core/webui
npm install
npm run build       # outputs to ../static/
npm run typecheck   # tsc --noEmit
```

`npm run build` output goes to `src/hometools/streaming/core/static/`
(git-ignored, `node_modules/` also git-ignored). No Node runtime is
required on the server — only at build time, same as any other frontend
build step.

**Known `npm audit` finding:** `esbuild <=0.24.2` (bundled by `vite@5.4.x`)
has a moderate advisory (GHSA-67mh-4wv8-2f99) that only affects the Vite
**dev server** (`vite dev`/`vite serve`) — a malicious website could read
responses from a locally running dev server. This scaffold only ever runs
`vite build` (no dev server is used or exposed), so the finding is not
exploitable here. Revisit when upgrading to Vite 7+ becomes convenient
(breaking change, needs a newer Node baseline).

## Migration plan

1. **Config extraction** (done) — moved all request-varying values
   previously interpolated into `render_player_js(...)` (api_path,
   enable_shuffle, language_groups_json, min_rating, ...) into one JSON
   blob rendered as `<script id="ht-config" type="application/json">` next
   to the existing `#initial-data` tag in `_html.py`. `PlayerConfig` in
   `src/main.ts` is the TypeScript contract for that blob.
2. **Static serving** (done) — `FastAPI` `StaticFiles` mount for `/static/`
   (`server_utils/_static.py::mount_static_assets()`); `_html.py` renders
   `<script src="/static/player.<hash>.js"></script>` right before the
   remaining inline `<script>{js}</script>`. Built in `format: "iife"` (not
   an ES module) so ported symbols can be bridged onto `window` — see
   `vite.config.ts` and `src/main.ts`'s header comment.
3. **Module-by-module port** (in progress) — `player_js/_core.py` →
   `src/core.ts`, etc. First slice done: `fmtTime`/`escHtml`/`formatBytes`
   (the only three top-level helpers in the entire generated JS with zero
   references to any other identifier — see
   `docs/IMPLEMENTATION_PLAN.md` Design Discussions for why that mattered
   and what blocks the next, more-coupled fragments). Each ported module:
   delete the Python generator function, update
   `tests/test_feature_parity.py` and `tests/test_streaming_player_ui.py`
   to assert against the built JS bundle instead of the Python string.
4. **Cleanup** — once all `player_js/*.py` + `css/*.py` modules are ported,
   delete `_player_js.py`/`_css.py` and the `esprima`-based
   `tests/test_js_syntax.py` (superseded by `tsc`).

## Local build for development (outside Docker)

If you're running a streaming server directly from a source checkout
(not the Docker image, which builds this automatically), run this once
(and again after pulling changes to this directory):

```bash
cd src/hometools/streaming/core/webui
npm install
npm run build
```

Without this, `server_utils/_static.py` logs a startup warning and the
page renders without the `/static` bundle — any already-ported symbol
(currently `fmtTime`/`escHtml`/`formatBytes`) will be `undefined` in the
browser and throw a `ReferenceError` when called.

## Rules while this migration is in progress

- Do **not** duplicate business logic between a `.ts` file here and its
  Python counterpart — pick one source of truth per module and delete the
  other in the same change (per `.github/copilot-instructions.md` rule 1).
- Before porting a `player_js/*.py` fragment, grep the **entire**
  `player_js/` directory for every identifier it defines — if any other
  fragment reads/writes one of them, you need an ambient `.d.ts` contract
  for the shared globals first (see `docs/IMPLEMENTATION_PLAN.md` Design
  Discussions → "Player-JS-Modulkopplung"). That contract now exists at
  `src/legacy-globals.d.ts` — extend it (don't duplicate) as more of
  `_core.py`'s state gets bridged onto `window` by a future port.

### Opportunistic migration rule

Don't schedule a big dedicated "port fragment X" task for every remaining
`player_js/*.py` file. Instead: whenever *any* unrelated change (bugfix,
feature) touches a `player_js/*.py` fragment, check the function(s) you're
already editing/near:

1. Is it pure (no read/write of any identifier from `legacy-globals.d.ts`
   or another fragment) or does it only need types already declared there?
2. If yes — port it to a `.ts` module in the same change: delete the
   Python string version, add a one-line comment pointing at the new file
   (see `pathUtils.ts`/`dupeUtils.ts` for the pattern), bridge it onto
   `window` in `main.ts`, and update any test that asserted the function's
   presence/behavior in `render_player_js()`'s output to instead read the
   `.ts` source (or, once available, the built bundle).
3. If no (it reads/writes stateful globals not yet in the ambient
   contract) — leave it, but add the missing identifiers to
   `legacy-globals.d.ts` if you now know their type, so the *next*
   opportunistic port has one less blocker.

This keeps the migration moving without a dedicated migration sprint, and
each slice stays small enough to review and test in isolation — mirroring
how `needsConversion`/`filenameFromPath`/`dupeUtils.ts` were ported.

## CSS ports (`src/styles/*.css`)

CSS has none of the coupling problems JS has — a fragment is just a string,
nothing reads identifiers from anywhere. Port one `css/*.py` fragment at a
time:

1. Copy the rules into `src/styles/<area>.css`, import it in `main.ts`.
2. Delete the Python fragment + its `render_*_css()` export and its entry
   in `_css.py`'s concatenation.
3. Add a test asserting the rules are gone from `render_base_css()` and
   present in the `.css` file (see
   `tests/test_streaming_static.py::test_meta_pill_css_ported_out_of_python`).

Build details: `cssCodeSplit: false` extracts one real stylesheet instead
of letting Vite inject it from JS at runtime — the bundle `<script>` sits
at the end of `<body>`, so runtime injection would flash unstyled content.
`_html.py` links it **after** the inline `<style>`, so a ported rule wins
over a stale legacy duplicate at equal specificity.

Ported so far: `metaPill.css`.

