import { defineConfig } from "vite";
import { resolve } from "node:path";

/**
 * Builds the (future) hometools streaming player UI as static assets.
 *
 * Output goes to ../static/ (i.e. src/hometools/streaming/core/static/),
 * from where FastAPI will serve it via StaticFiles once the HTML skeleton
 * (server_utils/_html.py) is switched from inline <script>/<style> to
 * <script src="/static/..."> / <link rel="stylesheet" href="/static/...">.
 *
 * IMPORTANT — migration status (see docs/IMPLEMENTATION_PLAN.md):
 * Phase 4 (static serving) + Phase 5 first slice (fmtTime/escHtml/
 * formatBytes ported to src/main.ts) are done. FastAPI mounts this build's
 * output at /static (see server_utils/_static.py) and _html.py injects a
 * <script src="/static/player.<hash>.js"> tag — resolved via the Vite
 * manifest.json (build.manifest below) — BEFORE the remaining Python-
 * generated inline <script>. Output format is IIFE (not an ES module) and
 * every ported symbol is explicitly attached to `window` so the legacy
 * concatenated inline script (still one shared non-strict function scope)
 * keeps resolving bare identifiers like `fmtTime` via the scope chain to
 * `window.fmtTime` — see src/main.ts's closing `Object.assign(window, ...)`.
 * Do NOT switch this to `format: "es"` without also switching every
 * `<script>` tag that consumes these globals to real ES module imports.
 */
export default defineConfig({
  root: __dirname,
  build: {
    outDir: resolve(__dirname, "../static"),
    emptyOutDir: false,
    manifest: true,
    rollupOptions: {
      input: resolve(__dirname, "src/main.ts"),
      output: {
        format: "iife",
        entryFileNames: "player.[hash].js",
        chunkFileNames: "player-chunk.[hash].js",
        assetFileNames: "player.[hash][extname]",
      },
    },
  },
});

