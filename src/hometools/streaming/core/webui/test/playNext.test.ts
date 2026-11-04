import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { dequeueNext, playNextItem } from "../src/playNext";
import type { PlayNextHooks } from "../src/playNext";

function mk() {
  const player = { currentTime: 5, play: vi.fn(() => Promise.resolve()) };
  const hooks: PlayNextHooks = {
    player,
    playFromQueue: vi.fn(),
    playTrack: vi.fn(),
    setWasPlaying: vi.fn(),
    showStopped: vi.fn(),
  };
  return { player, hooks };
}

describe("dequeueNext", () => {
  it("false on empty queue", () => {
    installState();
    const { hooks } = mk();
    expect(dequeueNext(hooks)).toBe(false);
    expect(hooks.playFromQueue).not.toHaveBeenCalled();
  });
  it("plays head of queue", () => {
    installState({ userQueue: [item("a")] });
    const { hooks } = mk();
    expect(dequeueNext(hooks)).toBe(true);
    expect(hooks.playFromQueue).toHaveBeenCalledWith(0);
  });
});

describe("playNextItem", () => {
  it("repeat-one restarts", () => {
    installState({ repeatMode: "one", filteredItems: [item("a")], currentIndex: 0 });
    const { player, hooks } = mk();
    playNextItem(hooks);
    expect(player.currentTime).toBe(0);
    expect(player.play).toHaveBeenCalled();
    expect(hooks.playTrack).not.toHaveBeenCalled();
  });
  it("queue wins over list", () => {
    installState({ userQueue: [item("q")], filteredItems: [item("a"), item("b")], currentIndex: 0 });
    const { hooks } = mk();
    playNextItem(hooks);
    expect(hooks.playFromQueue).toHaveBeenCalledWith(0);
    expect(hooks.playTrack).not.toHaveBeenCalled();
  });
  it("advances to next index", () => {
    installState({ filteredItems: [item("a"), item("b")], currentIndex: 0 });
    const { hooks } = mk();
    playNextItem(hooks);
    expect(hooks.playTrack).toHaveBeenCalledWith(1);
  });
  it("stops at end of list", () => {
    installState({ filteredItems: [item("a"), item("b")], currentIndex: 1 });
    const { hooks } = mk();
    playNextItem(hooks);
    expect(hooks.playTrack).not.toHaveBeenCalled();
    expect(hooks.setWasPlaying).toHaveBeenCalledWith(false);
    expect(hooks.showStopped).toHaveBeenCalled();
  });
  it("empty list is no-op", () => {
    installState();
    const { hooks } = mk();
    playNextItem(hooks);
    expect(hooks.playTrack).not.toHaveBeenCalled();
    expect(hooks.showStopped).not.toHaveBeenCalled();
  });
});

