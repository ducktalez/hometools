import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { resolvePlaylistItems } from "../src/smartPlaylist";

const all = [item("a.mp3", { rating: 5 }), item("b.mp3", { rating: 1 }), item("c.mp3")];

describe("resolvePlaylistItems", () => {
  it("unknown id -> null", () => {
    expect(resolvePlaylistItems("x", [], all, {})).toBeNull();
  });

  it("manual: resolves in playlist order, skips missing paths", () => {
    const pls = [{ id: "p", name: "P", items: ["c.mp3", "gone.mp3", "a.mp3"] }];
    const r = resolvePlaylistItems("p", pls, all, {});
    expect(r?.resolved.map((i) => i.relative_path)).toEqual(["c.mp3", "a.mp3"]);
    expect(r?.pl.id).toBe("p");
  });

  it("manual: empty or fully-missing -> null", () => {
    expect(resolvePlaylistItems("p", [{ id: "p", items: [] }], all, {})).toBeNull();
    expect(resolvePlaylistItems("p", [{ id: "p", items: ["gone"] }], all, {})).toBeNull();
  });

  it("smart: evaluates rules; no match -> null", () => {
    const smart = (v: number) => ({ id: "s", smart: { match: "all" as const, rules: [{ field: "rating", op: "gte", value: v }] } });
    expect(resolvePlaylistItems("s", [smart(5)], all, {})?.resolved.map((i) => i.relative_path)).toEqual(["a.mp3"]);
    expect(resolvePlaylistItems("s", [smart(9)], all, {})).toBeNull();
  });
});

