import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { refreshFolderRatings, resetRatingRefresh } from "../src/ratingRefresh";

afterEach(() => {
  vi.unstubAllGlobals();
  resetRatingRefresh();
});

function stub(data: unknown) {
  const info = { textContent: "", title: "" };
  vi.stubGlobal("document", { getElementById: () => info });
  const f = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(data) }));
  vi.stubGlobal("fetch", f);
  return { f, info };
}
const tick = () => new Promise((r) => setTimeout(r, 0));

describe("refreshFolderRatings", () => {
  it("no-op when disabled or empty", () => {
    installState();
    const { f } = stub({});
    const applyFilter = vi.fn();
    refreshFolderRatings([item("a")], { enabled: false, apiBase: "/x", applyFilter });
    refreshFolderRatings([], { enabled: true, apiBase: "/x", applyFilter });
    expect(f).not.toHaveBeenCalled();
  });
  it("patches ratings, re-renders in playlist view, dedupes same folder", async () => {
    const a = item("a", { rating: 1 });
    const s = installState({ allItems: [a], playlistItems: [a], inPlaylist: true, currentPath: "f" });
    const { f } = stub({ ratings: { a: 5 }, changed: 1, last_refresh: "2026-01-01T10:00:00Z" });
    const applyFilter = vi.fn();
    const h = { enabled: true, apiBase: "/api/audio", applyFilter };
    refreshFolderRatings([a], h);
    await tick();
    await tick();
    expect(f).toHaveBeenCalledTimes(1);
    expect(s.allItems[0].rating).toBe(5);
    expect(applyFilter).toHaveBeenCalled();
    refreshFolderRatings([a], h);
    expect(f).toHaveBeenCalledTimes(1);
    resetRatingRefresh();
    refreshFolderRatings([a], h);
    expect(f).toHaveBeenCalledTimes(2);
  });
});

