import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { applyHeaderState, enterTrackListView, enterFolderGridView, type ViewHooks } from "../src/viewEntry";

afterEach(() => vi.unstubAllGlobals());

function el() {
  const cls = new Set<string>();
  return {
    cls,
    textContent: "",
    innerHTML: "",
    value: "x",
    currentSrc: "",
    classList: {
      add: (c: string) => cls.add(c),
      remove: (c: string) => cls.delete(c),
      toggle: (c: string, on: boolean) => (on ? cls.add(c) : cls.delete(c)),
    },
  };
}

function setup(recent: { hidden: boolean } | null = { hidden: false }) {
  const dom = {
    headerTitle: el(), backBtn: el(), playAllBtn: el(), folderGrid: el(), trackView: el(),
    filterBar: el(), playerBar: el(), trackCount: el(), searchInput: el(), player: el(),
  };
  const calls: string[] = [];
  const h = {
    dom,
    originalTitle: "Orig",
    renderBreadcrumb: () => calls.push("crumb"),
    applyViewMode: () => calls.push("viewMode"),
    initGlobalSearch: () => calls.push("initSearch"),
    hideGlobalSearch: () => calls.push("hideSearch"),
    initFilterBarScrollReveal: () => calls.push("scroll"),
    applyFilter: () => calls.push("filter"),
    routerUpdate: () => calls.push("router"),
  };
  vi.stubGlobal("document", { getElementById: (id: string) => (id === "recent-section" ? recent : null) });
  return { dom, calls, h: h as unknown as ViewHooks, recent };
}

describe("applyHeaderState", () => {
  it("title falls back: opts.title > leaf of currentPath > original", () => {
    const s = installState({ allItems: [item("a")] });
    const t = setup();
    applyHeaderState({ title: "T" }, t.h);
    expect(t.dom.headerTitle.textContent).toBe("T");
    s.currentPath = "A/B";
    applyHeaderState({}, t.h);
    expect(t.dom.headerTitle.textContent).toBe("B");
    s.currentPath = "";
    applyHeaderState(null, t.h);
    expect(t.dom.headerTitle.textContent).toBe("Orig");
  });
  it("toggles disabled classes, refreshes breadcrumb + view toggle", () => {
    installState({ allItems: [item("a")] });
    const t = setup();
    applyHeaderState({ backDisabled: true, playAllDisabled: false }, t.h);
    expect(t.dom.backBtn.cls.has("disabled")).toBe(true);
    expect(t.dom.playAllBtn.cls.has("disabled")).toBe(false);
    expect(t.calls).toEqual(["crumb", "viewMode", "initSearch"]);
  });
  it("search hidden when catalog empty or disableSearch", () => {
    installState({ allItems: [] });
    const t = setup();
    applyHeaderState({}, t.h);
    expect(t.calls).toContain("hideSearch");
    installState({ allItems: [item("a")] });
    const t2 = setup();
    applyHeaderState({ disableSearch: true }, t2.h);
    expect(t2.calls).toContain("hideSearch");
    expect(t2.calls).not.toContain("initSearch");
  });
});

describe("enterTrackListView", () => {
  it("shows track view, hides grid + recent strip, resets filter box, keeps search shown", () => {
    const s = installState({ allItems: [item("a")], currentIndex: 5 });
    const t = setup();
    enterTrackListView({ resetIndex: true, trackCount: "3 tracks", collapseFilterBar: true }, t.h);
    expect(t.dom.folderGrid.cls.has("view-hidden")).toBe(true);
    expect(t.dom.trackView.cls.has("view-hidden")).toBe(false);
    expect(t.dom.filterBar.cls.has("fb-scroll-hidden")).toBe(true);
    expect(t.dom.playerBar.cls.has("view-hidden")).toBe(false);
    expect(t.recent!.hidden).toBe(true);
    expect(t.dom.searchInput.value).toBe("");
    expect(s.currentIndex).toBe(-1);
    expect(t.dom.trackCount.textContent).toBe("3 tracks");
    expect(t.calls).not.toContain("hideSearch");
    expect(t.calls.slice(-3)).toEqual(["scroll", "filter", "router"]);
  });
  it("skipFilter skips applyFilter; hideFilterBar hides bar; no recent section is fine", () => {
    installState();
    const t = setup(null);
    enterTrackListView({ skipFilter: true, hideFilterBar: true }, t.h);
    expect(t.calls).not.toContain("filter");
    expect(t.dom.filterBar.cls.has("view-hidden")).toBe(true);
  });
});

describe("enterFolderGridView", () => {
  it("back disabled at root by default; grid shown, track view + filter bar hidden", () => {
    installState({ currentPath: "" });
    const t = setup();
    enterFolderGridView({ trackCount: "2 folders", contentHtml: "<x/>" }, t.h);
    expect(t.dom.backBtn.cls.has("disabled")).toBe(true);
    expect(t.dom.folderGrid.cls.has("view-hidden")).toBe(false);
    expect(t.dom.trackView.cls.has("view-hidden")).toBe(true);
    expect(t.dom.filterBar.cls.has("view-hidden")).toBe(true);
    expect(t.dom.trackCount.textContent).toBe("2 folders");
    expect(t.dom.folderGrid.innerHTML).toBe("<x/>");
    expect(t.calls[t.calls.length - 1]).toBe("router");
  });
  it("back enabled in subfolder unless overridden; player bar hidden only without media", () => {
    installState({ currentPath: "A" });
    const t = setup();
    enterFolderGridView({}, t.h);
    expect(t.dom.backBtn.cls.has("disabled")).toBe(false);
    expect(t.dom.playerBar.cls.has("view-hidden")).toBe(true);
    const t2 = setup();
    t2.dom.player.currentSrc = "blob:x";
    enterFolderGridView({ backDisabled: true }, t2.h);
    expect(t2.dom.backBtn.cls.has("disabled")).toBe(true);
    expect(t2.dom.playerBar.cls.has("view-hidden")).toBe(false);
  });
});

