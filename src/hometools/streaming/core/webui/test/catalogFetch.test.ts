import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { triggerSilentRefresh, refreshCatalog, scheduleBackgroundRefresh, forceBackgroundRefresh, clearIndexRefreshTimer } from "../src/catalogFetch";
import type { CatalogFetchHooks } from "../src/catalogFetch";

afterEach(() => {
  clearIndexRefreshTimer();
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

