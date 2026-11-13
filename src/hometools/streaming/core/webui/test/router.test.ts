import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readUrl, buildUrl, stateKey, createRouter, type RouterHooks } from "../src/router";

describe("router url helpers", () => {
  it("round-trips params", () => {
    const s = readUrl("?view=playlist&path=a%2Fb&track=a%2Fb%2Fc.mp3&fr=3");
    expect(s.view).toBe("playlist");
    expect(s.path).toBe("a/b");
    expect(s.fr).toBe("3");
    expect(buildUrl(s, "/x")).toBe("/x?view=playlist&path=a%2Fb&track=a%2Fb%2Fc.mp3&fr=3");
  });
  it("empty -> bare pathname", () => {
    expect(buildUrl(readUrl(""), "/x")).toBe("/x");
  });
  it("key ignores track/filter params", () => {
    const a = readUrl("?view=folder&path=p&track=t1");
    const b = readUrl("?view=folder&path=p&track=t2&fr=2");
    expect(stateKey(a)).toBe(stateKey(b));
    expect(stateKey(readUrl("?view=folder&path=q"))).not.toBe(stateKey(a));
  });
});

describe("router restore/update", () => {
  let st: Record<string, unknown>;
  let loc: { pathname: string; search: string };
  const pushState = vi.fn();
  const replaceState = vi.fn();
  beforeEach(() => {
    st = {
      allItems: [],
      filteredItems: [],
      currentIndex: -1,
      currentPath: "",
      inPlaylist: false,
      globalSearchActive: false,
      currentPlaylistId: "",
    };
    loc = { pathname: "/", search: "" };
    vi.stubGlobal("window", { htState: st, location: loc, addEventListener: vi.fn() });
    vi.stubGlobal("history", { pushState, replaceState });
    vi.stubGlobal("localStorage", { setItem: vi.fn() });
    vi.stubGlobal("document", { getElementById: () => null });
    pushState.mockClear();
    replaceState.mockClear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function hooks(over: Partial<RouterHooks> = {}): RouterHooks {
    return {
      getUi: () => ({ rating: 0, fav: false, genre: "", showHidden: true, viewMode: "list" }),
      setUi: vi.fn(),
      toolsOpen: () => false,
      openToolsPanel: vi.fn(),
      contentsAt: () => ({ files: [] }),
      itemsUnder: () => [],
      showPlaylist: vi.fn(),
      showFolderView: vi.fn(),
      showUserPlaylistView: vi.fn(),
      openOfflineLibrary: vi.fn(),
      globalSearch: vi.fn(),
      markActive: vi.fn(),
      updateFilterChips: vi.fn(),
      ...over,
    };
  }

  it("update is suppressed until restore", () => {
    const r = createRouter(hooks());
    r.update();
    expect(pushState).not.toHaveBeenCalled();
    r.restore();
    st.currentPath = "movies";
    r.update();
    expect(pushState).toHaveBeenCalledTimes(1);
    expect(pushState.mock.calls[0][2]).toBe("/?view=folder&path=movies");
  });
  it("restore view=folder navigates", () => {
    loc.search = "?view=folder&path=tv";
    const h = hooks();
    createRouter(h).restore();
    expect(st.currentPath).toBe("tv");
    expect(h.showFolderView).toHaveBeenCalled();
  });
  it("restore favorites + filter params applied", () => {
    loc.search = "?view=favorites&fr=4&fh=0";
    const h = hooks();
    createRouter(h).restore();
    expect(h.showUserPlaylistView).toHaveBeenCalledWith("__favorites__");
    expect(h.setUi).toHaveBeenCalledWith({ rating: 4 });
    expect(h.setUi).toHaveBeenCalledWith({ showHidden: false });
  });
  it("track-only change replaces history", () => {
    const r = createRouter(hooks());
    r.restore();
    st.inPlaylist = true;
    st.currentPath = "a";
    st.filteredItems = [{ relative_path: "a/1.mp3" }, { relative_path: "a/2.mp3" }];
    st.currentIndex = 0;
    r.update();
    st.currentIndex = 1;
    loc.search = "?view=playlist&path=a&track=a%2F1.mp3";
    r.update();
    expect(replaceState).toHaveBeenCalledTimes(1);
  });
});

