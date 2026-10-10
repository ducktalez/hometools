import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { applyFilterChain, type FilterChainOptions } from "../src/filterChain";

const base: FilterChainOptions = {
  needle: "",
  debugFilter: false,
  effectiveThreshold: 0,
  showHidden: true,
  justRatedPath: null,
  filterRating: 0,
  filterFav: false,
  filterGenre: "",
  savedFavorites: {},
};
const opts = (o: Partial<FilterChainOptions>) => ({ ...base, ...o });
const rps = (xs: LegacyMediaItem[]) => xs.map((x) => x.relative_path);

const items = [
  item("u", { rating: 0, genre: "Rock" }),
  item("r1", { rating: 1, genre: "Pop" }),
  item("r2", { rating: 2, genre: "Rock" }),
  item("r5", { rating: 5, genre: "Pop", title: "Hello" }),
];

describe("normal mode", () => {
  it("threshold, showHidden=false: hides rated-below, keeps unrated + threshold", () => {
    const out = applyFilterChain(items, opts({ effectiveThreshold: 2, showHidden: false }));
    expect(rps(out)).toEqual(["u", "r2", "r5"]);
  });
  it("threshold, showHidden=true: keeps all, grays below (clone, original untouched)", () => {
    const out = applyFilterChain(items, opts({ effectiveThreshold: 2 }));
    expect(rps(out)).toEqual(["u", "r1", "r2", "r5"]);
    expect(out[1]._hiddenShown).toBe(true);
    expect(items[1]._hiddenShown).toBeUndefined();
  });
  it("just-rated item survives threshold, grayed", () => {
    const out = applyFilterChain(items, opts({ effectiveThreshold: 2, showHidden: false, justRatedPath: "r1" }));
    expect(rps(out)).toContain("r1");
    expect(out.find((x) => x.relative_path === "r1")?._hiddenShown).toBe(true);
  });
  it("quick rating filter keeps just-rated, grayed", () => {
    const out = applyFilterChain(items, opts({ filterRating: 3, justRatedPath: "r2" }));
    expect(rps(out)).toEqual(["r2", "r5"]);
    expect(out[0]._hiddenShown).toBe(true);
  });
  it("fav + genre + needle", () => {
    expect(rps(applyFilterChain(items, opts({ filterFav: true, savedFavorites: { r2: true } })))).toEqual(["r2"]);
    expect(rps(applyFilterChain(items, opts({ filterGenre: "Pop" })))).toEqual(["r1", "r5"]);
    expect(rps(applyFilterChain(items, opts({ needle: "hello" })))).toEqual(["r5"]);
  });
  it("hidden-shown items bypass quick filters", () => {
    const out = applyFilterChain(items, opts({ effectiveThreshold: 2, filterGenre: "Rock" }));
    expect(rps(out)).toEqual(["u", "r1", "r2"]);
  });
});

describe("debug mode", () => {
  it("annotates instead of removing; needle still filters", () => {
    const out = applyFilterChain(items, opts({ debugFilter: true, filterGenre: "Pop", effectiveThreshold: 2, showHidden: false }));
    expect(rps(out)).toEqual(["u", "r1", "r2", "r5"]);
    expect(out[0]._debugReason).toMatch(/Genre/);
    expect(out[1]._debugReason).toMatch(/Schwelle/);
    expect(out[3]._debugReason).toBeUndefined();
    expect(rps(applyFilterChain(items, opts({ debugFilter: true, needle: "hello" })))).toEqual(["r5"]);
  });
});

