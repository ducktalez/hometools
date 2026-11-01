import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { startCrossfade, crossfadeCleanup, isCrossfading } from "../src/crossfade";
import type { CrossfadeHooks } from "../src/crossfade";
afterEach(() => {
  crossfadeCleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
function fakeAudio() {
  return {
    style: {},
    volume: 0,
    src: "",
    preload: "",
    load: vi.fn(),
    pause: vi.fn(),
    removeAttribute: vi.fn(),
    play: () => Promise.resolve(),
  };
}
function hooks(): CrossfadeHooks {
  return {
    player: { volume: 1 } as unknown as HTMLMediaElement,
    durationSec: 1,
    flushOutgoingProgress: vi.fn(),
    playTrack: vi.fn(),
    playFromQueue: vi.fn(),
  };
}
describe("crossfade", () => {
  it("does nothing without a next item with stream_url", () => {
    installState({ filteredItems: [item("a.mp3")], currentIndex: 0 });
    startCrossfade(hooks());
    expect(isCrossfading()).toBe(false);
  });
  it("ramps volumes, then hands over to playTrack(next) and resets volume", () => {
    vi.useFakeTimers();
    const xf = fakeAudio();
    vi.stubGlobal("document", { createElement: () => xf, body: { appendChild: vi.fn() } });
    installState({
      filteredItems: [item("a.mp3", { stream_url: "/a" }), item("b.mp3", { stream_url: "/b" })],
      currentIndex: 0,
    });
    const h = hooks();
    startCrossfade(h);
    expect(isCrossfading()).toBe(true);
    expect(xf.src).toBe("/b");
    vi.advanceTimersByTime(1000);
    expect(isCrossfading()).toBe(false);
    expect(h.flushOutgoingProgress).toHaveBeenCalled();
    expect(h.playTrack).toHaveBeenCalledWith(1);
    expect(h.player.volume).toBe(1);
  });
  it("queue head -> playFromQueue(0)", () => {
    vi.useFakeTimers();
    vi.stubGlobal("document", { createElement: fakeAudio, body: { appendChild: vi.fn() } });
    installState({ filteredItems: [item("a.mp3")], userQueue: [item("q.mp3", { stream_url: "/q" })], currentIndex: 0 });
    const h = hooks();
    startCrossfade(h);
    vi.advanceTimersByTime(1000);
    expect(h.playFromQueue).toHaveBeenCalledWith(0);
    expect(h.playTrack).not.toHaveBeenCalled();
  });
});
