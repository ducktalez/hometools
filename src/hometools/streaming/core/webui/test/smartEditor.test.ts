import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { collectAllPlaylistRelPaths, resolveAllPlaylistItems, buildSmartSubmit } from "../src/smartPlaylist";
import type { SmartEditorState } from "../src/smartPlaylist";

const pls = [
  { id: "a", items: ["x", "y"] },
  { id: "b", items: ["y", "z"] },
  { id: "c" },
];

describe("collectAllPlaylistRelPaths / resolveAllPlaylistItems", () => {
  it("dedups, keeps order", () => {
    expect(collectAllPlaylistRelPaths(pls)).toEqual(["x", "y", "z"]);
    expect(collectAllPlaylistRelPaths([])).toEqual([]);
  });
  it("resolves, skips missing", () => {
    const r = resolveAllPlaylistItems(pls, [item("z"), item("x")]);
    expect(r.map((i) => i.relative_path)).toEqual(["x", "z"]);
  });
});

describe("buildSmartSubmit", () => {
  const st = (o: Partial<SmartEditorState> = {}): SmartEditorState => ({
    id: null,
    name: "N",
    match: "all",
    rules: [{ field: "rating", op: "gte", value: 4 }],
    limit: "",
    ...o,
  });
  it("validates name + rules", () => {
    expect(buildSmartSubmit(st({ name: "" }))).toHaveProperty("error");
    expect(buildSmartSubmit(st({ rules: [] }))).toHaveProperty("error");
  });
  it("POST for new, limit only when > 0", () => {
    const r = buildSmartSubmit(st({ limit: 5 })) as { method: string; payload: any };
    expect(r.method).toBe("POST");
    expect(r.payload.name).toBe("N");
    expect(r.payload.smart.limit).toBe(5);
    const r0 = buildSmartSubmit(st({ limit: 0 })) as { payload: any };
    expect(r0.payload.smart.limit).toBeUndefined();
  });
  it("PUT for existing, strips self-reference", () => {
    const r = buildSmartSubmit(
      st({ id: "me", rules: [{ field: "in_playlist", op: "any_of", value: ["me", "o"] }] })
    ) as { method: string; payload: any };
    expect(r.method).toBe("PUT");
    expect(r.payload.playlist_id).toBe("me");
    expect(r.payload.smart.rules[0].value).toEqual(["o"]);
  });
});

