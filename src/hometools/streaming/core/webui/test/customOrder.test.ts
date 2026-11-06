import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { item } from "./helpers";
import { folderOrderKey, loadOrder, sortByOrder, saveOrder, loadOrderAsync } from "../src/customOrder";

describe("order server sync", () => {
  const store: Record<string, string> = {};
  beforeEach(() => {
    for (const k of Object.keys(store)) delete store[k];
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => (k in store ? store[k] : null),
      setItem: (k: string, v: string) => void (store[k] = v),
    });
  });
  afterEach(() => vi.unstubAllGlobals());
  const flush = () => new Promise((r) => setTimeout(r, 0));

  it("saveOrder writes storage + PUT body", () => {
    const f = vi.fn(() => Promise.resolve({}));
    vi.stubGlobal("fetch", f);
    saveOrder("/api/o", "k", "__root__", ["a", "b"]);
    expect(store.k).toBe('["a","b"]');
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/o");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ folder_path: "__root__", items: ["a", "b"] });
  });
  it("saveOrder survives fetch throwing", () => {
    vi.stubGlobal("fetch", () => {
      throw new Error("x");
    });
    expect(() => saveOrder("/api/o", "k", "r", ["a"])).not.toThrow();
  });
  it("loadOrderAsync: server items cached + passed", async () => {
    const f = vi.fn(() => Promise.resolve({ json: () => Promise.resolve({ items: ["x"] }) }));
    vi.stubGlobal("fetch", f);
    const cb = vi.fn();
    loadOrderAsync("/api/o", "k", "A B", cb);
    await flush();
    expect(f).toHaveBeenCalledWith("/api/o?path=A%20B");
    expect(cb).toHaveBeenCalledWith(["x"]);
    expect(store.k).toBe('["x"]');
  });
  it("loadOrderAsync: throwing cb is not called twice", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve({ json: () => Promise.resolve({ items: ["x"] }) }));
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    const cb = vi.fn(() => {
      throw new Error("boom");
    });
    loadOrderAsync("/a", "k", "r", cb);
    await flush();
    expect(cb).toHaveBeenCalledTimes(1);
    expect(err).toHaveBeenCalled();
    err.mockRestore();
  });
  it("loadOrderAsync: empty server / failure -> localStorage fallback", async () => {
    store.k = '["l"]';
    vi.stubGlobal("fetch", () => Promise.resolve({ json: () => Promise.resolve({ items: [] }) }));
    const cb = vi.fn();
    loadOrderAsync("/a", "k", "r", cb);
    await flush();
    expect(cb).toHaveBeenCalledWith(["l"]);
    vi.stubGlobal("fetch", () => Promise.reject(new Error("net")));
    const cb2 = vi.fn();
    loadOrderAsync("/a", "k", "r", cb2);
    await flush();
    expect(cb2).toHaveBeenCalledWith(["l"]);
  });
});
function fakeStorage(data: Record<string, string> = {}) {
  (globalThis as unknown as { localStorage: unknown }).localStorage = {
    getItem: (k: string) => (k in data ? data[k] : null),
  };
}
describe("customOrder", () => {
  beforeEach(() => fakeStorage());
  it("folderOrderKey falls back to __root__", () => {
    expect(folderOrderKey("")).toBe("ht-folder-order-__root__");
    expect(folderOrderKey("Music/Rock")).toBe("ht-folder-order-Music/Rock");
  });
  it("loadOrder: missing, valid, corrupt, non-array", () => {
    expect(loadOrder("k")).toEqual([]);
    fakeStorage({ k: '["a","b"]' });
    expect(loadOrder("k")).toEqual(["a", "b"]);
    fakeStorage({ k: "{nope" });
    expect(loadOrder("k")).toEqual([]);
    fakeStorage({ k: '{"a":1}' });
    expect(loadOrder("k")).toEqual([]);
  });
  it("sortByOrder: ordered first, unknown last, stable, copy", () => {
    const items = [item("x"), item("b"), item("y"), item("a")];
    const out = sortByOrder(items, ["a", "b"]);
    expect(out.map((i) => i.relative_path)).toEqual(["a", "b", "x", "y"]);
    expect(out).not.toBe(items);
  });
  it("sortByOrder: empty order returns same array", () => {
    const items = [item("x")];
    expect(sortByOrder(items, [])).toBe(items);
  });
});
