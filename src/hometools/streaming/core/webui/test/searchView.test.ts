import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { searchTitle, searchTrackCountLabel, globalSearch, exitGlobalSearch, navigateToSearchFolder } from "../src/searchView";
import type { SearchViewHooks } from "../src/searchView";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<SearchViewHooks> = {}): SearchViewHooks {
  return {
    effectiveThreshold: () => 0,
    showHidden: () => false,
    itemNoun: "song",
    esc: (s) => String(s),
    filePlaceholder: "ph",
    icFolderPlay: "ic",
    trackList: () => null,
    enterTrackListView: vi.fn(),
    showFolderView: vi.fn(),
    playItem: vi.fn(),
    markActive: vi.fn(),
    ...over,
  };
}

describe("labels", () => {
  it("title singular/plural", () => {
    expect(searchTitle(1)).toBe("1 Ergebnis");
    expect(searchTitle(0)).toBe("0 Ergebnisse");
    expect(searchTitle(5)).toBe("5 Ergebnisse");
  });
  it("track count label with folders", () => {
    expect(searchTrackCountLabel(1, 0, "song")).toBe("1 song");
    expect(searchTrackCountLabel(2, 0, "song")).toBe("2 songs");
    expect(searchTrackCountLabel(2, 3, "song")).toBe("3 Ordner · 2 songs");
  });
});

describe("globalSearch", () => {
  it("sets state before entering list view and passes skipFilter/hideFilterBar", () => {
    const s = installState({ allItems: [item("x/Abba.mp3", { title: "Abba" }), item("y/Other.mp3", { title: "Other" })] });
    const order: string[] = [];
    const h = hooks({
      enterTrackListView: vi.fn((o) => {
        order.push("enter");
        expect(s.inPlaylist).toBe(true);
        expect(s.playlistItems).toHaveLength(1);
        expect(o.skipFilter).toBe(true);
        expect(o.hideFilterBar).toBe(true);
        expect(o.title).toBe("1 Ergebnis");
        expect(o.trackCount).toBe("1 song");
      }),
    });
    globalSearch("ABBA", h);
    expect(order).toEqual(["enter"]);
    expect(s.globalSearchActive).toBe(true);
    expect(s.filteredItems).toBe(s.playlistItems);
  });

  it("no state bridge -> no-op", () => {
    (globalThis as unknown as { window: object }).window = {};
    const h = hooks();
    globalSearch("a", h);
    expect(h.enterTrackListView).not.toHaveBeenCalled();
  });
});

describe("exit / navigate", () => {
  function stubInput() {
    const inp = { value: "abc" };
    vi.stubGlobal("document", { getElementById: () => inp });
    return inp;
  }
  it("exitGlobalSearch clears input, flag, shows folder view", () => {
    const s = installState({ globalSearchActive: true });
    const inp = stubInput();
    const h = hooks();
    exitGlobalSearch(h);
    expect(s.globalSearchActive).toBe(false);
    expect(inp.value).toBe("");
    expect(h.showFolderView).toHaveBeenCalledTimes(1);
  });
  it("navigateToSearchFolder sets currentPath", () => {
    const s = installState({ globalSearchActive: true, currentPath: "" });
    stubInput();
    const h = hooks();
    navigateToSearchFolder("a/b", h);
    expect(s.currentPath).toBe("a/b");
    expect(s.globalSearchActive).toBe(false);
    expect(h.showFolderView).toHaveBeenCalled();
  });
});

