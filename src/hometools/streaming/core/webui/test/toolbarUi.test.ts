import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { onViewToggle, initToolbar, initEditModalEvents, type ToolbarHooks } from "../src/toolbarUi";

let state: { inPlaylist: boolean };
beforeEach(() => {
  state = { inPlaylist: false };
  vi.stubGlobal("window", { htState: state });
  vi.stubGlobal("localStorage", { setItem: vi.fn() });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function el() {
  const h: Record<string, (e?: unknown) => void> = {};
  return { h, addEventListener: (t: string, f: (e?: unknown) => void) => (h[t] = f) };
}

function hooks(over: Partial<ToolbarHooks> = {}): ToolbarHooks {
  let mode = "list";
  let hidden = true;
  return {
    viewToggle: null,
    searchInput: null,
    sortField: null,
    filterCombinedBtn: null,
    filterHiddenBtn: null,
    isVideoMode: false,
    isTrackViewVisible: () => false,
    toggleTrackViewMode: vi.fn(),
    anyToolActive: () => false,
    getViewMode: () => mode,
    setViewMode: (m) => (mode = m),
    getShowHidden: () => hidden,
    setShowHidden: (v) => (hidden = v),
    applyViewMode: vi.fn(),
    applyFilter: vi.fn(),
    showFolderView: vi.fn(),
    toggleFilterPopover: vi.fn(),
    updateFilterChips: vi.fn(),
    routerUpdate: vi.fn(),
    ...over,
  };
}

describe("onViewToggle", () => {
  it("track view: toggles table mode (audio only)", () => {
    const h = hooks({ isTrackViewVisible: () => true });
    onViewToggle(h);
    expect(h.toggleTrackViewMode).toHaveBeenCalled();
    const v = hooks({ isTrackViewVisible: () => true, isVideoMode: true });
    onViewToggle(v);
    expect(v.toggleTrackViewMode).not.toHaveBeenCalled();
  });
  it("folder view: list->grid, re-shows folders, updates router", () => {
    const h = hooks();
    onViewToggle(h);
    expect(h.getViewMode()).toBe("grid");
    expect(h.showFolderView).toHaveBeenCalled();
    expect(h.routerUpdate).toHaveBeenCalled();
  });
  it("in playlist: re-applies mode + filter instead", () => {
    state.inPlaylist = true;
    const h = hooks();
    onViewToggle(h);
    expect(h.applyViewMode).toHaveBeenCalled();
    expect(h.applyFilter).toHaveBeenCalled();
    expect(h.showFolderView).not.toHaveBeenCalled();
  });
  it("locked while tools active", () => {
    const h = hooks({ anyToolActive: () => true });
    onViewToggle(h);
    expect(h.getViewMode()).toBe("list");
  });
});

describe("initToolbar", () => {
  it("debounces search", () => {
    vi.useFakeTimers();
    const search = el();
    const h = hooks({ searchInput: search as unknown as HTMLInputElement });
    initToolbar(h);
    search.h.input();
    search.h.input();
    expect(h.applyFilter).not.toHaveBeenCalled();
    vi.advanceTimersByTime(200);
    expect(h.applyFilter).toHaveBeenCalledTimes(1);
  });
  it("hidden chip toggles flag + persists", () => {
    const btn = el();
    const h = hooks({ filterHiddenBtn: btn as unknown as HTMLElement });
    initToolbar(h);
    btn.h.click();
    expect(h.getShowHidden()).toBe(false);
    expect(localStorage.setItem).toHaveBeenCalledWith("ht-show-hidden", "0");
  });
});

describe("initEditModalEvents", () => {
  it("disabled -> no listeners", () => {
    const doc = { getElementById: vi.fn(), addEventListener: vi.fn() };
    vi.stubGlobal("document", doc);
    initEditModalEvents({ enabled: false, close: vi.fn(), submit: vi.fn() });
    expect(doc.addEventListener).not.toHaveBeenCalled();
  });
  it("Escape closes, Enter in input submits", () => {
    const keys: Record<string, (e: unknown) => void> = {};
    const backdrop = { hasAttribute: () => false, addEventListener: vi.fn() };
    vi.stubGlobal("document", {
      getElementById: () => backdrop,
      addEventListener: (t: string, f: (e: unknown) => void) => (keys[t] = f),
    });
    const close = vi.fn();
    const submit = vi.fn();
    initEditModalEvents({ enabled: true, close, submit });
    keys.keydown({ key: "Escape", preventDefault: vi.fn(), target: {} });
    keys.keydown({ key: "Enter", preventDefault: vi.fn(), target: { tagName: "INPUT" } });
    expect(close).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledTimes(1);
  });
});

