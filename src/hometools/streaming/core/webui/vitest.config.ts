import { defineConfig } from "vitest/config";

/**
 * Unit tests for pure/bridge-backed modules in src/. Tests live in test/
 * (outside src/: not bundled, no rebuild trigger, not in tsc include).
 * Node env — no DOM; bridge-backed modules get a fake window.htState.
 * Run: `npm test` (also invoked from pytest, tests/test_webui_unit.py).
 */
export default defineConfig({
  test: {
    root: __dirname,
    include: ["test/**/*.test.ts"],
    environment: "node",
  },
});

