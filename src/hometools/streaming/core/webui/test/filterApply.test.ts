import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { computeFilteredItems, updateFilterChips, applyFilter } from "../src/filterApply";
import type { FilterApplyHooks } from "../src/filterApply";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<FilterApplyHooks> = {}): FilterApplyHooks {
  return {
    combinedBtn: () => null,
    hiddenBtn: () => null,
    getFilter: () => ({ rating: 0, fav: false, genre: "" }),
    icFilter: "F",
    icEye: "E",
    effectiveThreshold: () => 0,
    showHidden: () => false,
    refreshOpenPopover: vi.fn(),
    searchValue: () => "",
    sortValue: () => "title",
    locallyDeleted: () => ({}),
    debugFilter: false,
    justRatedPath: () => null,
    savedFavorites: () => ({}),
    hasCustomPlaylist: () => false,
    renderTracks: vi.fn(),
    ...over,
  };
}

describe("computeFilteredItems", () => {
  it("strips locally deleted, applies needle and sorts by title", () => {
    installState({ playlistItems: [item("c", { title: "Cat" }), item("a", { title: "Apple" }), item("b", { title: "Banana" })] });
    const all = computeFilteredItems(hooks());
    expect(all.map((t) => t.relative_path)).toEqual(["a", "b", "c"]);
    const del = computeFilteredItems(hooks({ locallyDeleted: () => ({ b: true }) }));
    expect(del.map((t) => t.relative_path)).toEqual(["a", "c"]);
    const q = computeFilteredItems(hooks({ searchValue: () => "  BAN " }));
    expect(q.map((t) => t.relative_path)).toEqual(["b"]);
  });

  it("favorite filter uses savedFavorites", () => {
    installState({ playlistItems: [item("a"), item("b")] });
    const r = computeFilteredItems(hooks({ getFilter: () => ({ rating: 0, fav: true, genre: "" }), savedFavorites: () => ({ b: true }) }));
    expect(r.map((t) => t.relative_path)).toEqual(["b"]);
  });
});

describe("applyFilter", () => {
  it("renders computed items with force flag", () => {
    installState({ playlistItems: [item("a")] });
    const h = hooks();
    applyFilter(true, h);
    expect(h.renderTracks).toHaveBeenCalledTimes(1);
    const [items, force] = (h.renderTracks as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(items).toHaveLength(1);
    expect(force).toBe(true);
  });
});

describe("updateFilterChips", () => {
  const btn = () => {
    const cls = new Set<string>();
    return {
      innerHTML: "",
      title: "",
      style: { display: "x" },
      classList: { toggle: (c: string, on: boolean) => (on ? cls.add(c) : cls.delete(c)) },
      cls,
    };
  };
  it("updates combined chip, refreshes popover, hides hidden chip when threshold 0", () => {
    installState({ playlistItems: [] });
    const c = btn();
    const hb = btn();
    const h = hooks({
      combinedBtn: () => c as unknown as HTMLElement,
      hiddenBtn: () => hb as unknown as HTMLElement,
      getFilter: () => ({ rating: 3, fav: false, genre: "" }),
    });
    updateFilterChips(h);
    expect(c.innerHTML).toContain("Filtern (1)");
    expect(c.cls.has("active")).toBe(true);
    expect(h.refreshOpenPopover).toHaveBeenCalledTimes(1);
    expect(hb.style.display).toBe("none");
  });
});

