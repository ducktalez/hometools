import { describe, it, expect, vi, afterEach } from "vitest";
import { reachedEnd, onEnded, onError, onPause, onPlay, initPlayerEvents } from "../src/playerEvents";
import type { PlayerEventsHooks } from "../src/playerEvents";
import { setProgressPath } from "../src/progress";
import { setWasPlaying, wasPlaying } from "../src/bgPlayback";

afterEach(() => {
  setProgressPath("");
  setWasPlaying(false);
  vi.unstubAllGlobals();
});

function mk(over: Record<string, unknown> = {}, isVideoMode = false) {
  const player = { duration: 100, currentTime: 100, error: null, currentSrc: "", ended: false, volume: 1, ...over };
  const btnPlay = { innerHTML: "" };
  const listeners: Record<string, () => void> = {};
  (player as Record<string, unknown>).addEventListener = (e: string, f: () => void) => (listeners[e] = f);
  const h: PlayerEventsHooks = {
    player: player as unknown as HTMLMediaElement,
    btnPlay,
    icPlay: "PLAY",
    icPause: "PAUSE",
    isVideoMode,
    showVidControls: vi.fn(),
    saveProgressNow: vi.fn(),
    clearProgressFor: vi.fn(),
    finishCrossfade: vi.fn(),
    playNextItem: vi.fn(),
    currentStreamUrl: () => "/s",
    removeGoneTrack: vi.fn(),
    showToast: vi.fn(),
  };
  return { h, btnPlay, listeners };
}
const tick = () => new Promise((r) => setTimeout(r, 0));

describe("reachedEnd", () => {
  it("near end / unknown duration true, mid false", () => {
    expect(reachedEnd(100, 99)).toBe(true);
    expect(reachedEnd(NaN, 5)).toBe(true);
    expect(reachedEnd(0, 0)).toBe(true);
    expect(reachedEnd(100, 50)).toBe(false);
  });
});

describe("onEnded", () => {
  it("real end: clears progress, plays next", () => {
    vi.stubGlobal("document", { hidden: false });
    setProgressPath("a.mp4");
    const m = mk();
    onEnded(m.h);
    expect(m.h.clearProgressFor).toHaveBeenCalledWith("a.mp4");
    expect(m.h.playNextItem).toHaveBeenCalled();
  });
  it("spurious end: save + play icon, no advance", () => {
    const m = mk({ currentTime: 10 });
    onEnded(m.h);
    expect(m.h.saveProgressNow).toHaveBeenCalled();
    expect(m.btnPlay.innerHTML).toBe("PLAY");
    expect(m.h.playNextItem).not.toHaveBeenCalled();
  });
});

describe("onError", () => {
  it("no error -> play icon; aborted ignored", () => {
    const m = mk();
    onError(m.h);
    expect(m.btnPlay.innerHTML).toBe("PLAY");
    const m2 = mk({ error: { code: 1 } });
    onError(m2.h);
    expect(m2.btnPlay.innerHTML).toBe("");
  });
  it("network error + HEAD 404 -> removeGoneTrack", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ status: 404 })));
    setProgressPath("a.mp4");
    const m = mk({ error: { code: 2 } });
    onError(m.h);
    await tick();
    expect(m.h.removeGoneTrack).toHaveBeenCalledWith("a.mp4");
  });
  it("network error + other status -> toast; fetch failure -> connection toast", async () => {
    setProgressPath("a.mp4");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ status: 500 })));
    const m = mk({ error: { code: 2 } });
    onError(m.h);
    await tick();
    expect(m.h.showToast).toHaveBeenCalledWith("Wiedergabe fehlgeschlagen");
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    const m2 = mk({ error: { code: 2 } });
    onError(m2.h);
    await tick();
    expect(m2.h.showToast).toHaveBeenCalledWith("Verbindungsfehler");
  });
  it("decode error -> toast", () => {
    const m = mk({ error: { code: 3 } });
    onError(m.h);
    expect(m.h.showToast).toHaveBeenCalledWith("Wiedergabe fehlgeschlagen");
  });
});

describe("onPause / onPlay / init", () => {
  it("hidden page: ignored", () => {
    vi.stubGlobal("document", { hidden: true });
    setWasPlaying(true);
    const m = mk();
    onPause(m.h);
    expect(wasPlaying()).toBe(true);
    expect(m.h.saveProgressNow).not.toHaveBeenCalled();
  });
  it("user pause: clears wasPlaying, icon, save, video controls", () => {
    vi.stubGlobal("document", { hidden: false });
    setWasPlaying(true);
    const m = mk({}, true);
    onPause(m.h);
    expect(wasPlaying()).toBe(false);
    expect(m.btnPlay.innerHTML).toBe("PLAY");
    expect(m.h.saveProgressNow).toHaveBeenCalled();
    expect(m.h.showVidControls).toHaveBeenCalled();
  });
  it("play: pause icon; init registers all four listeners", () => {
    const m = mk({}, true);
    onPlay(m.h);
    expect(m.btnPlay.innerHTML).toBe("PAUSE");
    expect(m.h.showVidControls).toHaveBeenCalled();
    initPlayerEvents(m.h);
    expect(Object.keys(m.listeners).sort()).toEqual(["ended", "error", "pause", "play"]);
  });
});

