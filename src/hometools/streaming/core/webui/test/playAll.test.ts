import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { playAllCurrent, navigateInto, playAllIn, showPlaylist } from "../src/playAll";

describe("playAllCurrent", () => {
  it("plays items under current path", () => {
    installState({ allItems: [item("a/1.mp4"), item("a/2.mp4"), item("b/3.mp4")], currentPath: "a" });
    const showPlaylist = vi.fn();
    playAllCurrent({ filesAt: () => [], showPlaylist });
    expect(showPlaylist).toHaveBeenCalledTimes(1);
    const [items, auto] = showPlaylist.mock.calls[0];
    expect(items.map((i: { relative_path: string }) => i.relative_path)).toEqual(["a/1.mp4", "a/2.mp4"]);
    expect(auto).toBe(true);
  });
  it("falls back to filesAt when nothing under path", () => {
    installState({ allItems: [], currentPath: "x" });
    const f = [item("x/f.mp4")];
    const showPlaylist = vi.fn();
    playAllCurrent({ filesAt: () => f, showPlaylist });
    expect(showPlaylist).toHaveBeenCalledWith(f, true);
  });
  it("does nothing when empty", () => {
    installState({ allItems: [], currentPath: "x" });
    const showPlaylist = vi.fn();
    playAllCurrent({ filesAt: () => [], showPlaylist });
    expect(showPlaylist).not.toHaveBeenCalled();
  });
});

describe("navigateInto / playAllIn", () => {
  const mk = (over = {}) => ({
    showFolderView: vi.fn(),
    triggerSilentRefresh: vi.fn(),
    loadLastPlayedLocal: () => null,
    showPlaylist: vi.fn(),
    ...over,
  });
  it("navigateInto appends and refreshes", () => {
    const s = installState({ allItems: [], currentPath: "a" });
    const h = mk();
    navigateInto("b", h);
    expect(s.currentPath).toBe("a/b");
    expect(h.triggerSilentRefresh).toHaveBeenCalled();
    expect(h.showFolderView).toHaveBeenCalled();
  });
  it("playAllIn plays folder from start", () => {
    installState({ allItems: [item("a/1.mp4"), item("a/2.mp4")], currentPath: "" });
    const h = mk();
    playAllIn("a", h);
    expect(h.showPlaylist).toHaveBeenCalledWith(expect.any(Array), true);
  });
  it("playAllIn resumes series at last episode", () => {
    const e1 = { ...item("s/1.mp4"), season: 1 };
    const e2 = { ...item("s/2.mp4"), season: 1 };
    installState({ allItems: [e1, e2], currentPath: "" });
    const h = mk({ loadLastPlayedLocal: () => ({ path: "s/2.mp4" }) });
    playAllIn("s", h);
    expect(h.showPlaylist).toHaveBeenCalledWith(expect.any(Array), true, 1);
  });
  it("playAllIn no-op when empty", () => {
    installState({ allItems: [], currentPath: "" });
    const h = mk();
    playAllIn("zz", h);
    expect(h.showPlaylist).not.toHaveBeenCalled();
  });
});

describe("showPlaylist", () => {
  const mk = (over = {}) => ({
    destroyPlaylistDragDrop: vi.fn(),
    sortByFolderOrder: (_p: string, i: unknown[]) => i as never[],
    enterTrackListView: vi.fn(),
    refreshFolderRatings: vi.fn(),
    playTrack: vi.fn(),
    restoreLastEpisode: vi.fn(),
    loadFolderOrderAsync: vi.fn(),
    loadFolderOrder: () => [],
    applyFilter: vi.fn(),
    routerUpdate: vi.fn(),
    ...over,
  });
  it("sets state and autoplays startIdx", () => {
    const s = installState({ currentPath: "a" });
    const h = mk();
    showPlaylist([item("a/1.mp4"), item("a/2.mp4")], true, 1, h);
    expect(s.inPlaylist).toBe(true);
    expect(s.currentPlaylistId).toBe("__folder__");
    expect(s.playlistItems).toHaveLength(2);
    expect(h.playTrack).toHaveBeenCalledWith(1);
    expect(h.refreshFolderRatings).toHaveBeenCalledWith([expect.anything(), expect.anything()]);
    expect(h.restoreLastEpisode).not.toHaveBeenCalled();
    expect(h.enterTrackListView).toHaveBeenCalledWith({ backDisabled: false, resetIndex: true });
    expect(h.routerUpdate).toHaveBeenCalled();
  });
  it("autoplay false + startIdx 0: no play, no episode restore", () => {
    installState({ currentPath: "a" });
    const h = mk();
    showPlaylist([item("a/1.mp4")], false, 0, h);
    expect(h.playTrack).not.toHaveBeenCalled();
    expect(h.restoreLastEpisode).not.toHaveBeenCalled();
  });
  it("passive nav restores last episode, no play", () => {
    installState({ currentPath: "" });
    const h = mk();
    showPlaylist([item("1.mp4")], false, undefined, h);
    expect(h.restoreLastEpisode).toHaveBeenCalled();
    expect(h.playTrack).not.toHaveBeenCalled();
  });
  it("re-sorts when server order differs", () => {
    const s = installState({ currentPath: "a", allItems: [item("a/1.mp4")] });
    const h = mk({
      loadFolderOrderAsync: (_p: string, cb: (o: string[]) => void) => cb(["x"]),
      loadFolderOrder: () => ["y"],
    });
    showPlaylist([item("a/1.mp4"), item("a/gone.mp4")], false, 0, h);
    expect(s.playlistItems).toHaveLength(1);
    expect(h.applyFilter).toHaveBeenCalled();
  });
});
