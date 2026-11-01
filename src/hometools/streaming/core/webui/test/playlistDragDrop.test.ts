import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { dropIndex, initPlaylistDragDrop, destroyPlaylistDragDrop } from "../src/playlistDragDrop";

afterEach(() => vi.unstubAllGlobals());

describe("dropIndex", () => {
  it("above/below, adjusted when dragging downwards", () => {
    expect(dropIndex(0, 2, true)).toBe(1);
    expect(dropIndex(0, 2, false)).toBe(2);
    expect(dropIndex(3, 1, true)).toBe(1);
    expect(dropIndex(3, 1, false)).toBe(2);
    expect(dropIndex(1, 1, false)).toBe(1); // no-op
  });
});

type L = (e?: unknown) => void;

function stubDom(itemCount: number) {
  const tl: Record<string, L> = {};
  const doc: Record<string, L> = {};
  const removed: string[] = [];
  const trackList = {
    querySelectorAll: (sel: string) => (sel.startsWith(".track-item") ? new Array(itemCount).fill({}) : []),
    addEventListener: (ev: string, f: L) => (tl[ev] = f),
    removeEventListener: (ev: string) => {
      removed.push("tl:" + ev);
      delete tl[ev];
    },
  };
  vi.stubGlobal("document", {
    getElementById: (id: string) => (id === "track-list" ? trackList : null),
    addEventListener: (ev: string, f: L) => (doc[ev] = f),
    removeEventListener: (ev: string) => {
      removed.push("doc:" + ev);
      delete doc[ev];
    },
  });
  return { tl, doc, removed };
}

describe("initPlaylistDragDrop lifecycle", () => {
  it("no-op for < 2 items", () => {
    installState();
    const d = stubDom(1);
    initPlaylistDragDrop({ reorder: vi.fn() });
    expect(Object.keys(d.tl)).toEqual([]);
    expect(Object.keys(d.doc)).toEqual([]);
  });

  it("attaches listeners; destroy removes them all (named handlers)", () => {
    installState({ filteredItems: [item("a"), item("b")] });
    const d = stubDom(2);
    initPlaylistDragDrop({ reorder: vi.fn() });
    expect(Object.keys(d.tl).sort()).toEqual(["mousedown", "touchcancel", "touchend", "touchmove", "touchstart"]);
    expect(Object.keys(d.doc).sort()).toEqual(["mousemove", "mouseup"]);
    destroyPlaylistDragDrop();
    expect(Object.keys(d.tl)).toEqual([]);
    expect(Object.keys(d.doc)).toEqual([]);
    expect(d.removed.length).toBe(7);
    destroyPlaylistDragDrop(); // idempotent
    expect(d.removed.length).toBe(7);
  });

  it("re-init cleans previous listeners first", () => {
    installState();
    const d = stubDom(2);
    initPlaylistDragDrop({ reorder: vi.fn() });
    initPlaylistDragDrop({ reorder: vi.fn() });
    expect(d.removed.length).toBe(7);
    destroyPlaylistDragDrop();
  });
});

