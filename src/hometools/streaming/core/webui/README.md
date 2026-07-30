# hometools streaming webui (migration scaffold)

Vite + TypeScript build for the streaming player UI. This directory is
**Phase 1** of the gradual migration away from the Python-string-generated
JS/CSS in `server_utils/_player_js.py` / `_css.py` / `player_js/*.py` /
`css/*.py`.

**Current status (2026-07-30):** Phase 1-4 done, Phase 5 in progress (first
slice done — `fmtTime`/`escHtml`/`formatBytes` are real TS functions here,
bridged onto `window` for the remaining Python-generated inline script to
consume). FastAPI mounts this build's output at `/static`
(`server_utils/_static.py`) and `_html.py` renders its `<script src="...">`
tag before the remaining inline `<script>{js}</script>`. See
`docs/architecture.md` → "Phase 4: FastAPI static serving + Phase 5 first
slice" for the full design.

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
  Discussions → "Player-JS-Modulkopplung").


