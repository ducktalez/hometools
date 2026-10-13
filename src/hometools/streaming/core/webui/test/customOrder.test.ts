import { describe, it, expect, beforeEach } from "vitest";
import { item } from "./helpers";
import { folderOrderKey, loadOrder, sortByOrder } from "../src/customOrder";
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
