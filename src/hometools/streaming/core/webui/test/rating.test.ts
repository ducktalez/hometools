import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { patchAllItemsRating, setRating } from "../src/rating";
import type { RatingHooks } from "../src/rating";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<RatingHooks> = {}): RatingHooks {
  return {
    writeEnabled: true,
    ratingApiPath: "/api/audio/rating",
    auditUndoPath: "/api/audit/undo",
    icStarFilled: "F",
    icStarEmpty: "E",
    toast: vi.fn(),
    applyFilter: vi.fn(),
    markActive: vi.fn(),
    rebuildShuffleQueue: vi.fn(),
    ...over,
  };
}
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("patchAllItemsRating", () => {
  it("patches every array copy-on-write", () => {
    const a = item("a.mp3", { rating: 1 });
    const s = installState({ allItems: [a], playlistItems: [a], filteredItems: [a], userQueue: [a] });
    patchAllItemsRating("a.mp3", 4);
    expect(s.allItems[0].rating).toBe(4);
    expect(s.playlistItems[0].rating).toBe(4);
    expect(s.filteredItems[0].rating).toBe(4);
    expect(s.userQueue[0].rating).toBe(4);
    expect(a.rating).toBe(1);
  });
});

describe("setRating", () => {
  it("no-op when write disabled", () => {
    installState({ filteredItems: [item("a.mp3")], currentIndex: 0 });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    setRating(5, hooks({ writeEnabled: false }));
    expect(f).not.toHaveBeenCalled();
  });
  it("posts, patches, arms justRatedPath, toasts without entry_id", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const a = item("a.mp3", { rating: 1 });
    const s = installState({ allItems: [a], filteredItems: [a], currentIndex: 0 });
    vi.stubGlobal("document", {
      getElementById: () => null,
      querySelector: () => null,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, rating: 5 }) }))
    );
    const h = hooks();
    setRating(5, h);
    await vi.advanceTimersByTimeAsync(0);
    expect(s.allItems[0].rating).toBe(5);
    expect(s.justRatedPath).toBe("a.mp3");
    expect(h.toast).toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(5000);
    expect(s.justRatedPath).toBeNull();
    vi.useRealTimers();
    await flush();
  });
});

