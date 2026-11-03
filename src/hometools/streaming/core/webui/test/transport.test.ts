import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { togglePlay, handlePreviousTrack } from "../src/transport";
import type { TransportHooks } from "../src/transport";
import { wasPlaying, setWasPlaying } from "../src/bgPlayback";

afterEach(() => setWasPlaying(false));

function mk(paused: boolean, time = 0, dur = 0) {
  const player = {
    paused,
    currentTime: time,
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
  };
  const btnPlay = { innerHTML: "" };
  const hooks: TransportHooks = {
    player: player as unknown as HTMLMediaElement,
    btnPlay,
    icPlay: "PLAY",
    icPause: "PAUSE",
    playTrack: vi.fn(),
    startBgMirror: vi.fn(),
    stopBgSync: vi.fn(),
    currentItemDuration: () => dur,
  };
  return { player, btnPlay, hooks };
}

describe("togglePlay", () => {
  it("nothing selected -> plays track 0", () => {
    installState({ currentIndex: -1, filteredItems: [item("a")] });
    const m = mk(true);
    togglePlay(m.hooks);
    expect(m.hooks.playTrack).toHaveBeenCalledWith(0);
    expect(m.player.play).not.toHaveBeenCalled();
  });
  it("paused -> play, pause icon, bg mirror", async () => {
    installState({ currentIndex: 0, filteredItems: [item("a")] });
    const m = mk(true);
    togglePlay(m.hooks);
    expect(m.player.play).toHaveBeenCalled();
    expect(m.btnPlay.innerHTML).toBe("PAUSE");
    await Promise.resolve();
    await Promise.resolve();
    expect(m.hooks.startBgMirror).toHaveBeenCalled();
  });
  it("playing -> user pause clears wasPlaying, stops sync", () => {
    installState({ currentIndex: 0, filteredItems: [item("a")] });
    setWasPlaying(true);
    const m = mk(false);
    togglePlay(m.hooks);
    expect(m.player.pause).toHaveBeenCalled();
    expect(wasPlaying()).toBe(false);
    expect(m.hooks.stopBgSync).toHaveBeenCalled();
    expect(m.btnPlay.innerHTML).toBe("PLAY");
  });
});

describe("handlePreviousTrack", () => {
  it(">=3s in: restart current", () => {
    installState({ currentIndex: 2, filteredItems: [item("a"), item("b"), item("c")] });
    const m = mk(false, 30, 200);
    handlePreviousTrack(m.hooks);
    expect(m.hooks.playTrack).toHaveBeenCalledWith(2);
  });
  it("<3s: previous track", () => {
    installState({ currentIndex: 2, filteredItems: [item("a"), item("b"), item("c")] });
    const m = mk(false, 1, 200);
    handlePreviousTrack(m.hooks);
    expect(m.hooks.playTrack).toHaveBeenCalledWith(1);
  });
  it("short track (<10s) goes previous even when >=3s", () => {
    installState({ currentIndex: 2, filteredItems: [item("a"), item("b"), item("c")] });
    const m = mk(false, 5, 8);
    handlePreviousTrack(m.hooks);
    expect(m.hooks.playTrack).toHaveBeenCalledWith(1);
  });
});

