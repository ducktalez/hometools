import { describe, it, expect } from "vitest";
import { initViewState } from "../src/viewState";

const store = (o: Record<string, string>) => ({ getItem: (k: string) => (k in o ? o[k] : null) });

describe("initViewState", () => {
  it("defaults", () => {
    expect(initViewState(false, store({}))).toEqual({
      filterRating: 0,
      filterFav: false,
      filterGenre: "",
      showHidden: true,
      viewMode: "list",
      trackViewMode: "rows",
    });
  });
  it("reads persisted values", () => {
    const s = initViewState(
      false,
      store({
        "ht-filter-rating": "4",
        "ht-filter-fav": "1",
        "ht-filter-genre": "Rock",
        "ht-show-hidden": "0",
        "ht-view-mode": "grid",
        "ht-track-view-mode": "table",
      }),
    );
    expect(s).toEqual({ filterRating: 4, filterFav: true, filterGenre: "Rock", showHidden: false, viewMode: "grid", trackViewMode: "table" });
  });
  it("video never starts in table mode", () => {
    expect(initViewState(true, store({ "ht-track-view-mode": "table" })).trackViewMode).toBe("rows");
  });
  it("garbage values fall back", () => {
    const s = initViewState(false, store({ "ht-filter-rating": "x", "ht-view-mode": "zzz" }));
    expect(s.filterRating).toBe(0);
    expect(s.viewMode).toBe("list");
  });
  it("throwing storage tolerated", () => {
    const bad = {
      getItem: () => {
        throw new Error("denied");
      },
    };
    expect(initViewState(false, bad).viewMode).toBe("list");
  });
});
