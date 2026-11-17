/**
 * Playlist hook wiring. Replaces the hook-builder glue formerly in
 * `player_js/_smart_playlists.py`: binds the playlist modules (views,
 * actions, reorder, picker, editor, drag-drop) to CFG paths and to the
 * remaining legacy callbacks. `deps` is a thunk so legacy functions are
 * resolved at call time (declaration order independent).
 */

import { getState } from "./stateBridge";
import { resolvePlaylistItems, type UserPlaylist } from "./smartPlaylist";
import { openSmartPlaylistEditor } from "./smartEditor";
import {
  showUserPlaylistView,
  playUserPlaylist,
  openPlaylistModal,
  closePlaylistModal,
  type PlaylistViewHooks,
} from "./playlistViews";
import {
  deleteUserPlaylist,
  renameUserPlaylist,
  addToPlaylist,
  createAndAddToPlaylist,
  removeFromPlaylist,
  refreshSmartPlaylist,
  type PlaylistHooks,
} from "./playlistActions";
import { openTrackPicker, isManualPlaylistView, reloadPlaylistView } from "./trackPicker";
import { reorderPlaylistItem } from "./playlistReorder";
import { initPlaylistDragDrop, destroyPlaylistDragDrop } from "./playlistDragDrop";

export interface PlaylistWiringCfg {
  /** `PLAYLISTS_API_PATH` */
  apiPath: string;
  /** `PLAYLISTS_SMART_PATH` */
  smartPath: string;
  /** `IC_SMART_PLAYLIST` markup */
  smartIcon: string;
}

/** Legacy callbacks still owned by the closure script. */
export interface PlaylistWiringDeps {
  toast(msg: string): void;
  esc(s: unknown): string;
  showFolderView(): void;
  applyFilter(force?: boolean): void;
  enterTrackListView(opts: { title: string }): void;
  playTrack(index: number): void;
  sortFavoritesByOrder(items: LegacyMediaItem[]): LegacyMediaItem[];
  loadFavoritesOrder(): string[];
  loadFavoritesOrderAsync(cb: (serverOrder: string[]) => void): void;
  saveFavoritesOrder(paths: string[]): void;
  saveFolderOrder(folderPath: string, paths: string[]): void;
  renderTracks(items: LegacyMediaItem[], force: boolean): void;
}

export function createPlaylistWiring(cfg: PlaylistWiringCfg, deps: () => PlaylistWiringDeps) {
  const resolve = (plId: string) => {
    const st = getState();
    if (!st) return null;
    return resolvePlaylistItems(plId, st.userPlaylists as UserPlaylist[], st.allItems, st.savedFavorites);
  };

  const actionHooks = (): PlaylistHooks => {
    const d = deps();
    return {
      apiPath: cfg.apiPath,
      toast: d.toast,
      refreshRoot: () => {
        const st = getState();
        if (st && !st.currentPath && !st.inPlaylist) d.showFolderView();
      },
      closeModal: closePlaylistModal,
    };
  };

  const add = (plId: string, rp: string) => addToPlaylist(plId, rp, actionHooks());

  const viewHooks = (): PlaylistViewHooks => {
    const d = deps();
    return {
      toast: d.toast,
      esc: d.esc,
      enterTrackListView: d.enterTrackListView,
      applyFilter: () => d.applyFilter(),
      playTrack: d.playTrack,
      savedFavorites: () => getState()?.savedFavorites ?? {},
      sortFavoritesByOrder: d.sortFavoritesByOrder,
      loadFavoritesOrder: d.loadFavoritesOrder,
      loadFavoritesOrderAsync: d.loadFavoritesOrderAsync,
      resolvePlaylist: resolve,
      addToPlaylist: add,
    };
  };

  const reload = (plId: string, force?: boolean) =>
    reloadPlaylistView(plId, resolve, (f) => deps().applyFilter(f), force);

  const reorder = (relativePath: string, toIndex: number): void => {
    const d = deps();
    reorderPlaylistItem(relativePath, toIndex, {
      apiPath: cfg.apiPath,
      toast: d.toast,
      renderTracks: d.renderTracks,
      saveFavoritesOrder: d.saveFavoritesOrder,
      saveFolderOrder: d.saveFolderOrder,
    });
  };

  return {
    resolvePlaylistItems: resolve,
    openSmartPlaylistEditor(existing: UserPlaylist | null): void {
      const d = deps();
      openSmartPlaylistEditor(existing, {
        apiPath: cfg.smartPath,
        esc: d.esc,
        icon: cfg.smartIcon,
        toast: d.toast,
        showFolderView: d.showFolderView,
      });
    },
    refreshSmartPlaylist(plId: string): void {
      const d = deps();
      refreshSmartPlaylist(plId, { applyFilter: () => d.applyFilter(), showFolderView: d.showFolderView, toast: d.toast });
    },
    showUserPlaylistView: (plId: string) => showUserPlaylistView(plId, viewHooks()),
    playUserPlaylist: (plId: string) => playUserPlaylist(plId, viewHooks()),
    openPlaylistModal: (rp: string) => openPlaylistModal(rp, viewHooks()),
    closePlaylistModal,
    openTrackPicker(plId: string): void {
      const d = deps();
      openTrackPicker({
        playlistId: plId,
        esc: d.esc,
        // no root refresh: picker re-renders the open playlist via refresh()
        addToPlaylist: (id, rp) =>
          addToPlaylist(id, rp, { ...actionHooks(), refreshRoot: () => {}, closeModal: undefined }),
        refresh: () => reload(plId),
      });
    },
    deleteUserPlaylist: (plId: string) => deleteUserPlaylist(plId, actionHooks()),
    renameUserPlaylist: (plId: string) => renameUserPlaylist(plId, actionHooks()),
    addToPlaylist: add,
    createAndAddToPlaylist: (name: string, rp: string) => createAndAddToPlaylist(name, rp, actionHooks()),
    isManualPlaylistView,
    removeFromUserPlaylist(relativePath: string): void {
      const plId = getState()?.currentPlaylistId ?? "";
      removeFromPlaylist(plId, relativePath, actionHooks(), () => reload(plId, true));
    },
    reorderPlaylistItem: reorder,
    initPlaylistDragDrop(): void {
      initPlaylistDragDrop({ reorder });
    },
    destroyPlaylistDragDrop,
  };
}

export type PlaylistWiring = ReturnType<typeof createPlaylistWiring>;
