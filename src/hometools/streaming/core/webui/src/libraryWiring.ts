/**
 * Library hook wiring. Replaces the hook-builder glue formerly in
 * folder list, move widget, context menus, rating, favorites, edit modal and
 * resolved per call, so declaration order in the closure script does not matter).
 */

import { getState } from "./stateBridge";
import { getDom } from "./dom";
import { invalidateDupeIndex, ensureDupeIndex } from "./dupeState";
import { openDupePanel, closeDupePanel, playDupeItem, playDuplicates } from "./dupePanel";
import {
  deleteTrackFromList,
  deleteDuplicateFile,
  removeGoneTrack,
  moveFileToFolder,
  type LibraryOpsHooks,
} from "./libraryOps";
import { getAllFolders, invalidateFolderCache } from "./folderCache";
import { getRecentMoveTargets } from "./recentMoveTargets";
import { moveWidgetHtml } from "./inlineWidgets";
import { currentFolderOf } from "./pathUtils";
import { openCtxMenu, trackCtxMenuItems, revealInExplorer, type CtxItem } from "./ctxMenu";
import {
  renderPlayerRating,
  patchAllItemsRating,
  updateTrackRatingBar,
  setRating,
  setInlineRating,
  type RatingHooks,
} from "./rating";
import { loadFavorites, updateFavoriteButtons, toggleFavorite, type FavoritesHooks } from "./favorites";
import {
  initEditModalRatingEvents,
  openEditModal,
  closeEditModal,
  submitEditModal,
  type EditModalHooks,
} from "./editModal";
import { FAVORITES_ORDER_KEY, folderOrderKey, loadOrder, saveOrder, loadOrderAsync, sortByOrder } from "./customOrder";
import { resetRenderGuard } from "./trackRender";
import { getProgressPath } from "./progress";
import { rebuildShuffleQueue } from "./shuffle";

export interface LibraryCfg {
  filePlaceholder: string;
  deleteApiPath: string;
  moveApiPath: string;
  revealApiPath: string;
  ratingApiPath: string;
  auditUndoPath: string;
  folderOrderApiPath: string;
  apiBase: string;
  ratingWriteEnabled: boolean;
  metadataEditEnabled: boolean;
  metadataEditPath: string;
  icPlay: string;
  icDuplicate: string;
  icTrash: string;
  icFolderOpen: string;
  icStarFilled: string;
  icStarEmpty: string;
}

export interface LibraryDeps {
  esc(s: unknown): string;
  toast(msg: string): void;
  applyFilter(): void;
  markActive(): void;
  showFolderView(): void;
  showPlaylist(items: CatalogItem[], autoplay: boolean, startIdx: number): void;
  playTrack(idx: number): void;
  itemsUnder(path: string): CatalogItem[];
  destroyPlaylistDragDrop(): void;
  enterTrackListView(opts: { title: string; playAllDisabled: boolean; collapseFilterBar: boolean; resetIndex: boolean }): void;
  saveCatalogCache(items: unknown[]): void;
  isManualPlaylistView(): boolean;
  removeFromUserPlaylist(relativePath: string): void;
  filterFavActive(): boolean;
}

export function createLibraryWiring(cfg: LibraryCfg, deps: () => LibraryDeps) {
  const text = (k: "playerTitle" | "playerArtist", v: string): void => {
    const e = getDom()[k];
    if (e) e.textContent = v;
  };

  const invalidateDupeMap = (): void => {
    invalidateDupeIndex();
    resetRenderGuard();
  };

  const opsHooks = (): LibraryOpsHooks => {
    const d = deps();
    return {
      deleteApiPath: cfg.deleteApiPath,
      moveApiPath: cfg.moveApiPath,
      toast: d.toast,
      invalidateCaches: () => {
        invalidateDupeMap();
        invalidateFolderCache();
      },
      saveCatalogCache: d.saveCatalogCache,
      applyFilter: d.applyFilter,
      showFolderView: d.showFolderView,
      playTrack: d.playTrack,
      itemsUnder: d.itemsUnder,
      progressRelPath: getProgressPath,
      showPausedIcon: () => {
        const b = getDom().btnPlay;
        if (b) b.innerHTML = cfg.icPlay;
      },
      reopenDupePanel: openDupe,
    };
  };

  const ratingHooks = (): RatingHooks => {
    const d = deps();
    return {
      writeEnabled: cfg.ratingWriteEnabled,
      ratingApiPath: cfg.ratingApiPath,
      auditUndoPath: cfg.auditUndoPath,
      icStarFilled: cfg.icStarFilled,
      icStarEmpty: cfg.icStarEmpty,
      toast: d.toast,
      applyFilter: d.applyFilter,
      markActive: d.markActive,
      rebuildShuffleQueue,
    };
  };

  const favHooks = (): FavoritesHooks => {
    const d = deps();
    return { apiBase: cfg.apiBase, toast: d.toast, applyFilter: d.applyFilter, filterFavActive: d.filterFavActive };
  };

  const editHooks = (): EditModalHooks => {
    const d = deps();
    return {
      metadataEditEnabled: cfg.metadataEditEnabled,
      ratingWriteEnabled: cfg.ratingWriteEnabled,
      metadataEditPath: cfg.metadataEditPath,
      ratingApiPath: cfg.ratingApiPath,
      icStarFilled: cfg.icStarFilled,
      icStarEmpty: cfg.icStarEmpty,
      toast: d.toast,
      applyFilter: d.applyFilter,
      renderPlayerRating: (s) => renderPlayerRating(s, ratingHooks()),
      rebuildShuffleQueue,
      setPlayerText: (title, artist) => {
        text("playerTitle", title);
        text("playerArtist", artist);
      },
    };
  };

  const allFolders = (): string[] => getAllFolders(getState()?.allItems ?? []);

  function openDupe(): void {
    const d = deps();
    const items = getState()?.allItems ?? [];
    const di = ensureDupeIndex(items);
    openDupePanel(
      { allItems: items, dupeMap: di.map, dupeSafety: di.safety, dupePaths: di.paths } as never,
      {
        escHtml: d.esc,
        filePlaceholder: cfg.filePlaceholder,
        icDuplicate: cfg.icDuplicate,
        icTrash: cfg.icTrash,
        deleteDuplicate: (i) => deleteDuplicateFile(i, opsHooks()),
        playItem: (t) => playDupeItem(t, { itemsUnder: d.itemsUnder, showPlaylist: d.showPlaylist, playTrack: d.playTrack }),
      },
    );
  }

  const openCtx = (btn: HTMLElement, items: CtxItem[]): void => openCtxMenu(btn, items, deps().esc);
  const reveal = (relativePath: string | undefined): void => {
    void revealInExplorer(relativePath ?? "", { apiPath: cfg.revealApiPath, toast: deps().toast });
  };

  const orderKey = (p: string): string => folderOrderKey(p);

  return {
    invalidateDupeMap,
    openDupePanel: openDupe,
    closeDupePanel,
    playDuplicates(): void {
      const d = deps();
      playDuplicates(ensureDupeIndex(getState()?.allItems ?? []).map, {
        toast: d.toast,
        closePanel: closeDupePanel,
        destroyPlaylistDragDrop: d.destroyPlaylistDragDrop,
        enterTrackListView: d.enterTrackListView,
        rebuildShuffleQueue,
      });
    },
    deleteDuplicateFile: (i: number) => deleteDuplicateFile(i, opsHooks()),
    removeGoneTrack: (rp: string) => removeGoneTrack(rp, opsHooks()),
    deleteTrackFromList: (i: number) => deleteTrackFromList(i, opsHooks()),
    moveFileToFolder: (i: number, target: string) => moveFileToFolder(i, target, opsHooks()),
    getAllFolders: allFolders,
    renderMoveWidget: (t: { relative_path?: string }, idx: number) =>
      moveWidgetHtml(idx, currentFolderOf(t), getRecentMoveTargets(), allFolders(), deps().esc, cfg.icTrash),
    openCtxMenu: openCtx,
    openTrackCtxMenu(btn: HTMLElement, relativePath: string | undefined, _title?: string): void {
      const d = deps();
      openCtx(
        btn,
        trackCtxMenuItems({
          icFolderOpen: cfg.icFolderOpen,
          icTrash: cfg.icTrash,
          isManualPlaylist: d.isManualPlaylistView(),
          reveal: () => reveal(relativePath),
          removeFromPlaylist: () => d.removeFromUserPlaylist(relativePath ?? ""),
        }),
      );
    },
    revealInExplorer: (relativePath: string | undefined) => reveal(relativePath),
    renderPlayerRating: (s: number) => renderPlayerRating(s, ratingHooks()),
    patchAllItemsRating,
    updateTrackRatingBar: (i: number, r: number) => updateTrackRatingBar(i, r, ratingHooks()),
    setRating: (s: number) => setRating(s, ratingHooks()),
    setInlineRating: (i: number, s: number) => setInlineRating(i, s, ratingHooks()),
    loadFavorites: () => void loadFavorites(favHooks()),
    updateFavoriteButtons,
    toggleFavorite: (item: Parameters<typeof toggleFavorite>[0], btn: HTMLElement | null) =>
      toggleFavorite(item, btn, favHooks()),
    initEditModalRatingEvents: () => initEditModalRatingEvents(editHooks()),
    openEditModal: (i: number) => openEditModal(i, editHooks()),
    closeEditModal,
    submitEditModal: () => submitEditModal(editHooks()),
    loadFavoritesOrder: () => loadOrder(FAVORITES_ORDER_KEY),
    saveFavoritesOrder: (paths: string[]) =>
      saveOrder(cfg.folderOrderApiPath, FAVORITES_ORDER_KEY, "__favorites__", paths),
    loadFavoritesOrderAsync: (cb: (o: string[]) => void) =>
      loadOrderAsync(cfg.folderOrderApiPath, FAVORITES_ORDER_KEY, "__favorites__", cb),
    sortFavoritesByOrder: <T extends { relative_path: string }>(items: T[]) =>
      sortByOrder(items, loadOrder(FAVORITES_ORDER_KEY)),
    folderOrderKey: orderKey,
    loadFolderOrder: (p: string) => loadOrder(orderKey(p)),
    saveFolderOrder: (p: string, paths: string[]) =>
      saveOrder(cfg.folderOrderApiPath, orderKey(p), p || "__root__", paths),
    loadFolderOrderAsync: (p: string, cb: (o: string[]) => void) =>
      loadOrderAsync(cfg.folderOrderApiPath, orderKey(p), p || "__root__", cb),
    sortByFolderOrder: <T extends { relative_path: string }>(p: string, items: T[]) =>
      sortByOrder(items, loadOrder(orderKey(p))),
  };
}

export type LibraryWiring = ReturnType<typeof createLibraryWiring>;
