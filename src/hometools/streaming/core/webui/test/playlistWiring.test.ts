import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { createPlaylistWiring } from "../src/playlistWiring";

const deps = () => ({
  toast: vi.fn(),
  esc: (s: unknown) => String(s),
  showFolderView: vi.fn(),
  applyFilter: vi.fn(),
  enterTrackListView: vi.fn(),
  playTrack: vi.fn(),
  sortFavoritesByOrder: (i: LegacyMediaItem[]) => i,
  loadFavoritesOrder: () => [],
  loadFavoritesOrderAsync: vi.fn(),
  saveFavoritesOrder: vi.fn(),
  saveFolderOrder: vi.fn(),
  renderTracks: vi.fn(),
});

describe("createPlaylistWiring", () => {
  const cfg = { apiPath: "/pl", smartPath: "/pl/smart", smartIcon: "" };

  it("exposes every wrapper the legacy fragment calls", () => {
    const w = createPlaylistWiring(cfg, deps);
    for (const k of [
      "openSmartPlaylistEditor", "refreshSmartPlaylist", "showUserPlaylistView", "playUserPlaylist",
      "openPlaylistModal", "closePlaylistModal", "openTrackPicker", "deleteUserPlaylist",
      "renameUserPlaylist", "addToPlaylist", "createAndAddToPlaylist", "isManualPlaylistView",
      "removeFromUserPlaylist", "reorderPlaylistItem", "initPlaylistDragDrop", "destroyPlaylistDragDrop",
    ] as const) {
      expect(typeof w[k]).toBe("function");
    }
  });

  it("resolves manual playlist items from allItems via state", () => {
    installState({
      allItems: [item("a"), item("b")],
      userPlaylists: [{ id: "p1", name: "P", items: ["b"] }],
    });
    const r = createPlaylistWiring(cfg, deps).resolvePlaylistItems("p1");
    expect(r?.resolved.map((i) => i.relative_path)).toEqual(["b"]);
    expect(createPlaylistWiring(cfg, deps).resolvePlaylistItems("nope")).toBeNull();
  });

  it("resolves null without state", () => {
    (globalThis as unknown as { window: object }).window = {};
    expect(createPlaylistWiring(cfg, deps).resolvePlaylistItems("p1")).toBeNull();
  });
});
