# hometools streaming webui

Vite + TypeScript source of the streaming player UI (audio + video). The
build output goes to `../static/` and is served by FastAPI
(`server_utils/_static.py`); `_html.py` renders the HTML skeleton and links
the hashed bundle.

## Layout

- `src/main.ts` — entry: CSS imports, click guard, hover preview, `startApp()`.
- `src/app.ts` — composition root: reads config, builds the `create*Wiring`
  factories and wires them together.
- `src/config.ts` — `PlayerConfig` = TS contract of the `#ht-config` JSON blob
  (`_html.py::_render_player_config_json`, includes `icons` from `_svg.py`).
- `src/*Wiring.ts` — factories that bind state + DOM to the feature modules.
- `src/*.ts` (rest) — feature modules; pure ones take explicit params.
- `src/stateBridge.ts` — `window.htState`, live view over `app.ts` state.
- `src/globals.d.ts` — ambient types (`CatalogItem`, `Window` extras).
- `src/styles/*.css` — all UI CSS, one stylesheet (`cssCodeSplit: false`).
- `test/*.test.ts` — vitest behaviour tests (node env, `fake-indexeddb`;
  state via `test/helpers.ts::installState()`). Also run from pytest via
  `tests/test_webui_unit.py` (skipped without npm/`node_modules`).

## Usage

```bash
cd src/hometools/streaming/core/webui
npm install
npm run build       # -> ../static/ (git-ignored)
npm run typecheck   # tsc --noEmit
npm test            # vitest run
```

The Docker image builds the bundle automatically. For a source checkout run
`npm install && npm run build` once (and after pulling changes here);
without a bundle `_static.py` logs a warning and the page has no UI logic.

## Rules

- One source of truth per feature; icons stay in `server_utils/_svg.py`
  (`SVG_*`), delivered to the app via `#ht-config.icons`.
- New logic -> small module with explicit params + vitest test; wire it in a
  `*Wiring.ts` / `app.ts`. No new `window` globals.
- API shape change -> update TS, Service Worker (`_pwa.py`) and caches together.

## npm audit notes

`esbuild <=0.24.2` (via `vite@5.4.x`) has an advisory (GHSA-67mh-4wv8-2f99)
affecting only the Vite **dev server**; only `vite build` is used here, so
it is not exploitable. Same for `vitest@2.x`'s `@vitest/mocker` advisory
(GHSA-82fw-gwwq-j7x9): no mocks used. Fix = vite 6+/vitest 4+ major upgrade.