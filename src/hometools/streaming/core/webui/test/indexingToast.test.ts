import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";

function fakeDom() {
  const classes = new Set<string>();
  const handlers: Record<string, () => void> = {};
  const el = {
    className: "",
    title: "",
    innerHTML: "",
    classList: {
      add: (c: string) => classes.add(c),
      remove: (c: string) => classes.delete(c),
    },
    addEventListener: (e: string, f: () => void) => (handlers[e] = f),
  };
  const create = vi.fn(() => el);
  vi.stubGlobal("document", { createElement: create, body: { appendChild: vi.fn() } });
  const store: Record<string, string> = {};
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => (store[k] = v),
    removeItem: (k: string) => delete store[k],
  });
  vi.stubGlobal("window", {});
  return { el, classes, handlers, create, store };
}

const esc = (s: unknown) => String(s);

beforeEach(() => vi.resetModules());
afterEach(() => vi.unstubAllGlobals());

describe("indexingToast", () => {
  it("shows toast with message", async () => {
    const d = fakeDom();
    const m = await import("../src/indexingToast");
    m.showIndexingToast("Scan", { build_percent: 50 }, esc);
    expect(d.classes.has("visible")).toBe(true);
    expect(d.el.innerHTML).toContain("Scan");
    expect(d.el.innerHTML).toContain("width:50%");
  });

  it("click dismisses for the run and persists; same run stays hidden after reload", async () => {
    const d = fakeDom();
    let m = await import("../src/indexingToast");
    m.showIndexingToast("Scan", { last_build_started_at: 123 }, esc);
    d.handlers.click();
    expect(d.classes.has("visible")).toBe(false);
    expect(d.store["ht-index-toast-dismissed"]).toBe("123");
    m.showIndexingToast("Scan", { last_build_started_at: 123 }, esc);
    expect(d.classes.has("visible")).toBe(false);
    // simulate reload: fresh module, same localStorage
    vi.resetModules();
    m = await import("../src/indexingToast");
    d.classes.clear();
    m.showIndexingToast("Scan", { last_build_started_at: 123 }, esc);
    expect(d.classes.has("visible")).toBe(false);
  });

  it("new run shows toast again", async () => {
    const d = fakeDom();
    d.store["ht-index-toast-dismissed"] = "123";
    const m = await import("../src/indexingToast");
    m.showIndexingToast("Scan", { last_build_started_at: 456 }, esc);
    expect(d.classes.has("visible")).toBe(true);
  });

  it("hide clears dismissal and hides", async () => {
    const d = fakeDom();
    const m = await import("../src/indexingToast");
    m.showIndexingToast("Scan", { last_build_started_at: 1 }, esc);
    d.handlers.click();
    m.hideIndexingToast();
    expect("ht-index-toast-dismissed" in d.store).toBe(false);
    m.showIndexingToast("Scan", { last_build_started_at: 2 }, esc);
    expect(d.classes.has("visible")).toBe(true);
    m.hideIndexingToast();
    expect(d.classes.has("visible")).toBe(false);
  });
});

