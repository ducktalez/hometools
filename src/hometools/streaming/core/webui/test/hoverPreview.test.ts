import { describe, it, expect, vi, afterEach } from "vitest";
import { frameStyle, installHoverPreview, destroyHoverPreview, HOVER_DELAY_MS, _clearSpriteCache } from "../src/hoverPreview";
import type { SpriteMeta } from "../src/hoverPreview";

afterEach(() => {
  destroyHoverPreview();
  _clearSpriteCache();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const meta: SpriteMeta = { cols: 10, rows: 4, frame_w: 160, frame_h: 90, interval: 5, count: 40 };

describe("frameStyle", () => {
  it("first frame, same aspect: no offset, background spans the grid", () => {
    const s = frameStyle(meta, 160, 90, 0);
    expect(s.backgroundSize).toBe("1600px 360px");
    expect(s.backgroundPosition).toBe("0px 0px");
  });
  it("scales and moves to column/row of the index", () => {
    const s = frameStyle(meta, 320, 180, 11); // col 1, row 1, scale 2
    expect(s.backgroundSize).toBe("3200px 720px");
    expect(s.backgroundPosition).toBe("-320px -180px");
  });
  it("square box: cover-fit centers horizontally", () => {
    const s = frameStyle(meta, 100, 100, 0); // scale = 100/90
    const dw = 160 * (100 / 90);
    expect(s.backgroundPosition).toBe(String((100 - dw) / 2) + "px 0px");
  });
});

describe("installHoverPreview", () => {
  it("is a no-op when disabled", () => {
    const add = vi.fn();
    vi.stubGlobal("window", { matchMedia: () => ({ matches: true }) });
    vi.stubGlobal("document", { addEventListener: add, removeEventListener: vi.fn() });
    installHoverPreview({ enabled: false });
    expect(add).not.toHaveBeenCalled();
  });
  it("is a no-op without hover capability", () => {
    const add = vi.fn();
    vi.stubGlobal("window", { matchMedia: () => ({ matches: false }) });
    vi.stubGlobal("document", { addEventListener: add, removeEventListener: vi.fn() });
    installHoverPreview({ enabled: true });
    expect(add).not.toHaveBeenCalled();
  });
  it("hover -> overlay after delay, leave -> removed; destroy removes listeners", async () => {
    vi.useFakeTimers();
    const handlers: Record<string, (e: unknown) => void> = {};
    const removed: string[] = [];
    vi.stubGlobal("window", { matchMedia: () => ({ matches: true }) });
    const overlay = { style: {} as Record<string, string>, className: "", remove: vi.fn() };
    vi.stubGlobal("document", {
      addEventListener: (n: string, h: (e: unknown) => void) => (handlers[n] = h),
      removeEventListener: (n: string) => removed.push(n),
      createElement: () => overlay,
    });
    vi.stubGlobal("Image", class {
      onload: (() => void) | null = null;
      set src(_v: string) {
        setTimeout(() => this.onload && this.onload(), 0);
      }
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(meta) }))
    );
    const wrap = {
      dataset: { previewPath: "a/b.mp4" },
      clientWidth: 160,
      clientHeight: 90,
      appendChild: vi.fn(),
      contains: () => false,
    };
    installHoverPreview({ enabled: true });
    handlers.mouseover({ target: { closest: () => wrap } });
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS + 10);
    expect(wrap.appendChild).toHaveBeenCalledWith(overlay);
    expect(overlay.className).toBe("hover-preview");
    handlers.mouseout({ relatedTarget: null });
    expect(overlay.remove).toHaveBeenCalled();
    destroyHoverPreview();
    expect(removed).toEqual(expect.arrayContaining(["mouseover", "mouseout"]));
  });
});

