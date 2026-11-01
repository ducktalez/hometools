import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import { loadFavorites, toggleFavorite } from "../src/favorites";
import type { FavoritesHooks } from "../src/favorites";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<FavoritesHooks> = {}): FavoritesHooks {
  return { apiBase: "/api/audio", toast: vi.fn(), applyFilter: vi.fn(), filterFavActive: () => false, ...over };
}
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("loadFavorites", () => {
  it("replaces savedFavorites from shortcuts, reapplies filter when fav filter active", async () => {
    const s = installState({ inPlaylist: true, savedFavorites: { old: true } });
    vi.stubGlobal("document", { querySelectorAll: () => [] });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ id: "a" }, { id: "b" }] }) }))
    );
    const h = hooks({ filterFavActive: () => true });
    await loadFavorites(h);
    expect(s.savedFavorites).toEqual({ a: true, b: true });
    expect(h.applyFilter).toHaveBeenCalled();
  });
  it("network error leaves state alone", async () => {
    const s = installState({ savedFavorites: { keep: true } });
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    await loadFavorites(hooks());
    expect(s.savedFavorites).toEqual({ keep: true });
  });
});

describe("toggleFavorite", () => {
  it("adds when not pinned", async () => {
    const s = installState();
    const f = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    vi.stubGlobal("fetch", f);
    vi.stubGlobal("navigator", {});
    const h = hooks();
    toggleFavorite({ relative_path: "a/b.mp3", title: "T" }, null, h);
    await flush();
    expect(s.savedFavorites["a/b.mp3"]).toBe(true);
    expect(h.toast).toHaveBeenCalledWith("Als Favorit gespeichert");
  });
  it("removes when pinned", async () => {
    const s = installState({ savedFavorites: { "a/b.mp3": true } });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })));
    const h = hooks();
    toggleFavorite({ relative_path: "a/b.mp3" }, null, h);
    await flush();
    expect(s.savedFavorites["a/b.mp3"]).toBeUndefined();
    expect(h.toast).toHaveBeenCalledWith("Favorit entfernt");
  });
});

