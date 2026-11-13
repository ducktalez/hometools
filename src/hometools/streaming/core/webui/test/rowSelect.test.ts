import { describe, it, expect, vi, afterEach } from "vitest";
import { selectTrackRow } from "../src/rowSelect";

afterEach(() => vi.unstubAllGlobals());

function el() {
  const set = new Set<string>();
  return {
    classList: {
      add: (c: string) => set.add(c),
      remove: (c: string) => set.delete(c),
      has: (c: string) => set.has(c),
    },
  };
}

describe("rowSelect", () => {
  it("clears old selection, marks target row", () => {
    const old = el();
    old.classList.add("row-selected");
    const row = el();
    vi.stubGlobal("document", { querySelectorAll: () => [old] });
    const list = { querySelector: vi.fn((s: string) => (s.includes('"3"') ? row : null)) };
    selectTrackRow(list as unknown as ParentNode, 3);
    expect(old.classList.has("row-selected")).toBe(false);
    expect(row.classList.has("row-selected")).toBe(true);
  });
  it("missing row: only clears", () => {
    vi.stubGlobal("document", { querySelectorAll: () => [] });
    const list = { querySelector: () => null };
    expect(() => selectTrackRow(list as unknown as ParentNode, 9)).not.toThrow();
  });
});

