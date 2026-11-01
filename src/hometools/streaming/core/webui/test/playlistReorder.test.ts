import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { reorderPaths, reorderPlaylistItem, applyPlaylistUpdate } from "../src/playlistReorder";

const flush = () => new Promise((r) => setTimeout(r, 0));
const hooks = () => ({
  apiPath: "/pl",
  toast: vi.fn(),
  renderTracks: vi.fn(),
  saveFavoritesOrder: vi.fn(),
  saveFolderOrder: vi.fn(),
});
afterEach(() => vi.unstubAllGlobals());

describe("reorderPaths", () => {
  it("moves + clamps, null when absent", () => {
    expect(reorderPaths(["a", "b", "c"], "a", 2)).toEqual(["b", "c", "a"]);
    expect(reorderPaths(["a", "b", "c"], "c", -5)).toEqual(["c", "a", "b"]);
    expect(reorderPaths(["a", "b"], "a", 99)).toEqual(["b", "a"]);
    expect(reorderPaths(["a"], "x", 0)).toBeNull();
  });
});

describe("reorderPlaylistItem", () => {
  it("no-op without playlist id or on __alltitles__", () => {
    const h = hooks();
    installState({ currentPlaylistId: "" });
    reorderPlaylistItem("a", 0, h);
    installState({ currentPlaylistId: "__alltitles__" });
    reorderPlaylistItem("a", 0, h);
    expect(h.renderTracks).not.toHaveBeenCalled();
  });
  it("favorites: persists order, re-renders, keeps playing index", () => {
    const items = [item("a"), item("b"), item("c")];
    const s = installState({
      currentPlaylistId: "__favorites__",
      playlistItems: items,
      filteredItems: items,
      currentIndex: 0,
    });
    const h = hooks();
    reorderPlaylistItem("a", 2, h);
    expect(h.saveFavoritesOrder).toHaveBeenCalledWith(["b", "c", "a"]);
    expect(s.playlistItems.map((i) => i.relative_path)).toEqual(["b", "c", "a"]);
    expect(s.currentIndex).toBe(2);
    expect(h.renderTracks).toHaveBeenCalledWith(s.filteredItems, true);
  });
  it("folder: saves under currentPath", () => {
    const items = [item("a"), item("b")];
    installState({ currentPlaylistId: "__folder__", currentPath: "F", playlistItems: items, filteredItems: items });
    const h = hooks();
    reorderPlaylistItem("b", 0, h);
    expect(h.saveFolderOrder).toHaveBeenCalledWith("F", ["b", "a"]);
  });
  it("server playlist: optimistic apply then server copy", async () => {
    const all = [item("a"), item("b")];
    const s = installState({
      currentPlaylistId: "p",
      allItems: all,
      userPlaylists: [{ id: "p", name: "P", items: ["a", "b"] }],
    });
    const h = hooks();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ json: () => Promise.resolve({ playlist: { id: "p", name: "P", items: ["b", "a"] } }) })));
    reorderPlaylistItem("a", 1, h);
    expect(h.renderTracks).toHaveBeenCalledTimes(1);
    await flush();
    expect(h.renderTracks).toHaveBeenCalledTimes(2);
    expect((s.userPlaylists[0] as { items: string[] }).items).toEqual(["b", "a"]);
  });
  it("server failure restores snapshot + toasts", async () => {
    const all = [item("a"), item("b")];
    const s = installState({
      currentPlaylistId: "p",
      allItems: all,
      userPlaylists: [{ id: "p", name: "P", items: ["a", "b"] }],
    });
    const h = hooks();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    reorderPlaylistItem("a", 1, h);
    await flush();
    expect((s.userPlaylists[0] as { items: string[] }).items).toEqual(["a", "b"]);
    expect(h.toast).toHaveBeenCalledWith("Fehler beim Verschieben — rückgängig");
  });
});

describe("applyPlaylistUpdate", () => {
  it("skips items missing from catalog", () => {
    const s = installState({ allItems: [item("a")] });
    const h = hooks();
    applyPlaylistUpdate({ id: "p", name: "P", items: ["x", "a"] }, h);
    expect(s.playlistItems.map((i) => i.relative_path)).toEqual(["a"]);
  });
});

