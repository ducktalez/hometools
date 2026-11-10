import { describe, it, expect, vi, afterEach } from "vitest";
import { initFullscreenButton, initCastButton } from "../src/videoButtons";

afterEach(() => vi.unstubAllGlobals());

function btn() {
  const h: Record<string, (e: unknown) => void> = {};
  const classes = new Set<string>();
  return {
    hidden: true,
    h,
    classes,
    classList: { add: (c: string) => classes.add(c), remove: (c: string) => classes.delete(c) },
    addEventListener: (e: string, f: (e: unknown) => void) => (h[e] = f),
  };
}
const ev = { stopPropagation: vi.fn() };

describe("fullscreen button", () => {
  it("requests fullscreen on overlay", () => {
    vi.stubGlobal("document", { fullscreenEnabled: true });
    const b = btn();
    const overlay = { requestFullscreen: vi.fn(() => Promise.resolve()) };
    initFullscreenButton({ button: b as never, overlay: overlay as never, player: {} as never });
    b.h.click(ev);
    expect(overlay.requestFullscreen).toHaveBeenCalled();
  });

  it("falls back to webkitEnterFullscreen when request rejects", async () => {
    vi.stubGlobal("document", { fullscreenEnabled: true });
    const b = btn();
    const overlay = { requestFullscreen: vi.fn(() => Promise.reject(new Error("x"))) };
    const player = { webkitEnterFullscreen: vi.fn() };
    initFullscreenButton({ button: b as never, overlay: overlay as never, player: player as never });
    b.h.click(ev);
    await Promise.resolve();
    await Promise.resolve();
    expect(player.webkitEnterFullscreen).toHaveBeenCalled();
  });

  it("iOS: no fullscreen API -> webkitEnterFullscreen", () => {
    vi.stubGlobal("document", { fullscreenEnabled: false });
    const b = btn();
    const player = { webkitEnterFullscreen: vi.fn() };
    initFullscreenButton({ button: b as never, overlay: {} as never, player: player as never });
    b.h.click(ev);
    expect(player.webkitEnterFullscreen).toHaveBeenCalled();
  });

  it("no button -> no-op", () => {
    expect(() => initFullscreenButton({ button: null, overlay: null, player: {} as never })).not.toThrow();
  });
});

describe("cast button", () => {
  it("Remote Playback: availability toggles hidden, click prompts, connect marks active", () => {
    vi.stubGlobal("window", {});
    const b = btn();
    let availCb: (a: boolean) => void = () => {};
    const rl: Record<string, () => void> = {};
    const player = {
      tagName: "VIDEO",
      remote: {
        watchAvailability: (cb: (a: boolean) => void) => {
          availCb = cb;
          return Promise.resolve(1);
        },
        prompt: vi.fn(() => Promise.resolve()),
        addEventListener: (e: string, f: () => void) => (rl[e] = f),
      },
    };
    initCastButton({ button: b as never, player: player as never });
    availCb(true);
    expect(b.hidden).toBe(false);
    availCb(false);
    expect(b.hidden).toBe(true);
    b.h.click(ev);
    expect(player.remote.prompt).toHaveBeenCalled();
    rl.connect();
    expect(b.classes.has("active")).toBe(true);
    rl.disconnect();
    expect(b.classes.has("active")).toBe(false);
  });

  it("AirPlay fallback", () => {
    vi.stubGlobal("window", { WebKitPlaybackTargetAvailabilityEvent: function () {} });
    const b = btn();
    const pl: Record<string, (e: unknown) => void> = {};
    const player = {
      tagName: "VIDEO",
      addEventListener: (e: string, f: (e: unknown) => void) => (pl[e] = f),
      webkitShowPlaybackTargetPicker: vi.fn(),
    };
    initCastButton({ button: b as never, player: player as never });
    pl.webkitplaybacktargetavailabilitychanged({ availability: "available" });
    expect(b.hidden).toBe(false);
    b.h.click(ev);
    expect(player.webkitShowPlaybackTargetPicker).toHaveBeenCalled();
  });

  it("no support or audio element: stays hidden, no listeners", () => {
    vi.stubGlobal("window", {});
    const b = btn();
    initCastButton({ button: b as never, player: { tagName: "VIDEO", addEventListener: vi.fn() } as never });
    expect(b.hidden).toBe(true);
    expect(b.h.click).toBeUndefined();
    const b2 = btn();
    initCastButton({ button: b2 as never, player: { tagName: "AUDIO" } as never });
    expect(b2.h.click).toBeUndefined();
  });
});

