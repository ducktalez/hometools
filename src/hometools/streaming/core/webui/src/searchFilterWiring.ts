/**
 * Search/filter/track-list hook wiring. Replaces the hook-builder glue formerly
 * in `player_js/_search_filter.py`: global search, filter pipeline + chips,
 * filter popover, windowed rendering, row select, player-bar nav/actions,
 * track-list delegation, inline edit. Legacy callbacks come in via `deps`
 * (thunk, resolved per call, so declaration order in the closure script does
 * not matter).
 */

import { getState } from "./stateBridge";
import { getDom } from "./dom";
import { globalSearch, exitGlobalSearch, type SearchViewHooks } from "./searchView";
import { updateFilterChips, applyFilter, type FilterApplyHooks } from "./filterApply";
import {
  renderFilterPopoverBody,
  closeFilterPopover,
  toggleFilterPopover,
  type FilterPopoverHooks,
} from "./filterPopoverUi";
import {
  stopRenderObserver,
  appendTrackBatch,
  ensureRenderedTo,
  markActive,
  startWindowedRender,
  type RenderWindowHooks,
} from "./trackRenderWindow";
import { selectTrackRow } from "./rowSelect";
import { jumpToCurrentTrack, updatePlayerBarActions, type JumpHooks, type PlayerBarActionsHooks } from "./playerNav";
import { wireTrackListDelegation, type TrackListHooks } from "./trackListDelegation";
import { saveInlineTableEdit } from "./inlineEdit";
import { playAllCurrent } from "./playAll";
import { collectGenres } from "./catalogQuery";

type Fn = (...a: never[]) => unknown;

export interface SearchFilterCfg {
  itemNoun: string;
  filePlaceholder: string;
  icons: {
    folderPlay: string;
    filter: string;
    eye: string;
    starFilled: string;
    starEmpty: string;
    trash: string;
    dl: string;
    pin: string;
    edit: string;
    playlist: string;
    queue: string;
    dots: string;
  };
  debugFilter: boolean;
  batchSize: number;
  isVideoMode: boolean;
  metadataEditEnabled: boolean;
  playlistsEnabled: boolean;
  metadataEditPath: string;
  bpmMin: number;
  bpmMax: number;
}

/** Legacy closure functions/values the wiring still needs. */
export interface SearchFilterDeps {
  effectiveThreshold(): number;
  showHidden(): boolean;
  viewMode(): string;
  trackViewMode(): string;
  getFilter: FilterApplyHooks["getFilter"];
  setFilter: FilterPopoverHooks["setFilter"];
  locallyDeleted: FilterApplyHooks["locallyDeleted"];
  esc: SearchViewHooks["esc"];
  fmtTime(sec: number): string;
  toast: TrackListHooks["showToast"];
  anyToolActive(): boolean;
  toolFlags(): { active?: boolean; bpmCalc?: boolean };
  currentDupeIndex(): { paths?: unknown; safety?: unknown } | null;
  renderBpmPill: Fn;
  renderInlineRating: Fn;
  renderMoveWidget: Fn;
  showFolderView: SearchViewHooks["showFolderView"];
  showPlaylist: JumpHooks["showPlaylist"];
  enterTrackListView: SearchViewHooks["enterTrackListView"];
  playItem: SearchViewHooks["playItem"];
  contentsAt(path: string): { files: LegacyMediaItem[] };
  itemsUnder: JumpHooks["itemsUnder"];
  renderTracks: FilterApplyHooks["renderTracks"];
  updateFavoriteButtons(): void;
  updateAllDownloadButtons(): void;
  updateQueueButtons(): void;
  initPlaylistDragDrop(): void;
  renderFilterPopoverBody(): void;
  routerUpdate(): void;
  getAllFolders: PlayerBarActionsHooks["allFolders"];
  moveFileToFolder: PlayerBarActionsHooks["moveFileToFolder"];
  deleteTrackFromList: PlayerBarActionsHooks["deleteTrackFromList"];
  openTrackCtxMenu: PlayerBarActionsHooks["openTrackCtxMenu"];
  setInlineRating: TrackListHooks["setInlineRating"];
  openBpmAdjustMenu: TrackListHooks["openBpmAdjustMenu"];
  deleteTrackDownload: TrackListHooks["deleteTrackDownload"];
  cancelDownload: TrackListHooks["cancelDownload"];
  downloadTrack: TrackListHooks["downloadTrack"];
  toggleFavorite: TrackListHooks["toggleFavorite"];
  openEditModal: TrackListHooks["openEditModal"];
  loadUserPlaylists(): Promise<unknown>;
  openPlaylistModal(relativePath: string): void;
  removeFromQueue: TrackListHooks["removeFromQueue"];
  addToQueue: TrackListHooks["addToQueue"];
  revealInExplorer: TrackListHooks["revealInExplorer"];
  playTrack: TrackListHooks["playTrack"];
}

export function createSearchFilterWiring(cfg: SearchFilterCfg, deps: () => SearchFilterDeps) {
  const el = (k: keyof ReturnType<typeof getDom>) => getDom()[k] as HTMLElement;
  const input = () => el("searchInput") as HTMLInputElement;
  const sortSel = () => el("sortField") as HTMLInputElement;

  const searchHooks = (): SearchViewHooks => {
    const d = deps();
    return {
      effectiveThreshold: d.effectiveThreshold,
      showHidden: d.showHidden,
      itemNoun: cfg.itemNoun,
      esc: d.esc,
      filePlaceholder: cfg.filePlaceholder,
      icFolderPlay: cfg.icons.folderPlay,
      trackList: () => el("trackList"),
      enterTrackListView: d.enterTrackListView,
      showFolderView: d.showFolderView,
      playItem: d.playItem,
      markActive: markActiveW,
    };
  };

  const filterApplyHooks = (): FilterApplyHooks => {
    const d = deps();
    return {
      combinedBtn: () => el("filterCombinedBtn"),
      hiddenBtn: () => el("filterHiddenBtn"),
      getFilter: d.getFilter,
      icFilter: cfg.icons.filter,
      icEye: cfg.icons.eye,
      effectiveThreshold: d.effectiveThreshold,
      showHidden: d.showHidden,
      refreshOpenPopover: () => {
        if (document.getElementById("ht-filter-popover")) d.renderFilterPopoverBody();
      },
      searchValue: () => input().value,
      sortValue: () => sortSel().value,
      locallyDeleted: d.locallyDeleted,
      debugFilter: cfg.debugFilter,
      justRatedPath: () => getState()?.justRatedPath ?? null,
      savedFavorites: () => getState()?.savedFavorites ?? {},
      hasCustomPlaylist: () => !!getState()?.currentPlaylistId,
      renderTracks: d.renderTracks,
    };
  };

  const popoverHooks = (): FilterPopoverHooks => {
    const d = deps();
    return {
      genres: () => collectGenres(getState()?.playlistItems ?? []),
      getFilter: d.getFilter,
      setFilter: d.setFilter,
      icons: { starFilled: cfg.icons.starFilled, starEmpty: cfg.icons.starEmpty },
      esc: d.esc,
      onChange: () => {
        updateFilterChips(filterApplyHooks());
        applyFilter(undefined, filterApplyHooks());
        d.routerUpdate();
      },
    };
  };

  const renderWindowHooks = (): RenderWindowHooks => {
    const d = deps();
    return {
      trackList: () => el("trackList"),
      batchSize: cfg.batchSize,
      rowCtx: () => {
        const tf = d.toolFlags();
        const dupe = d.currentDupeIndex() || {};
        return {
          escHtml: d.esc,
          fmtTime: d.fmtTime,
          showOrig: d.anyToolActive(),
          currentIndex: getState()?.currentIndex ?? -1,
          bpmCalcEnabled: !!(tf.active && tf.bpmCalc),
          trackViewMode: d.trackViewMode(),
          isVideoMode: cfg.isVideoMode,
          metadataEditEnabled: cfg.metadataEditEnabled,
          playlistsEnabled: cfg.playlistsEnabled,
          itemNoun: cfg.itemNoun,
          bpmMin: cfg.bpmMin,
          bpmMax: cfg.bpmMax,
          dupePaths: dupe.paths || null,
          dupeSafety: dupe.safety || null,
          filePlaceholder: cfg.filePlaceholder,
          ic: {
            folderPlay: cfg.icons.folderPlay,
            trash: cfg.icons.trash,
            dl: cfg.icons.dl,
            pin: cfg.icons.pin,
            edit: cfg.icons.edit,
            playlist: cfg.icons.playlist,
            queue: cfg.icons.queue,
            dots: cfg.icons.dots,
          },
          renderBpmPill: d.renderBpmPill,
          renderInlineRating: d.renderInlineRating,
          renderMoveWidget: d.renderMoveWidget,
        } as unknown as ReturnType<RenderWindowHooks["rowCtx"]>;
      },
      decorateRows: () => {
        d.updateFavoriteButtons();
        d.updateAllDownloadButtons();
        d.updateQueueButtons();
      },
      maybeInitPlaylistDragDrop: () => {
        const st = getState();
        if (cfg.playlistsEnabled && st && st.inPlaylist && st.currentPlaylistId && d.viewMode() === "list") {
          d.initPlaylistDragDrop();
        }
      },
      wireDelegation: wireDelegation,
    };
  };

  function markActiveW(): void {
    markActive(renderWindowHooks());
  }

  function wireDelegation(): void {
    const d = deps();
    wireTrackListDelegation(el("trackList"), {
      metadataEditEnabled: cfg.metadataEditEnabled,
      playlistsEnabled: cfg.playlistsEnabled,
      itemNoun: cfg.itemNoun,
      setInlineRating: d.setInlineRating,
      openBpmAdjustMenu: d.openBpmAdjustMenu,
      deleteTrackDownload: d.deleteTrackDownload,
      cancelDownload: d.cancelDownload,
      downloadTrack: d.downloadTrack,
      toggleFavorite: d.toggleFavorite,
      openEditModal: d.openEditModal,
      openPlaylistModalFor: (rp) => {
        void d.loadUserPlaylists().then(() => d.openPlaylistModal(rp));
      },
      removeFromQueue: d.removeFromQueue,
      addToQueue: d.addToQueue,
      showToast: d.toast,
      moveFileToFolder: d.moveFileToFolder,
      deleteTrackFromList: d.deleteTrackFromList,
      openTrackCtxMenu: d.openTrackCtxMenu,
      revealInExplorer: d.revealInExplorer,
      playTrack: d.playTrack,
      selectTrackRow: (idx) => selectTrackRow(el("trackList"), idx),
      saveInlineTableEdit: (e) => saveInlineTableEdit(e, { editPath: cfg.metadataEditPath, toast: d.toast }),
    });
  }

  const updatePlayerBarActionsW = (): void => {
    const d = deps();
    updatePlayerBarActions({
      container: () => el("playerBarActions"),
      allFolders: d.getAllFolders,
      esc: d.esc,
      icDots: cfg.icons.dots,
      icTrash: cfg.icons.trash,
      moveFileToFolder: d.moveFileToFolder,
      deleteTrackFromList: d.deleteTrackFromList,
      openTrackCtxMenu: d.openTrackCtxMenu,
    });
  };

  return {
    globalSearch: (needle: string) => globalSearch(needle, searchHooks()),
    exitGlobalSearch: () => exitGlobalSearch(searchHooks()),
    playAllCurrent: () => {
      const d = deps();
      playAllCurrent({ filesAt: (p: string) => d.contentsAt(p).files, showPlaylist: d.showPlaylist });
    },
    updateFilterChips: () => updateFilterChips(filterApplyHooks()),
    applyFilter: (force?: boolean) => applyFilter(force, filterApplyHooks()),
    renderFilterPopoverBody: () => renderFilterPopoverBody(popoverHooks()),
    closeFilterPopover,
    toggleFilterPopover: (btn: HTMLElement) => toggleFilterPopover(btn, popoverHooks()),
    stopRenderObserver: () => stopRenderObserver(renderWindowHooks()),
    appendTrackBatch: () => appendTrackBatch(renderWindowHooks()),
    ensureRenderedTo: (idx: number) => ensureRenderedTo(idx, renderWindowHooks()),
    markActive: markActiveW,
    startWindowedRender: (tracks: LegacyMediaItem[]) => startWindowedRender(tracks, renderWindowHooks()),
    selectTrackRow: (idx: number) => selectTrackRow(el("trackList"), idx),
    jumpToCurrentTrack: () => {
      const d = deps();
      jumpToCurrentTrack({
        ensureRenderedTo: (i) => ensureRenderedTo(i, renderWindowHooks()),
        markActive: markActiveW,
        itemsUnder: d.itemsUnder,
        showPlaylist: d.showPlaylist,
      });
    },
    updatePlayerBarActions: updatePlayerBarActionsW,
    wireTrackListDelegation: wireDelegation,
    saveInlineTableEdit: (e: HTMLElement) => {
      const d = deps();
      saveInlineTableEdit(e, { editPath: cfg.metadataEditPath, toast: d.toast });
    },
  };
}

export type SearchFilterWiring = ReturnType<typeof createSearchFilterWiring>;
