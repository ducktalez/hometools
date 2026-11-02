import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import { syncShufflePosition, beginPlayback } from "../src/playbackStart";
import type { BeginPlaybackHooks } from "../src/playbackStart";

afterEach(() => vi.restoreAllMocks());

describe("syncShufflePosition", () => {
  it("sets pos when index in queue", () => {
    const s = installState({ shuffleMode: true, shuffleQueue: [3, 1, 2], currentIndex: 2 });
    syncShufflePosition();
    expect(s.shufflePos).toBe(2);
    expect(s.shuffleQueue).toEqual([3, 1, 2]);
  });
  it("prepends when missing", () => {
    const s = installState({ shuffleMode: true, shuffleQueue: [3, 1], currentIndex: 7 });
    syncShufflePosition();
    expect(s.shuffleQueue).toEqual([7, 3, 1]);
    expect(s.shufflePos).toBe(0);
  });
  it("no-op when shuffle off / empty / no index", () => {
    const s = installState({ shuffleMode: false, shuffleQueue: [1], currentIndex: 0, shufflePos: 5 });
    syncShufflePosition();
    expect(s.shufflePos).toBe(5);
    const s2 = installState({ shuffleMode: true, shuffleQueue: [1], currentIndex: -1, shufflePos: 5 });
    syncShufflePosition();
    expect(s2.shufflePos).toBe(5);
  });
});

function mk(playResults: Array<"ok" | "fail">) {
  const calls: string[] = [];
  const listeners: Record<string, () => void> = {};
  const player = {
    src: "",
    load: vi.fn(),
    play: vi.fn(() => (playResults.shift() === "fail" ? Promise.reject(new Error("x")) : Promise.resolve())),
    addEventListener: (e: string, f: () => void) => (listeners[e] = f),
  };
  const btnPlay = { innerHTML: "" };
  const hooks: BeginPlaybackHooks = {
    player: player as unknown as HTMLMediaElement,
    btnPlay,
    icPause: "PAUSE",
    icPlay: "PLAY",
    revokeOfflineUrl: () => calls.push("revoke"),
    onStarted: () => calls.push("started"),
    generateWaveform: (u, r) => calls.push("wave:" + u + ":" + r),
  };
  return { player, btnPlay, hooks, calls, listeners };
}
const tick = () => new Promise((r) => setTimeout(r, 0));

describe("beginPlayback", () => {
  it("plays stream: pause icon + onStarted + waveform", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const m = mk(["ok"]);
    beginPlayback({ url: "/s", offline: false, fallbackUrl: "/s" }, "a.mp4", m.hooks);
    await tick();
    expect(m.player.src).toBe("/s");
    expect(m.btnPlay.innerHTML).toBe("PAUSE");
    expect(m.calls).toEqual(["wave:/s:a.mp4", "started"]);
  });
  it("offline failure -> revoke + stream fallback", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const m = mk(["fail", "ok"]);
    beginPlayback({ url: "blob:x", offline: true, fallbackUrl: "/s" }, "a.mp4", m.hooks);
    await tick();
    expect(m.calls).toContain("revoke");
    expect(m.player.src).toBe("/s");
    expect(m.calls).toContain("started");
  });
  it("stream failure waits for canplay, retry failure shows play icon", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    const m = mk(["fail", "fail"]);
    beginPlayback({ url: "/s", offline: false, fallbackUrl: "/s" }, "a.mp4", m.hooks);
    await tick();
    m.listeners.canplay();
    await tick();
    expect(m.btnPlay.innerHTML).toBe("PLAY");
  });
});

