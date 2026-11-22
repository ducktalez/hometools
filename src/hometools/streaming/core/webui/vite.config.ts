import { defineConfig } from "vite";
import { resolve } from "node:path";

/**
 * Builds the streaming player UI (src/main.ts -> app.ts) as static assets.
 *
 * Output goes to ../static/ (src/hometools/streaming/core/static/). FastAPI
 * serves it at /static (server_utils/_static.py); _html.py injects
 * <script src="/static/player.<hash>.js"> + the CSS link, resolved via the
 * Vite manifest.json (build.manifest below). Config + icons reach the app
 * through the `#ht-config` JSON blob (see src/config.ts).
 */
export default defineConfig({
  root: __dirname,
  build: {
    outDir: resolve(__dirname, "../static"),
    // true: only the Vite build writes here (gitignored, Docker copies it
    // fresh). false piled up 20+ orphaned hashed bundles.
    emptyOutDir: true,
    manifest: true,
    // false = extract to one real .css file instead of letting Vite inject
    // it from JS at runtime. The bundle <script> sits at the end of <body>,
    // so runtime injection would flash unstyled pills first.
    cssCodeSplit: false,
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

