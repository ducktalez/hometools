import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { setInlineRating } from "../src/rating";
import type { RatingHooks } from "../src/rating";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

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

function stubNet(body: object) {
  vi.stubGlobal("document", { getElementById: () => null, querySelector: () => null });
  const f = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(body) }));
  vi.stubGlobal("fetch", f);
  return f;
}

describe("setInlineRating", () => {
  it("no-op when write disabled or row missing", () => {
    installState({ filteredItems: [item("a.mp3")] });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    setInlineRating(0, 5, hooks({ writeEnabled: false }));
    setInlineRating(3, 5, hooks());
    expect(f).not.toHaveBeenCalled();
  });

  it("in playlist: refilters, relocates playing track, arms justRatedPath", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const a = item("a.mp3", { rating: 1 });
    const b = item("b.mp3", { rating: 2 });
    const s = installState({ allItems: [a, b], filteredItems: [a, b], currentIndex: 1, inPlaylist: true });
    stubNet({ ok: true, rating: 5 });
    const h = hooks({
      applyFilter: vi.fn(() => {
        s.filteredItems = [b, s.filteredItems[0]]; /* re-sort: b first */
      }),
    });
    setInlineRating(0, 5, h);
    await vi.advanceTimersByTimeAsync(0);
    expect(h.applyFilter).toHaveBeenCalledWith(true);
    expect(s.currentIndex).toBe(0); /* playing b.mp3 relocated */
    expect(s.allItems[0].rating).toBe(5);
    expect(s.justRatedPath).toBe("a.mp3");
    expect(h.markActive).toHaveBeenCalled();
    expect(h.toast).toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(5000);
    expect(s.justRatedPath).toBeNull();
  });

  it("outside playlist: no refilter; weighted shuffle rebuilt", async () => {
    const a = item("a.mp3");
    const s = installState({ allItems: [a], filteredItems: [a], currentIndex: 0, inPlaylist: false, shuffleMode: "weighted" });
    stubNet({ ok: true, rating: 3 });
    const h = hooks();
    setInlineRating(0, 3, h);
    await new Promise((r) => setTimeout(r, 0));
    expect(h.applyFilter).not.toHaveBeenCalled();
    expect(h.rebuildShuffleQueue).toHaveBeenCalledWith(0);
    expect(s.filteredItems[0].rating).toBe(3);
  });

  it("ignores failed response", async () => {
    const a = item("a.mp3", { rating: 1 });
    installState({ allItems: [a], filteredItems: [a] });
    stubNet({ ok: false });
    const h = hooks();
    setInlineRating(0, 4, h);
    await new Promise((r) => setTimeout(r, 0));
    expect(a.rating).toBe(1);
    expect(h.toast).not.toHaveBeenCalled();
  });
});

