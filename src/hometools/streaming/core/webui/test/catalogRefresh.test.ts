import { describe, it, expect } from "vitest";
import { catalogChanged, refreshToastMessage, hhmm, catalogRefreshInfo, ratingRefreshInfo, patchRatingsInPlace } from "../src/catalogRefresh";

const it_ = (rp: string, extra: Record<string, unknown> = {}) => ({ relative_path: rp, ...extra });

describe("catalogChanged", () => {
  it("count differs", () => expect(catalogChanged([it_("a")], [it_("a"), it_("b")])).toBe(true));
  it("same paths -> unchanged", () => expect(catalogChanged([it_("a"), it_("b")], [it_("b"), it_("a")])).toBe(false));
  it("same count, replaced file -> changed", () => expect(catalogChanged([it_("a")], [it_("b")])).toBe(true));
  it("both empty -> unchanged", () => expect(catalogChanged([], [])).toBe(false));
});

describe("refreshToastMessage", () => {
  it("added / removed / same", () => {
    expect(refreshToastMessage(12, 10)).toBe("12 Titel geladen (+2 neu)");
    expect(refreshToastMessage(8, 10)).toBe("8 Titel geladen (-2 entfernt)");
    expect(refreshToastMessage(10, 10)).toBe("10 Titel geladen");
  });
});

describe("info texts", () => {
  const dt = new Date(2026, 0, 2, 3, 4);
  it("hhmm pads", () => expect(hhmm(dt)).toBe("03:04"));
  it("catalog info", () => expect(catalogRefreshInfo(5, dt)).toBe("5 Titel (03:04)"));
  it("rating info", () => {
    expect(ratingRefreshInfo(7, 0, dt)).toBe("7 Ratings gelesen (03:04)");
    expect(ratingRefreshInfo(7, 2, dt)).toBe("7 Ratings gelesen, 2 aktualisiert (03:04)");
  });
});

describe("patchRatingsInPlace", () => {
  it("replaces changed items only, keeps others by identity", () => {
    const a = it_("a", { rating: 1 });
    const b = it_("b", { rating: 2 });
    const items = [a, b];
    const n = patchRatingsInPlace(items, { a: 5, b: 2, zzz: 1 });
    expect(n).toBe(1);
    expect(items[0]).not.toBe(a);
    expect(items[0].rating).toBe(5);
    expect(a.rating).toBe(1); // original untouched
    expect(items[1]).toBe(b);
  });
});

