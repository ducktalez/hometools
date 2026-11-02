import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { playAllCurrent } from "../src/playAll";

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

