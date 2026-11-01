import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { buildRealIdxMap, startWindowedRender, appendTrackBatch, ensureRenderedTo, stopRenderObserver } from "../src/trackRenderWindow";
import type { RenderWindowHooks } from "../src/trackRenderWindow";

afterEach(() => vi.unstubAllGlobals());

describe("buildRealIdxMap", () => {
  it("placeholders and debug rows map to -1, real rows count up", () => {
    expect(buildRealIdxMap([{}, { _missing: true }, {}, { _debugReason: "x" }, {}])).toEqual([0, -1, 1, -1, 2]);
  });
});

function setup(count: number, batchSize: number) {
  const inserted: string[] = [];
  const sentinel = { parentNode: null as unknown, insertAdjacentHTML: (_w: string, html: string) => inserted.push(html), setAttribute: vi.fn(), style: {} as Record<string, string>, className: "" };
  const trackList = {
    appendChild: (el: unknown) => {
      (el as { parentNode: unknown }).parentNode = trackList;
    },
    removeChild: (el: unknown) => {
      (el as { parentNode: unknown }).parentNode = null;
    },
    insertAdjacentHTML: (_w: string, html: string) => inserted.push(html),
  };
  vi.stubGlobal("document", { createElement: () => sentinel });
  vi.stubGlobal("IntersectionObserver", undefined);
  const items = Array.from({ length: count }, (_, i) => item("t" + i));
  const h: RenderWindowHooks = {
    trackList: () => trackList as unknown as HTMLElement,
    batchSize,
    rowCtx: () =>
      ({
        escHtml: (s: unknown) => String(s),
        fmtTime: () => "0:00",
        showOrig: false,
        currentIndex: -1,
        bpmCalcEnabled: false,
        trackViewMode: "list",
        isVideoMode: false,
        metadataEditEnabled: false,
        playlistsEnabled: false,
        itemNoun: "song",
        bpmMin: 0,
        bpmMax: 0,
        dupePaths: null,
        dupeSafety: null,
        filePlaceholder: "",
        ic: { folderPlay: "", trash: "", dl: "", pin: "", edit: "", playlist: "", queue: "", dots: "" },
        renderInlineRating: () => "",
        renderMoveWidget: () => "",
      }) as never,
    decorateRows: vi.fn(),
    maybeInitPlaylistDragDrop: vi.fn(),
    wireDelegation: vi.fn(),
  };
  return { h, items, inserted, sentinel };
}

describe("windowed render (no IntersectionObserver -> renders all synchronously)", () => {
  it("renders every batch, wires delegation once, DnD on first and last batch", () => {
    installState();
    const { h, items, sentinel } = setup(5, 2);
    // rowCtx is too sparse for real rows -> stub rows via spy on decorate count instead
    expect(() => startWindowedRender(items, h)).not.toThrow();
    expect(h.wireDelegation).toHaveBeenCalledTimes(1);
    expect(h.decorateRows).toHaveBeenCalledTimes(3); // 2+2+1
    expect(h.maybeInitPlaylistDragDrop).toHaveBeenCalledTimes(2); // first batch + last batch
    // sentinel removed once everything is rendered
    expect(sentinel.parentNode).toBeNull();
  });

  it("empty window: append is a no-op that stops the observer", () => {
    installState();
    const { h } = setup(0, 2);
    startWindowedRender([], h);
    appendTrackBatch(h);
    expect(h.decorateRows).not.toHaveBeenCalled();
  });

  it("ensureRenderedTo renders up to the requested real index", () => {
    installState();
    const { h, items } = setup(6, 2);
    // keep first batch only by making observer path exist
    vi.stubGlobal("IntersectionObserver", class { observe() {} disconnect() {} });
    startWindowedRender(items, h);
    expect(h.decorateRows).toHaveBeenCalledTimes(1);
    ensureRenderedTo(4, h);
    expect(h.decorateRows).toHaveBeenCalledTimes(3);
    stopRenderObserver(h);
  });
});


