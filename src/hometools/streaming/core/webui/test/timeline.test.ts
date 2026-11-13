import { describe, it, expect, vi, afterEach } from "vitest";
import { seekFraction, effectiveDuration, initTimeline } from "../src/timeline";

afterEach(() => vi.unstubAllGlobals());

describe("timeline", () => {
  it("seekFraction clamps", () => {
    expect(seekFraction(50, 0, 100)).toBe(0.5);
    expect(seekFraction(-10, 0, 100)).toBe(0);
    expect(seekFraction(500, 0, 100)).toBe(1);
  });
  it("effectiveDuration: player first, catalog fallback", () => {
    vi.stubGlobal("document", { hidden: false });
    expect(effectiveDuration({ player: { duration: 120 } as HTMLMediaElement, getItemDuration: () => 99 })).toBe(120);
    expect(effectiveDuration({ player: { duration: NaN } as HTMLMediaElement, getItemDuration: () => 99 })).toBe(99);
    expect(effectiveDuration({ player: { duration: NaN } as HTMLMediaElement, getItemDuration: () => 0 })).toBe(0);
  });
  it("loadedmetadata stores duration and updates labels", () => {
    vi.stubGlobal("document", { hidden: false, addEventListener: vi.fn() });
    vi.stubGlobal("window", { addEventListener: vi.fn() });
    const ev: Record<string, () => void> = {};
    const player = { duration: 61, currentTime: 0, addEventListener: (t: string, f: () => void) => (ev[t] = f) };
    const bar = { max: "", value: "", addEventListener: vi.fn() };
    const timeDur = { textContent: "" };
    const setItemDuration = vi.fn();
    initTimeline({
      player: player as unknown as HTMLMediaElement,
      progressBar: bar as unknown as HTMLInputElement,
      timeCur: { textContent: "" } as HTMLElement,
      timeDur: timeDur as HTMLElement,
      track: null,
      isVideoPlayer: false,
      crossfadeDuration: 0,
      fmtTime: (s) => "t" + s,
      getItemDuration: () => 0,
      setItemDuration,
      saveProgressNow: vi.fn(),
      saveProgressDebounced: vi.fn(),
      updateSkipIntroBtn: vi.fn(),
      startCrossfade: vi.fn(),
    });
    ev.loadedmetadata();
    expect(setItemDuration).toHaveBeenCalledWith(61);
    expect(timeDur.textContent).toBe("t61");
    expect(bar.max).toBe("61");
  });
});

