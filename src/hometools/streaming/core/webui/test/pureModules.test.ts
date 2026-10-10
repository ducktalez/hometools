import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { itemsUnder, collectGenres, sortTracks, replaceItemFields } from "../src/catalogQuery";
import { parseIntro, introButtonMode, patchIntroLocal } from "../src/intro";
import { buildFolderMatches, searchItems } from "../src/search";

const rps = (xs: LegacyMediaItem[]) => xs.map((x) => x.relative_path);

describe("catalogQuery", () => {
  const all = [item("A/x.mp3"), item("A/B/y.mp3"), item("AB/z.mp3")];
  it("itemsUnder: prefix + slash, not sibling with same prefix", () => {
    expect(rps(itemsUnder("A", all))).toEqual(["A/x.mp3", "A/B/y.mp3"]);
    expect(itemsUnder("", all)).toBe(all);
  });
  it("collectGenres: distinct, sorted, null-safe", () => {
    expect(collectGenres([item("a", { genre: "Rock" }), item("b", { genre: "Jazz" }), item("c", { genre: "Rock" })])).toEqual(["Jazz", "Rock"]);
    expect(collectGenres(null)).toEqual([]);
  });
  it("sortTracks: copy; title sort is season/episode aware", () => {
    const xs = [item("e2", { title: "B", season: 1, episode: 2 }), item("e1", { title: "C", season: 1, episode: 1 })];
    const out = sortTracks(xs, "title", false);
    expect(rps(out)).toEqual(["e1", "e2"]);
    expect(rps(xs)).toEqual(["e2", "e1"]);
  });
  it("sortTracks custom: playlist order kept; else rating desc", () => {
    const xs = [item("a", { rating: 1 }), item("b", { rating: 5 })];
    expect(rps(sortTracks(xs, "custom", true))).toEqual(["a", "b"]);
    expect(rps(sortTracks(xs, "custom", false))).toEqual(["b", "a"]);
  });
  it("sortTracks recent: mtime desc", () => {
    expect(rps(sortTracks([item("old", { mtime: 1 }), item("new", { mtime: 9 })], "recent", false))).toEqual(["new", "old"]);
  });
  it("replaceItemFields: copy-on-write in every array", () => {
    const orig = item("p", { rating: 1 });
    const a = [orig];
    const b = [orig];
    replaceItemFields([a, b, null], "p", { rating: 4 });
    expect(a[0].rating).toBe(4);
    expect(b[0].rating).toBe(4);
    expect(orig.rating).toBe(1);
    expect(a[0]).not.toBe(orig);
  });
});

describe("intro", () => {
  it("parseIntro: numbers/strings, series flag, null-safe", () => {
    expect(parseIntro(item("x", { intro_start: "2", intro_end: 90, season: 1 }))).toEqual({ start: 2, end: 90, isSeries: true });
    expect(parseIntro(item("x", { intro_end: -5 }))).toEqual({ start: 0, end: 0, isSeries: false });
    expect(parseIntro(null)).toEqual({ start: 0, end: 0, isSeries: false });
  });
  it("introButtonMode: skip window ends 0.3s early", () => {
    expect(introButtonMode(10, 1000, 0, 90, true)).toBe("skip");
    expect(introButtonMode(89.8, 1000, 0, 90, true)).toBe("");
  });
  it("introButtonMode: set window 5s..min(25%,180s), series only", () => {
    expect(introButtonMode(4, 1000, 0, 0, true)).toBe("");
    expect(introButtonMode(100, 1000, 0, 0, true)).toBe("set");
    expect(introButtonMode(181, 1000, 0, 0, true)).toBe("");
    expect(introButtonMode(30, 100, 0, 0, true)).toBe(""); // 25% of 100 = 25
    expect(introButtonMode(100, 1000, 0, 0, false)).toBe("");
  });
  it("patchIntroLocal mutates shared objects", () => {
    const it1 = item("p");
    patchIntroLocal([[it1], null], "p", 1, 80);
    expect(it1).toMatchObject({ intro_start: 1, intro_end: 80 });
  });
});

describe("search", () => {
  const all = [
    item("Avatar/S1/e1.mkv", { title: "Pilot" }),
    item("Avatar/S1/e2.mkv", { title: "Two" }),
    item("Other/avatar-doku.mkv", { title: "Doku" }),
    item("Low/x.mkv", { title: "avatar low", rating: 1 }),
  ];
  it("folder matches: shallow first, counted", () => {
    const fm = buildFolderMatches(all, "avatar", false, 0);
    expect(fm[0]).toMatchObject({ path: "Avatar", depth: 0, count: 2 });
  });
  it("item matches on title/path; hidden threshold applies", () => {
    expect(rps(searchItems(all, "avatar", false, 0))).toHaveLength(4);
    expect(rps(searchItems(all, "avatar", true, 2))).not.toContain("Low/x.mkv");
  });
});

