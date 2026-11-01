import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { jumpToCurrentTrack } from "../src/playerNav";
import type { JumpHooks } from "../src/playerNav";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<JumpHooks> = {}): JumpHooks {
  return {
    ensureRenderedTo: vi.fn(),
    markActive: vi.fn(),
    itemsUnder: vi.fn(() => []),
    showPlaylist: vi.fn(),
    ...over,
  };
}

describe("jumpToCurrentTrack", () => {
  it("no current track -> no-op", () => {
    installState({ currentIndex: -1 });
    const h = hooks();
    jumpToCurrentTrack(h);
    expect(h.markActive).not.toHaveBeenCalled();
  });

  it("already in the right folder view -> just scroll", () => {
    installState({ currentIndex: 0, filteredItems: [item("a/b.mp3")], inPlaylist: true, currentPath: "a" });
    const h = hooks();
    jumpToCurrentTrack(h);
    expect(h.ensureRenderedTo).toHaveBeenCalledWith(0);
    expect(h.markActive).toHaveBeenCalled();
    expect(h.showPlaylist).not.toHaveBeenCalled();
  });

  it("other view -> navigates to folder, re-finds index after showPlaylist", () => {
    const playing = item("a/b.mp3");
    const s = installState({ currentIndex: 0, filteredItems: [playing], inPlaylist: false, currentPath: "" });
    const newList = [item("a/x.mp3"), playing];
    const h = hooks({
      itemsUnder: vi.fn(() => newList),
      showPlaylist: vi.fn(() => {
        s.filteredItems = newList;
      }),
    });
    jumpToCurrentTrack(h);
    expect(s.currentPath).toBe("a");
    expect(h.showPlaylist).toHaveBeenCalledWith(newList, false);
    expect(s.currentIndex).toBe(1);
    expect(h.ensureRenderedTo).toHaveBeenCalledWith(1);
    expect(h.markActive).toHaveBeenCalled();
  });

  it("empty folder -> stays", () => {
    installState({ currentIndex: 0, filteredItems: [item("a/b.mp3")] });
    const h = hooks();
    jumpToCurrentTrack(h);
    expect(h.showPlaylist).not.toHaveBeenCalled();
  });
});

