import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { wireTrackListDelegation, unwireTrackListDelegation } from "../src/trackListDelegation";
import type { TrackListHooks } from "../src/trackListDelegation";

afterEach(() => {
  unwireTrackListDelegation();
  vi.unstubAllGlobals();
});

function hooks(over: Partial<TrackListHooks> = {}): TrackListHooks {
  const fn = () => vi.fn();
  return {
    metadataEditEnabled: true,
    playlistsEnabled: true,
    itemNoun: "song",
    setInlineRating: fn(),
    openBpmAdjustMenu: fn(),
    deleteTrackDownload: fn(),
    cancelDownload: fn(),
    downloadTrack: fn(),
    toggleFavorite: fn(),
    openEditModal: fn(),
    openPlaylistModalFor: fn(),
    removeFromQueue: fn(),
    addToQueue: fn(),
    showToast: fn(),
    moveFileToFolder: fn(),
    deleteTrackFromList: fn(),
    openTrackCtxMenu: fn(),
    revealInExplorer: fn(),
    playTrack: fn(),
    selectTrackRow: fn(),
    saveInlineTableEdit: fn(),
    ...over,
  };
}

/** Fake element whose closest(sel) matches only `sel` mapped in `hits`. */
function target(hits: Record<string, Record<string, unknown>>) {
  return {
    closest: (sel: string) => {
      const k = Object.keys(hits).find((h) => sel.includes(h));
      return k ? { dataset: {}, classList: { contains: () => false }, ...hits[k] } : null;
    },
  };
}

function setup(h: TrackListHooks) {
  const l: Record<string, (e: unknown) => void> = {};
  const removed: string[] = [];
  const tl = {
    addEventListener: (ev: string, f: (e: unknown) => void) => (l[ev] = f),
    removeEventListener: (ev: string) => removed.push(ev),
  };
  wireTrackListDelegation(tl as unknown as HTMLElement, h);
  return { l, removed, tl };
}

const ev = (t: unknown) => ({ target: t, stopPropagation: vi.fn(), preventDefault: vi.fn(), clientX: 0, clientY: 0 });

describe("wireTrackListDelegation", () => {
  it("rating star toggles to 0 when clicking the active rating", () => {
    installState({ filteredItems: [item("a", { rating: 3 })] });
    const h = hooks();
    const { l } = setup(h);
    l.click(ev(target({ ".track-inline-rating-star": { dataset: { index: "0", star: "3" } } })));
    expect(h.setInlineRating).toHaveBeenCalledWith(0, 0);
    l.click(ev(target({ ".track-inline-rating-star": { dataset: { index: "0", star: "4" } } })));
    expect(h.setInlineRating).toHaveBeenLastCalledWith(0, 4);
  });

  it("download button routes by state class", () => {
    installState();
    const h = hooks();
    const { l } = setup(h);
    const mk = (cls: string) => ({ ".track-dl-btn": { dataset: { streamUrl: "/s", title: "T" }, classList: { contains: (c: string) => c === cls } } });
    l.click(ev(target(mk("cached"))));
    expect(h.deleteTrackDownload).toHaveBeenCalled();
    l.click(ev(target(mk("downloading"))));
    expect(h.cancelDownload).toHaveBeenCalled();
    l.click(ev(target(mk("none"))));
    expect(h.downloadTrack).toHaveBeenCalledWith("/s", "T", expect.anything(), expect.objectContaining({ mediaType: "song" }));
  });

  it("queue button adds when absent, removes when present", () => {
    const a = item("a");
    installState({ filteredItems: [a], userQueue: [] });
    const h = hooks();
    const { l } = setup(h);
    const q = { ".track-queue-btn": { dataset: { relativePath: "a", index: "0" } } };
    l.click(ev(target(q)));
    expect(h.addToQueue).toHaveBeenCalledWith(a);
    installState({ filteredItems: [a], userQueue: [a] });
    l.click(ev(target(q)));
    expect(h.removeFromQueue).toHaveBeenCalledWith(0);
    expect(h.showToast).toHaveBeenCalledWith("Aus Warteschlange entfernt");
  });

  it("edit button gated by metadataEditEnabled", () => {
    installState();
    const off = hooks({ metadataEditEnabled: false });
    const { l } = setup(off);
    l.click(ev(target({ ".track-edit-btn": { dataset: { index: "2" } } })));
    expect(off.openEditModal).not.toHaveBeenCalled();
  });

  it("row click: hover device selects, touch device plays", () => {
    installState();
    const h = hooks();
    const { l } = setup(h);
    vi.stubGlobal("window", { getSelection: () => ({ toString: () => "" }), matchMedia: () => ({ matches: true }) });
    const row = { ".track-item": { dataset: { index: "5" } } };
    l.click(ev(target(row)));
    expect(h.selectTrackRow).toHaveBeenCalledWith(5);
    vi.stubGlobal("window", { getSelection: () => ({ toString: () => "" }), matchMedia: () => ({ matches: false }) });
    l.click(ev(target(row)));
    expect(h.playTrack).toHaveBeenCalledWith(5);
  });

  it("re-wire removes all five previous listeners (incl. dblclick)", () => {
    installState();
    const h = hooks();
    const first = setup(h);
    expect(Object.keys(first.l).sort()).toEqual(["change", "click", "dblclick", "focusout", "keydown"]);
    const second = setup(h);
    // second wire detached the listeners from the first list
    expect(first.removed.sort()).toEqual(["change", "click", "dblclick", "focusout", "keydown"]);
    expect(second.removed.length).toBe(0);
    unwireTrackListDelegation();
    expect(second.removed.sort()).toEqual(["change", "click", "dblclick", "focusout", "keydown"]);
  });

  it("keydown Enter blurs editable, Escape cancels", () => {
    installState();
    const h = hooks();
    const { l } = setup(h);
    const editable = { dataset: {} as Record<string, string>, blur: vi.fn() };
    const e = (key: string) => ({ key, preventDefault: vi.fn(), target: { closest: () => editable } });
    l.keydown(e("Enter"));
    expect(editable.blur).toHaveBeenCalledTimes(1);
    l.keydown(e("Escape"));
    expect(editable.dataset.cancelled).toBe("1");
    expect(editable.blur).toHaveBeenCalledTimes(2);
  });
});


