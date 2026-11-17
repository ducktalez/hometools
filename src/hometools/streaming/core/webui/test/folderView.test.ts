import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { showFolderView } from "../src/folderView";
import type { FolderViewHooks } from "../src/folderView";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<FolderViewHooks> = {}): FolderViewHooks {
  const noop = vi.fn();
  return {
    folderGrid: { innerHTML: "", querySelectorAll: () => [] } as unknown as HTMLElement,
    itemNoun: "track",
    defaultLang: "de",
    playlistsEnabled: false,
    offlineEnabled: false,
    recentEnabled: false,
    playlistsApiPath: "/p",
    icons: { smartPlaylist: "", playlist: "", dl: "", refresh: "", star: "", folderPlay: "", dots: "", edit: "", trash: "" },
    esc: (s) => String(s),
    toast: noop,
    cardOpts: () => ({}) as never,
    toolActive: () => false,
    contentsAt: () => ({ folders: [], files: [] }),
    destroyPlaylistDragDrop: vi.fn(),
    clearMoveGhosts: vi.fn(),
    enterFolderGridView: vi.fn(),
    showPlaylist: vi.fn(),
    loadRecentlyPlayed: vi.fn(),
    openOfflineLibrary: noop,
    updateOfflineFolderCount: noop,
    showUserPlaylistView: noop,
    playUserPlaylist: noop,
    openSmartPlaylistEditor: noop,
    refreshSmartPlaylist: noop,
    renameUserPlaylist: noop,
    deleteUserPlaylist: noop,
    navigateInto: noop,
    playAllIn: noop,
    showLangPicker: noop,
    triggerSilentRefresh: noop,
    ...over,
  };
}

function stubDoc() {
  vi.stubGlobal("document", { getElementById: () => null, querySelector: () => null });
}

describe("showFolderView", () => {
  it("resets view state and clears move ghosts / drag-drop", () => {
    const s = installState({ inPlaylist: true, currentPlaylistId: "x", globalSearchActive: true });
    stubDoc();
    const h = hooks();
    showFolderView(h);
    expect(s.inPlaylist).toBe(false);
    expect(s.currentPlaylistId).toBe("");
    expect(s.globalSearchActive).toBe(false);
    expect(h.destroyPlaylistDragDrop).toHaveBeenCalled();
    expect(h.clearMoveGhosts).toHaveBeenCalled();
  });

  it("empty library -> empty hint, no playlist", () => {
    installState();
    stubDoc();
    const h = hooks();
    showFolderView(h);
    expect(h.enterFolderGridView).toHaveBeenCalledWith(
      expect.objectContaining({ playAllDisabled: true, trackCount: "" })
    );
    expect(h.showPlaylist).not.toHaveBeenCalled();
  });

  it("leaf folder (files only) -> showPlaylist without autoplay", () => {
    installState({ currentPath: "A" });
    stubDoc();
    const files = [item("A/1.mp3")];
    const h = hooks({ contentsAt: () => ({ folders: [], files }) });
    showFolderView(h);
    expect(h.showPlaylist).toHaveBeenCalledWith(files, false);
    expect(h.enterFolderGridView).not.toHaveBeenCalled();
  });

  it("folders -> label with counts, grid html assigned, recent hidden when disabled", () => {
    installState({ allItems: [item("A/1.mp3")] });
    const rs = { hidden: false };
    vi.stubGlobal("document", {
      getElementById: (id: string) => (id === "recent-section" ? rs : null),
      querySelector: () => null,
    });
    const h = hooks({
      contentsAt: () => ({
        folders: [{ name: "A", displayName: "A", isFavorite: false, count: 1, thumbnail_url: "", thumbnail_lg_url: "", languages: [], variants: null }],
        files: [item("x.mp3")],
      }),
      cardOpts: () =>
        ({
          escHtml: (s: unknown) => String(s),
          viewMode: "list",
          showOrigNames: false,
          isVideo: false,
          itemNoun: "track",
          defaultLang: "de",
          audiobookDirs: [],
          langNames: {},
          folderPlaceholder: "",
          filePlaceholder: "",
          icStar: "",
          icFolderPlay: "",
          compositeFlagHtml: () => "",
          langBadgesHtml: () => "",
        }) as never,
    });
    showFolderView(h);
    expect(h.enterFolderGridView).toHaveBeenCalledWith({ trackCount: "1 folder, 1 track" });
    expect(h.folderGrid.innerHTML.length).toBeGreaterThan(0);
    expect(rs.hidden).toBe(true);
    expect(h.loadRecentlyPlayed).not.toHaveBeenCalled();
  });
});

