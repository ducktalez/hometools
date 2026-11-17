import { describe, it, expect } from "vitest";
import { createPlaybackState, computeEffectiveThreshold } from "../src/playbackState";

describe("computeEffectiveThreshold", () => {
  it("explicit min wins", () => expect(computeEffectiveThreshold(3, true)).toBe(3));
  it("defaults to 2 with rating write", () => expect(computeEffectiveThreshold(0, true)).toBe(2));
  it("0 without rating write", () => expect(computeEffectiveThreshold(0, false)).toBe(0));
});

describe("createPlaybackState", () => {
  it("starts empty and instances are independent", () => {
    const a = createPlaybackState();
    expect(a).toEqual({
      currentStreamUrl: "",
      itemDuration: 0,
      globalSearchActive: false,
      savedFavorites: {},
      justRatedPath: null,
      allItems: [],
      filteredItems: [],
      playlistItems: [],
      currentIndex: -1,
      currentPath: "",
      inPlaylist: false,
      shuffleMode: false,
      repeatMode: false,
      shuffleQueue: [],
      shufflePos: -1,
      userQueue: [],
      userPlaylists: [],
      playlistRevision: 0,
      currentPlaylistId: "",
      playlistAddPath: "",
    });
    a.itemDuration = 5;
    a.savedFavorites["x"] = true;
    expect(createPlaybackState().savedFavorites).toEqual({});
    expect(createPlaybackState().itemDuration).toBe(0);
  });
});
