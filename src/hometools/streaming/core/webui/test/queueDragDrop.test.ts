import { describe, it, expect, vi, afterEach } from "vitest";
import { queueDropIndex, initQueueDragDrop, destroyQueueDragDrop } from "../src/queueDragDrop";

afterEach(() => {
  destroyQueueDragDrop();
  vi.unstubAllGlobals();
});

describe("queueDropIndex", () => {
  it("above/below with downward adjustment", () => {
    expect(queueDropIndex(0, 2, true)).toBe(1);
    expect(queueDropIndex(0, 2, false)).toBe(2);
    expect(queueDropIndex(3, 1, true)).toBe(1);
    expect(queueDropIndex(3, 1, false)).toBe(2);
  });
});

type L = (e?: unknown) => void;
function stubDom(count: number) {
  const ql: Record<string, L> = {};
  const doc: Record<string, L> = {};
  const removed: string[] = [];
  const list = {
    querySelectorAll: (s: string) => (s === ".queue-item" ? new Array(count).fill({}) : []),
    addEventListener: (ev: string, f: L) => (ql[ev] = f),
    removeEventListener: (ev: string) => {
      removed.push(ev);
      delete ql[ev];
    },
  };
  vi.stubGlobal("document", {
    getElementById: (id: string) => (id === "queue-list" ? list : null),
    addEventListener: (ev: string, f: L) => (doc[ev] = f),
    removeEventListener: (ev: string) => {
      removed.push(ev);
      delete doc[ev];
    },
    body: { classList: { add: vi.fn(), remove: vi.fn() } },
  });
  return { ql, doc, removed };
}

describe("initQueueDragDrop lifecycle", () => {
  it("no-op below 2 items", () => {
    const d = stubDom(1);
    initQueueDragDrop({ move: vi.fn(), render: vi.fn() });
    expect(Object.keys(d.ql)).toEqual([]);
  });

  it("attaches 6 listeners; destroy removes them; re-init cleans first", () => {
    const d = stubDom(3);
    const h = { move: vi.fn(), render: vi.fn() };
    initQueueDragDrop(h);
    expect(Object.keys(d.ql).sort()).toEqual(["mousedown", "touchend", "touchmove", "touchstart"]);
    expect(Object.keys(d.doc).sort()).toEqual(["mousemove", "mouseup"]);
    initQueueDragDrop(h);
    expect(d.removed.length).toBe(6);
    destroyQueueDragDrop();
    expect(d.removed.length).toBe(12);
    expect(Object.keys(d.ql)).toEqual([]);
    destroyQueueDragDrop();
    expect(d.removed.length).toBe(12);
  });
});

