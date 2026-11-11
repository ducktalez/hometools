import { describe, it, expect, vi, afterEach } from "vitest";
import { parseWaveformPeaks, initWaveform, generateWaveform, drawWaveform, destroyWaveform } from "../src/waveform";

afterEach(() => {
  destroyWaveform();
  vi.unstubAllGlobals();
});

describe("parseWaveformPeaks", () => {
  it("stereo", () => {
    expect(parseWaveformPeaks({ peaks_l: [1, 2], peaks_r: [3, 4] })).toEqual({ left: [1, 2], right: [3, 4] });
  });
  it("stereo with empty right -> mono-ish", () => {
    expect(parseWaveformPeaks({ peaks_l: [1], peaks_r: [] })).toEqual({ left: [1], right: null });
  });
  it("legacy mono", () => {
    expect(parseWaveformPeaks({ peaks: [5, 6] })).toEqual({ left: [5, 6], right: null });
  });
  it("invalid", () => {
    expect(parseWaveformPeaks(null)).toBeNull();
    expect(parseWaveformPeaks({})).toBeNull();
    expect(parseWaveformPeaks({ peaks: [] })).toBeNull();
    expect(parseWaveformPeaks("x")).toBeNull();
  });
});

function setup(audio = true) {
  const calls: string[] = [];
  const ctx = new Proxy(
    { fillStyle: "", globalAlpha: 1 } as Record<string, unknown>,
    {
      get: (t, k: string) => (k in t ? t[k] : (...a: unknown[]) => calls.push(k + ":" + a.join(","))),
      set: (t, k: string, v) => ((t[k] = v), true),
    }
  );
  const canvas = { offsetWidth: 100, offsetHeight: 20, width: 0, height: 0, getContext: () => ctx };
  const resize: Array<() => void> = [];
  vi.stubGlobal("window", {
    addEventListener: (_e: string, f: () => void) => resize.push(f),
    removeEventListener: vi.fn(),
  });
  vi.stubGlobal("document", { documentElement: {} });
  vi.stubGlobal("getComputedStyle", () => ({ getPropertyValue: () => " #f00 " }));
  const frac = { cur: 0.25, rs: 0.5 };
  initWaveform({
    canvas: canvas as never,
    isAudioMode: audio,
    apiPath: "/api/audio/waveform",
    currentFraction: () => frac.cur,
    resizeFraction: () => frac.rs,
  });
  return { calls, canvas, resize, frac };
}

describe("waveform draw / generate", () => {
  it("initial draw sizes canvas and draws playhead only", () => {
    const c = setup();
    expect(c.canvas.width).toBe(100);
    expect(c.canvas.height).toBe(20);
    expect(c.calls.some((x) => x.startsWith("arc:"))).toBe(true);
    // no peaks -> no bar loop; only 1 base rect (track) and no played rect at 0
    expect(c.calls.filter((x) => x.startsWith("fillRect")).length).toBe(1);
  });

  it("generate fetches peaks and redraws bars with current fraction", async () => {
    const c = setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ peaks_l: [0.5, 1], peaks_r: [0.2, 0.4] }) }))
    );
    c.calls.length = 0;
    generateWaveform("u", "A/b.mp3");
    await new Promise((r) => setTimeout(r, 0));
    expect((fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0]).toBe(
      "/api/audio/waveform?path=A%2Fb.mp3"
    );
    // generate() clears first (1 base rect), then stereo redraw: centre line + 2 bars * (left + right)
    expect(c.calls.filter((x) => x.startsWith("fillRect")).length).toBe(1 + 1 + 4);
  });

  it("no relPath -> no fetch", () => {
    setup();
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    generateWaveform("u");
    expect(f).not.toHaveBeenCalled();
  });

  it("video mode: generate is a no-op", () => {
    setup(false);
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    generateWaveform("u", "x");
    expect(f).not.toHaveBeenCalled();
  });

  it("failed fetch keeps no peaks (still draws)", async () => {
    const c = setup();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false })));
    generateWaveform("u", "x");
    await new Promise((r) => setTimeout(r, 0));
    c.calls.length = 0;
    drawWaveform(0.5);
    // mono-style base track + played rect, no bars
    expect(c.calls.filter((x) => x.startsWith("fillRect")).length).toBe(2);
  });

  it("resize redraws with resizeFraction", () => {
    const c = setup();
    c.calls.length = 0;
    c.resize[0]();
    // played rect present => fraction .5 used
    expect(c.calls.filter((x) => x.startsWith("fillRect")).length).toBe(2);
  });
});


