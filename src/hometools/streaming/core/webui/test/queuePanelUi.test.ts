import { describe, it, expect, vi, afterEach } from "vitest";
import { queuePanelMaxHeight, clampQueueHeight, initQueuePeekHandle } from "../src/queuePanelUi";

afterEach(() => vi.unstubAllGlobals());

describe("queuePanelMaxHeight", () => {
  it("full available space when no user height", () => {
    expect(queuePanelMaxHeight(1000, 56, 80, null, 220)).toBe(1000 - 56 - 80 - 8);
  });
  it("user height capped by available, floored at min", () => {
    expect(queuePanelMaxHeight(1000, 56, 80, 300, 220)).toBe(300);
    expect(queuePanelMaxHeight(1000, 56, 80, 5000, 220)).toBe(856);
    expect(queuePanelMaxHeight(300, 56, 80, null, 220)).toBe(220);
  });
});

describe("clampQueueHeight", () => {
  it("grows up, clamps to [min, available]", () => {
    expect(clampQueueHeight(300, 50, 800, 220)).toBe(350);
    expect(clampQueueHeight(300, 900, 800, 220)).toBe(800);
    expect(clampQueueHeight(300, -500, 800, 220)).toBe(220);
    expect(clampQueueHeight(300, 50, 100, 220)).toBe(220);
  });
});

describe("initQueuePeekHandle", () => {
  type L = (e?: unknown) => void;
  function setup() {
    const h: Record<string, L> = {};
    const doc: Record<string, L> = {};
    vi.stubGlobal("document", {
      addEventListener: (ev: string, f: L) => (doc[ev] = f),
      removeEventListener: (ev: string) => delete doc[ev],
    });
    let open = false;
    const o = {
      handle: { addEventListener: (ev: string, f: L) => (h[ev] = f) } as unknown as HTMLElement,
      isOpen: () => open,
      open: vi.fn(() => (open = true)),
      toggle: vi.fn(),
    };
    initQueuePeekHandle(o);
    return { h, doc, o };
  }
  it("null handle is no-op", () => {
    initQueuePeekHandle({ handle: null, isOpen: () => false, open: vi.fn(), toggle: vi.fn() });
  });
  it("click toggles", () => {
    const { h, o } = setup();
    h.click();
    expect(o.toggle).toHaveBeenCalledTimes(1);
  });
  it("drag up opens once; following click does not toggle", () => {
    const { h, doc, o } = setup();
    h.mousedown({ clientY: 500 });
    doc.mousemove({ clientY: 495 });
    expect(o.open).not.toHaveBeenCalled();
    doc.mousemove({ clientY: 480 });
    expect(o.open).toHaveBeenCalledTimes(1);
    doc.mouseup();
    expect(doc.mousemove).toBeUndefined();
    h.click();
    expect(o.toggle).not.toHaveBeenCalled();
    h.click();
    expect(o.toggle).toHaveBeenCalledTimes(1);
  });
});

