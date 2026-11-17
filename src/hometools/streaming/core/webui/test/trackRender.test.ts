import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { renderTracks, renderGuardKey, resetRenderGuard } from "../src/trackRender";
import type { RenderTracksHooks } from "../src/trackRender";

afterEach(() => vi.unstubAllGlobals());

function fakeList(children = 0) {
  return {
    children: { length: children },
    innerHTML: "",
    classList: { toggle: vi.fn() },
  } as unknown as HTMLElement;
}

function hooks(over: Partial<RenderTracksHooks> = {}): RenderTracksHooks {
  return {
    itemNoun: "track",
    debugFilter: false,
    trackList: fakeList(),
    trackCount: { textContent: "" } as HTMLElement,
    searchInput: null,
    sortField: null,
    getFilter: () => ({ rating: 0, fav: false, genre: "" }),
    effectiveThreshold: () => 0,
    showHidden: () => true,
    stopRenderObserver: vi.fn(),
    startWindowedRender: vi.fn(),
    markActive: vi.fn(),
    openTrackPicker: vi.fn(),
    ...over,
  };
}

describe("renderGuardKey", () => {
  const f = { rating: 0, fav: false, genre: "" };
  it("changes with any visible input", () => {
    const base = renderGuardKey("p", "a", "", "", 3, f, 0, true, null);
    expect(renderGuardKey("p", "a", "", "", 4, f, 0, true, null)).not.toBe(base);
    expect(renderGuardKey("p", "a", "x", "", 3, f, 0, true, null)).not.toBe(base);
    expect(renderGuardKey("p", "a", "", "", 3, { ...f, fav: true }, 0, true, null)).not.toBe(base);
    expect(renderGuardKey("p", "a", "", "", 3, f, 0, true, "x.mp3")).not.toBe(base);
    expect(renderGuardKey("p", "a", "", "", 3, f, 0, true, null)).toBe(base);
  });
});

describe("renderTracks", () => {
  it("sets filteredItems, count label, hands over to windowed render", () => {
    resetRenderGuard();
    const s = installState();
    const h = hooks();
    const t = [item("a"), item("b")];
    renderTracks(t, false, h);
    expect(s.filteredItems).toBe(t);
    expect(h.trackCount!.textContent).toBe("2 tracks");
    expect(h.stopRenderObserver).toHaveBeenCalled();
    expect(h.startWindowedRender).toHaveBeenCalledWith(t);
  });

  it("singular noun for one item; hidden-shown items not counted", () => {
    resetRenderGuard();
    installState();
    const h = hooks();
    renderTracks([item("a"), { ...item("b"), _hiddenShown: true } as never], false, h);
    expect(h.trackCount!.textContent).toBe("1 track");
  });

  it("render guard skips rebuild when nothing changed, force overrides", () => {
    resetRenderGuard();
    installState();
    const list = fakeList(0);
    const h = hooks({ trackList: list });
    const t = [item("a")];
    renderTracks(t, false, h);
    (list.children as { length: number }).length = 1; /* DOM now populated */
    renderTracks(t, false, h);
    expect(h.startWindowedRender).toHaveBeenCalledTimes(1);
    expect(h.markActive).toHaveBeenCalledTimes(1);
    renderTracks(t, true, h);
    expect(h.startWindowedRender).toHaveBeenCalledTimes(2);
  });

  it("debug filter keeps debug-dimmed items out of filteredItems", () => {
    resetRenderGuard();
    const s = installState();
    const h = hooks({ debugFilter: true });
    renderTracks([item("a"), { ...item("b"), _debugReason: "x" } as never], false, h);
    expect(s.filteredItems).toHaveLength(1);
  });

  it("empty list -> hint; empty manual playlist -> add button", () => {
    resetRenderGuard();
    installState();
    const h = hooks();
    renderTracks([], false, h);
    expect(h.trackList.innerHTML).toContain("No matching items");
    expect(h.startWindowedRender).not.toHaveBeenCalled();

    resetRenderGuard();
    installState({
      inPlaylist: true,
      currentPlaylistId: "m",
      userPlaylists: [{ id: "m", name: "M", items: [] }],
    });
    vi.stubGlobal("document", { getElementById: () => null });
    const h2 = hooks();
    renderTracks([], false, h2);
    expect(h2.trackList.innerHTML).toContain("btn-add-tracks");
  });
});

