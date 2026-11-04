import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { triggerSilentRefresh, refreshCatalog, scheduleBackgroundRefresh, forceBackgroundRefresh, clearIndexRefreshTimer, loadInitialCatalog, resetInitialCatalogState } from "../src/catalogFetch";
import type { CatalogFetchHooks, InitialCatalogHooks } from "../src/catalogFetch";

afterEach(() => {
  clearIndexRefreshTimer();
  resetInitialCatalogState();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function hooks(): CatalogFetchHooks {
  return {
    apiPath: "/api/audio/tracks",
    showIndexingToast: vi.fn(),
    hideIndexingToast: vi.fn(),
    applyLocalMutations: (i) => i,
    invalidateCaches: vi.fn(),
    saveCache: vi.fn(),
    clearCache: vi.fn(),
    clearLocalDeleted: vi.fn(),
    resetRatingRefresh: vi.fn(),
    showFolderView: vi.fn(),
    itemsUnder: () => [],
    applyFilter: vi.fn(),
    toast: vi.fn(),
  };
}
function stubFetch(data: unknown, ok = true) {
  const f = vi.fn(() => Promise.resolve({ ok, json: () => Promise.resolve(data) }));
  vi.stubGlobal("fetch", f);
  vi.stubGlobal("document", { getElementById: () => null });
  return f;
}
const tick = () => new Promise((r) => setTimeout(r, 0));

describe("triggerSilentRefresh", () => {
  it("saves cache, re-renders on change", async () => {
    const s = installState({ allItems: [item("a")] });
    stubFetch({ items: [item("a"), item("b")] });
    const h = hooks();
    triggerSilentRefresh(h);
    await tick();
    expect(s.allItems.length).toBe(2);
    expect(h.saveCache).toHaveBeenCalled();
    expect(h.showFolderView).toHaveBeenCalled();
  });
  it("no re-render when unchanged, still saves", async () => {
    installState({ allItems: [item("a")] });
    stubFetch({ items: [item("a")] });
    const h = hooks();
    triggerSilentRefresh(h);
    await tick();
    expect(h.saveCache).toHaveBeenCalled();
    expect(h.showFolderView).not.toHaveBeenCalled();
  });
  it("ignores loading/error payload", async () => {
    installState({ allItems: [item("a")] });
    stubFetch({ loading: true, items: [] });
    const h = hooks();
    triggerSilentRefresh(h);
    await tick();
    expect(h.saveCache).not.toHaveBeenCalled();
  });
  it("in playlist: re-filters with items under path", async () => {
    const s = installState({ allItems: [item("a")], inPlaylist: true, currentPath: "f" });
    stubFetch({ items: [item("f/x")] });
    const h = hooks();
    h.itemsUnder = () => [item("f/x")];
    triggerSilentRefresh(h);
    await tick();
    expect(s.playlistItems.length).toBe(1);
    expect(h.applyFilter).toHaveBeenCalled();
  });
});

describe("refreshCatalog", () => {
  it("clears caches first, POSTs refresh, polls and saves", async () => {
    installState({ allItems: [item("a")] });
    const f = stubFetch({ items: [item("a"), item("b")] });
    const h = hooks();
    refreshCatalog(h);
    expect(h.clearCache).toHaveBeenCalled();
    expect(h.clearLocalDeleted).toHaveBeenCalled();
    await tick();
    await tick();
    await tick();
    expect(f).toHaveBeenCalledWith("/api/audio/refresh", { method: "POST" });
    expect(h.saveCache).toHaveBeenCalled();
    expect(h.toast).toHaveBeenCalled();
  });
});

describe("scheduleBackgroundRefresh", () => {
  it("full index: hides toast, saves cache, renders", async () => {
    vi.useFakeTimers();
    const s = installState();
    stubFetch({ items: [item("a")] });
    const h = hooks();
    scheduleBackgroundRefresh(h, 0);
    await vi.advanceTimersByTimeAsync(5);
    expect(h.hideIndexingToast).toHaveBeenCalled();
    expect(h.saveCache).toHaveBeenCalled();
    expect(s.allItems.length).toBe(1);
  });
  it("force is no-op without pending timer", () => {
    installState();
    const f = stubFetch({});
    forceBackgroundRefresh(hooks());
    expect(f).not.toHaveBeenCalled();
  });
});


function initHooks(cache: LegacyMediaItem[] | null = null): InitialCatalogHooks {
  return {
    ...hooks(),
    loadCache: () => cache,
    showLoadingState: vi.fn(),
    showCatalogLoadError: vi.fn(),
    autoRefreshOn: () => true,
  };
}
describe("loadInitialCatalog", () => {
  it("already-present payload: no fetch", async () => {
    installState({ allItems: [item("a")] });
    const f = stubFetch({});
    const r = await loadInitialCatalog(initHooks());
    expect(r.length).toBe(1);
    expect(f).not.toHaveBeenCalled();
  });
  it("cache hit: renders immediately, loads cache BEFORE any fetch, verifies silently", async () => {
    const s = installState();
    const f = stubFetch({ items: [item("a"), item("b")] });
    const h = initHooks([item("a")]);
    const p = loadInitialCatalog(h);
    expect(h.showFolderView).toHaveBeenCalledTimes(1);
    expect(h.showLoadingState).not.toHaveBeenCalled();
    await p;
    await tick();
    expect(f).toHaveBeenCalledTimes(1);
    expect(s.allItems.length).toBe(2);
    expect(h.saveCache).toHaveBeenCalled();
    expect(h.showFolderView).toHaveBeenCalledTimes(2);
  });
  it("cache hit + offline server: cached items stay", async () => {
    const s = installState();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const h = initHooks([item("a")]);
    await loadInitialCatalog(h);
    await tick();
    expect(s.allItems.length).toBe(1);
    expect(h.showCatalogLoadError).not.toHaveBeenCalled();
  });
  it("no cache: loading state, fetch, save, render, hide toast", async () => {
    const s = installState();
    stubFetch({ items: [item("a")] });
    const h = initHooks();
    const r = await loadInitialCatalog(h);
    expect(h.showLoadingState).toHaveBeenCalled();
    expect(h.saveCache).toHaveBeenCalled();
    expect(h.showFolderView).toHaveBeenCalled();
    expect(h.hideIndexingToast).toHaveBeenCalled();
    expect(r.length).toBe(1);
    expect(s.allItems.length).toBe(1);
  });
  it("server still building and empty: toast + retry later, returns []", async () => {
    vi.useFakeTimers();
    installState();
    const f = stubFetch({ loading: true, items: [], detail: "warming" });
    const h = initHooks();
    const r = await loadInitialCatalog(h);
    expect(r).toEqual([]);
    expect(h.showIndexingToast).toHaveBeenCalledWith("warming", undefined);
    expect(f).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(900);
    expect(f.mock.calls.length).toBeGreaterThanOrEqual(2);
  });
  it("refreshing + auto-refresh off: no background poll", async () => {
    vi.useFakeTimers();
    installState();
    const f = stubFetch({ items: [item("a")], refreshing: true });
    const h = { ...initHooks(), autoRefreshOn: () => false };
    await loadInitialCatalog(h);
    await vi.advanceTimersByTimeAsync(2000);
    expect(f).toHaveBeenCalledTimes(1);
    expect(h.showIndexingToast).toHaveBeenCalled();
  });
  it("http error: shows load error", async () => {
    installState();
    stubFetch({}, false);
    const h = initHooks();
    const r = await loadInitialCatalog(h);
    expect(r).toEqual([]);
    expect(h.showCatalogLoadError).toHaveBeenCalledWith("HTTP undefined");
  });
});
