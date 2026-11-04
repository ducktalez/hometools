import { describe, it, expect, vi, afterEach } from "vitest";
import { queuePanelMaxHeight, clampQueueHeight, initQueuePeekHandle } from "../src/queuePanelUi";
import { openQueuePanel, closeQueuePanel, toggleQueuePanel } from "../src/queuePanelUi";
import type { QueuePanelHooks } from "../src/queuePanelUi";

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

describe("queue panel open/close/toggle", () => {
  it("open sets state, renders, marks visible, closes lyrics", () => {
    const t = panelHooks(true);
    openQueuePanel(t.h);
    expect(t.isOpen()).toBe(true);
    expect(t.h.closeLyrics).toHaveBeenCalled();
    expect(t.h.sync).toHaveBeenCalled();
    expect(t.h.render).toHaveBeenCalled();
    expect(t.panel.set.has("visible")).toBe(true);
    expect(t.peek.set.has("queue-active")).toBe(true);
  });
  it("open without panel is no-op", () => {
    const t = panelHooks(false, false);
    openQueuePanel(t.h);
    expect(t.isOpen()).toBe(false);
  });
  it("close resets state and destroys dnd", () => {
    const t = panelHooks();
    openQueuePanel(t.h);
    closeQueuePanel(t.h);
    expect(t.isOpen()).toBe(false);
    expect(t.h.destroyDnd).toHaveBeenCalled();
    expect(t.panel.set.has("visible")).toBe(false);
    expect(t.peek.set.has("queue-active")).toBe(false);
  });
  it("toggle flips", () => {
    const t = panelHooks();
    toggleQueuePanel(t.h);
    expect(t.isOpen()).toBe(true);
    toggleQueuePanel(t.h);
    expect(t.isOpen()).toBe(false);
  });
});

function panelHooks(lyricsOpen = false, withPanel = true) {
  const cls = () => {
    const set = new Set<string>();
    return { set, classList: { add: (c: string) => void set.add(c), remove: (c: string) => void set.delete(c) } };
  };
  const panel = cls();
  const peek = cls();
  let open = false;
  const h = {
    ensureDom: vi.fn(),
    getPanel: () => (withPanel ? (panel as unknown as HTMLElement) : null),
    getPeekHandle: () => peek as unknown as HTMLElement,
    isOpen: () => open,
    setOpen: (v: boolean) => (open = v),
    lyricsOpen: () => lyricsOpen,
    closeLyrics: vi.fn(),
    sync: vi.fn(),
    render: vi.fn(),
    destroyDnd: vi.fn(),
  } as unknown as QueuePanelHooks;
  return { h, panel, peek, isOpen: () => open };
}
