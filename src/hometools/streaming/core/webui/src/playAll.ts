/**
 * "Play all" for the current folder.
 * (`playAllCurrent`). State via `htState`, view effects via hooks.
 */

import { getState } from "./stateBridge";
import { itemsUnder } from "./catalogQuery";
import { rebuildShuffleQueue } from "./shuffle";

export interface PlayAllHooks {
  /** Direct files of a folder (app `contentsAt(path).files`). */
  filesAt(path: string): CatalogItem[];
  showPlaylist(items: CatalogItem[], autoplay: boolean): void;
}

export function playAllCurrent(hooks: PlayAllHooks): void {
  const s = getState();
  if (!s) return;
  let items = itemsUnder(s.currentPath, s.allItems);
  if (!items.length) items = hooks.filesAt(s.currentPath);
  if (items.length) hooks.showPlaylist(items, true);
}

export interface FolderNavHooks {
  showFolderView(): void;
  triggerSilentRefresh(): void;
  /** Last played item (localStorage), or null. */
  loadLastPlayedLocal(): { path?: string } | null;
  showPlaylist(items: CatalogItem[], autoplay: boolean, startIdx?: number): void;
}

/** Descend into subfolder `name`; always fetch fresh catalog. */
export function navigateInto(name: string, hooks: FolderNavHooks): void {
  const s = getState();
  if (!s) return;
  s.currentPath = s.currentPath ? s.currentPath + "/" + name : name;
  hooks.triggerSilentRefresh();
  hooks.showFolderView();
}

/** Play folder `name`; series resume at last-watched episode. */
export function playAllIn(name: string, hooks: FolderNavHooks): void {
  const s = getState();
  if (!s) return;
  const full = s.currentPath ? s.currentPath + "/" + name : name;
  const items = itemsUnder(full, s.allItems);
  if (!items.length) return;
  s.currentPath = full;
  const isSeries = items.some((it) => ((it as { season?: number }).season || 0) > 0);
  if (isSeries) {
    const local = hooks.loadLastPlayedLocal();
    if (local && local.path) {
      const idx = items.findIndex((it) => it.relative_path === local.path);
      if (idx >= 0) {
        hooks.showPlaylist(items, true, idx);
        return;
      }
    }
  }
  hooks.showPlaylist(items, true);
}

export interface ShowPlaylistHooks {
  destroyPlaylistDragDrop(): void;
  sortByFolderOrder(path: string, items: CatalogItem[]): CatalogItem[];
  enterTrackListView(opts: { backDisabled: boolean; resetIndex: boolean }): void;
  refreshFolderRatings(items: CatalogItem[]): void;
  playTrack(idx: number): void;
  restoreLastEpisode(): void;
  loadFolderOrderAsync(path: string, cb: (order: string[]) => void): void;
  loadFolderOrder(path: string): string[];
  applyFilter(): void;
  routerUpdate(): void;
}

/** Folder-leaf playlist view (+ optional autoplay). State via htState. */
export function showPlaylist(
  items: CatalogItem[],
  autoplay: boolean | undefined,
  startIdx: number | undefined,
  hooks: ShowPlaylistHooks,
): void {
  const s = getState();
  if (!s) return;
  hooks.destroyPlaylistDragDrop();
  s.inPlaylist = true;
  s.currentPlaylistId = "__folder__";
  s.playlistItems = hooks.sortByFolderOrder(s.currentPath, items);

  hooks.enterTrackListView({ backDisabled: !s.currentPath, resetIndex: true });

  hooks.refreshFolderRatings(items);
  if (s.shuffleMode) rebuildShuffleQueue(startIdx || 0);
  if (autoplay && s.playlistItems.length) {
    const firstIdx = s.shuffleMode && s.shuffleQueue.length ? s.shuffleQueue[0] : startIdx || 0;
    hooks.playTrack(firstIdx);
  } else if (typeof startIdx === "undefined") {
    hooks.restoreLastEpisode();
  }
  const path = s.currentPath;
  hooks.loadFolderOrderAsync(path, (serverOrder) => {
    if (!serverOrder.length) return;
    const st = getState();
    if (!st || st.currentPlaylistId !== "__folder__") return;
    const local = hooks.loadFolderOrder(path);
    if (JSON.stringify(local) === JSON.stringify(serverOrder)) return;
    st.playlistItems = hooks.sortByFolderOrder(path, itemsUnder(path, st.allItems));
    hooks.applyFilter();
  });
  hooks.routerUpdate();
}
