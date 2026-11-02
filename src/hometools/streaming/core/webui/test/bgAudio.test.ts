import { describe, it, expect, vi, afterEach } from "vitest";
import { startBgMirror, stopBgSync, getBgAudio, bgAudioIsActive } from "../src/bgAudio";

afterEach(() => {
  stopBgSync();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function fakeAudio() {
  const l: Record<string, () => void> = {};
  return {
    style: {},
    src: "",
    currentTime: 0,
    muted: false,
    paused: true,
    preload: "",
    playsInline: false,
    play: vi.fn(() => Promise.resolve()),
    addEventListener: (e: string, f: () => void) => (l[e] = f),
    fire: (e: string) => l[e](),
  };
}
function hooks(over: Record<string, unknown> = {}) {
  return {
    player: { src: "/v.mp4", currentTime: 10, paused: false } as unknown as HTMLMediaElement,
    isVideoPlayer: true,
    playNext: vi.fn(),
    ...over,
  };
}

describe("bgAudio", () => {
  it("no-op for non-video players", () => {
    vi.stubGlobal("document", { createElement: fakeAudio, body: { appendChild: vi.fn() } });
    startBgMirror(hooks({ isVideoPlayer: false }));
    expect(getBgAudio()).toBeNull();
  });
  it("mirrors src/time muted, forwards ended, resyncs on drift", () => {
    vi.useFakeTimers();
    const a = fakeAudio();
    vi.stubGlobal("document", { createElement: () => a, body: { appendChild: vi.fn() } });
    const h = hooks();
    startBgMirror(h);
    expect(getBgAudio()).toBe(a);
    expect(a.src).toBe("/v.mp4");
    expect(a.currentTime).toBe(10);
    expect(a.muted).toBe(true);
    expect(a.play).toHaveBeenCalled();
    expect(bgAudioIsActive()).toBe(false);
    (h.player as { currentTime: number }).currentTime = 20;
    vi.advanceTimersByTime(2000);
    expect(a.currentTime).toBe(20);
    a.fire("ended");
    expect(h.playNext).toHaveBeenCalled();
  });
  it("active only when unmuted and playing", () => {
    const a = getBgAudio()!;
    a.muted = false;
    (a as { paused: boolean }).paused = false;
    expect(bgAudioIsActive()).toBe(true);
  });
});

