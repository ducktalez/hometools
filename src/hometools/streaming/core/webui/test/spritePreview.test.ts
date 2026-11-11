import { describe, it, expect, vi, afterEach } from "vitest";
import { initSpritePreview, loadSpriteData, spriteFrameRect, type SpriteMeta } from "../src/spritePreview";

afterEach(() => vi.unstubAllGlobals());

const meta: SpriteMeta = { cols: 5, rows: 4, frame_w: 160, frame_h: 90, count: 18, interval: 10 };

describe("spriteFrameRect", () => {
  it("maps time to col/row", () => {
    expect(spriteFrameRect(meta, 0)).toEqual({ sx: 0, sy: 0, sw: 160, sh: 90 });
    expect(spriteFrameRect(meta, 70)).toEqual({ sx: 320, sy: 90, sw: 160, sh: 90 });
  });
  it("clamps to last frame and 0", () => {
    expect(spriteFrameRect(meta, 9999)).toEqual({ sx: 2 * 160, sy: 3 * 90, sw: 160, sh: 90 });
    expect(spriteFrameRect(meta, -5).sx).toBe(0);
  });
});

function setup(video = true) {
  const h: Record<string, (e: unknown) => void> = {};
  const classes = new Set<string>();
  const drawImage = vi.fn();
  const track = {
    addEventListener: (e: string, f: (e: unknown) => void) => (h[e] = f),
    getBoundingClientRect: () => ({ left: 100, width: 200 }),
  };
  const preview = { style: {} as Record<string, string>, classList: { add: (c: string) => classes.add(c), remove: (c: string) => classes.delete(c) } };
  const canvas = { width: 0, height: 0, getContext: () => ({ drawImage }) };
  const timeEl = { textContent: "" };
  const player = { duration: 100 };
  initSpritePreview({
    player: player as never,
    isVideoMode: video,
    track: track as never,
    preview: preview as never,
    canvas: canvas as never,
    timeEl: timeEl as never,
    fmtTime: (s) => "t" + Math.round(s),
  });
  return { h, classes, drawImage, preview, canvas, timeEl };
}

async function loadMeta() {
  const imgs: Array<{ onload?: () => void; src?: string }> = [];
  vi.stubGlobal("Image", function (this: { onload?: () => void; src?: string }) {
    imgs.push(this);
  });
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(meta) })));
  loadSpriteData("S/a.mp4");
  await new Promise((r) => setTimeout(r, 0));
  imgs[0].onload!();
  return imgs[0];
}

describe("spritePreview", () => {
  it("mousemove before sprite loaded: nothing", () => {
    const c = setup();
    c.h.mousemove({ clientX: 150 });
    expect(c.classes.has("visible")).toBe(false);
  });

  it("after load: shows preview, time, draws frame; leave hides", async () => {
    const c = setup();
    const img = await loadMeta();
    expect(img.src).toBe("/thumb?path=S%2Fa.mp4&size=sprite");
    c.h.mousemove({ clientX: 200 }); // ratio .5 -> 50s -> idx 5 -> col0,row1
    expect(c.classes.has("visible")).toBe(true);
    expect(c.preview.style.left).toBe("50%");
    expect(c.timeEl.textContent).toBe("t50");
    expect(c.drawImage).toHaveBeenCalledWith(img, 0, 90, 160, 90, 0, 0, 160, 90);
    c.h.mouseleave({});
    expect(c.classes.has("visible")).toBe(false);
  });

  it("new loadSpriteData resets previous sprite", async () => {
    const c = setup();
    await loadMeta();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false })));
    loadSpriteData("S/b.mp4");
    c.h.mousemove({ clientX: 200 });
    expect(c.classes.has("visible")).toBe(false);
  });

  it("audio mode: no listeners, no fetch", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const c = setup(false);
    expect(c.h.mousemove).toBeUndefined();
    loadSpriteData("x");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});


