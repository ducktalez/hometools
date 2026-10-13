import { describe, it, expect } from "vitest";
import { buildDuplicateIndex } from "../src/dupeUtils";
const it_ = (rp: string, title: string, extra = {}) => ({ relative_path: rp, title, artist: "Artist X", ...extra });
describe("buildDuplicateIndex", () => {
  it("groups same normalized title+artist, drops singletons", () => {
    const items = [
      it_("a/one.mp3", "Great Song", { file_size: 1000, duration: 100 }),
      it_("b/one.mp3", "Great Song (Official Video)", { file_size: 1010, duration: 100 }),
      it_("c/other.mp3", "Totally Different"),
    ];
    const idx = buildDuplicateIndex(items);
    const groups = Object.values(idx.map);
    expect(groups).toEqual([[0, 1]]);
    expect(idx.paths.has("a/one.mp3")).toBe(true);
    expect(idx.paths.has("c/other.mp3")).toBe(false);
    expect(idx.safety["a/one.mp3"]).toBe(true);
  });
  it("unsafe when size/duration differ or missing", () => {
    const idx = buildDuplicateIndex([it_("a.mp3", "Great Song"), it_("b.mp3", "Great Song")]);
    expect(idx.safety["a.mp3"]).toBe(false);
    expect(idx.safety["b.mp3"]).toBe(false);
  });
  it("empty input", () => {
    const idx = buildDuplicateIndex([]);
    expect(idx.map).toEqual({});
    expect(idx.paths.size).toBe(0);
  });
});
