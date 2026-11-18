/**
 * Track-render / offline / tools-panel hook wiring. Replaces the hook-builder
 * glue formerly in `player_js/_track_render.py`: renderTracks, offline library
 * (+ active-download registry), download buttons, recently played, tools panel,
 * BPM menu, inline rating markup. Legacy callbacks come in via `deps` (thunk,
 * resolved per call, so declaration order in the closure script does not matter).
 */

import { getState } from "./stateBridge";
import { getDom } from "./dom";
import { renderTracks, type RenderTracksHooks } from "./trackRender";
import { initOfflineLibrary } from "./offlineLibrary";
import { closeOfflineLibrary } from "./backNav";
import { updateOfflineFolderCount } from "./offlineCount";
import { loadRecentlyPlayed } from "./recentlyPlayed";
import {
  updateAllDownloadButtons,
  cancelDownload,
  downloadTrack,
  deleteTrackDownload,
  checkIfMediaCached,
  playOfflineOrStream,
  type DownloadHooks,
} from "./downloadButtons";
import { initToolsPanel, toolFlags, anyToolActive, openToolsPanel, closeToolsPanel } from "./toolsPanel";
import { openBpmAdjustMenu } from "./bpmMenu";
import { inlineRatingHtml } from "./inlineWidgets";

export interface TrackRenderCfg {
  itemNoun: string;
  debugFilter: boolean;
  softLimit: number;
  recentApiPath: string;
  filePlaceholder: string;
  ratingWriteEnabled: boolean;
  icDl: string;
  icCheck: string;
  icStarFilled: string;
  icStarEmpty: string;
  icChevronsDown: string;
  icRefresh: string;
  icChevronsUp: string;
  bpmCalcApiPath: string;
  bpmAdjustApiPath: string;
  bpmSetApiPath: string;
  bpmMin: number;
  bpmMax: number;
}

export interface TrackRenderDeps {
  esc(s: unknown): string;
  toast(msg: string): void;
  formatBytes(n: number): string;
  getFilter: RenderTracksHooks["getFilter"];
  effectiveThreshold(): number;
  showHidden(): boolean;
  stopRenderObserver(): void;
  startWindowedRender: RenderTracksHooks["startWindowedRender"];
  markActive(): void;
  openTrackPicker: RenderTracksHooks["openTrackPicker"];
  applyFilter(force?: boolean): void;
  showFolderView(): void;
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean): void;
  playItem(item: LegacyMediaItem, idx: number): void;
  enterTrackListView(o: Record<string, unknown>): void;
  destroyPlaylistDragDrop(): void;
  applyViewMode(): void;
  updatePlayerBarActions(): void;
  invalidateDupeMap(): void;
  refreshCatalog(): void;
  playDuplicates(): void;
  closeDupePanel(): void;
  routerUpdate(): void;
}

export function createTrackRenderWiring(cfg: TrackRenderCfg, deps: () => TrackRenderDeps) {
  const el = (k: keyof ReturnType<typeof getDom>) => getDom()[k] as HTMLElement;
  const activeDownloads: Record<string, { abort(): void }> = {};

  const lib = initOfflineLibrary({
    itemNoun: cfg.itemNoun,
    softLimit: cfg.softLimit,
    formatBytes: (n) => deps().formatBytes(n),
    currentStreamUrl: () => getState()?.currentStreamUrl ?? "",
    updateDownloadButtons: () => updateButtons(),
    applyFilter: () => deps().applyFilter(),
    showFolderView: () => deps().showFolderView(),
    enterTrackListView: (o) => deps().enterTrackListView(o),
    destroyPlaylistDragDrop: () => deps().destroyPlaylistDragDrop(),
  });

  const dlIcons = { icDl: cfg.icDl, icCheck: cfg.icCheck };
  const updateButtons = (): void => {
    void updateAllDownloadButtons(dlIcons);
  };
  const dlHooks = (): DownloadHooks => {
    const d = deps();
    return {
      icDl: cfg.icDl,
      icCheck: cfg.icCheck,
      itemNoun: cfg.itemNoun,
      softLimit: cfg.softLimit,
      formatBytes: d.formatBytes,
      ensureStorageBudget: (n, u) => lib.ensureStorageBudget(n, u),
      toast: d.toast,
      refreshLibrary: () => void lib.refresh(),
      updateButtons,
    };
  };

  const startToolsPanel = (): void => initToolsPanel({
    folderGrid: el("folderGrid"),
    showFolderView: () => deps().showFolderView(),
    applyViewMode: () => deps().applyViewMode(),
    applyFilter: (force) => deps().applyFilter(force),
    updatePlayerBarActions: () => deps().updatePlayerBarActions(),
    invalidateDupeMap: () => deps().invalidateDupeMap(),
    refreshCatalog: () => deps().refreshCatalog(),
    playDuplicates: () => deps().playDuplicates(),
    closeDupePanel: () => deps().closeDupePanel(),
    routerUpdate: () => deps().routerUpdate(),
  });

  return {
    /** Run after the legacy ar _trw = assignment (restores tool state, may re-enter via deps). */
    start: startToolsPanel,
    renderTracks(tracks: LegacyMediaItem[], force?: boolean): void {
      const d = deps();
      renderTracks(tracks as never, force, {
        itemNoun: cfg.itemNoun,
        debugFilter: cfg.debugFilter,
        trackList: el("trackList"),
        trackCount: el("trackCount"),
        searchInput: el("searchInput") as HTMLInputElement,
        sortField: el("sortField") as HTMLSelectElement,
        getFilter: d.getFilter,
        effectiveThreshold: d.effectiveThreshold,
        showHidden: d.showHidden,
        stopRenderObserver: d.stopRenderObserver,
        startWindowedRender: d.startWindowedRender,
        markActive: d.markActive,
        openTrackPicker: d.openTrackPicker,
      });
    },
    cancelDownload: (url: string, btn: Parameters<typeof cancelDownload>[1]) =>
      cancelDownload(url, btn, activeDownloads, { icDl: cfg.icDl, toast: deps().toast }),
    refreshOfflineLibrary: () => lib.refresh(),
    openOfflineLibrary: () => lib.open(),
    ensureStorageBudget: (n: number, protectedUrl: string) => lib.ensureStorageBudget(n, protectedUrl),
    closeOfflineLibrary: () => closeOfflineLibrary({ showFolderView: () => deps().showFolderView() }),
    updateOfflineFolderCount: () => void updateOfflineFolderCount(el("downloadedPill") as never),
    loadRecentlyPlayed: () =>
      loadRecentlyPlayed({
        apiPath: cfg.recentApiPath,
        esc: deps().esc,
        placeholder: cfg.filePlaceholder,
        player: el("player") as HTMLMediaElement,
        showPlaylist: deps().showPlaylist,
        playItem: deps().playItem,
      }),
    updateAllDownloadButtons: updateButtons,
    downloadTrack: (url: string, title: string | undefined, btn: Parameters<typeof downloadTrack>[2], meta: Parameters<typeof downloadTrack>[3]) =>
      downloadTrack(url, title, btn, meta, activeDownloads, dlHooks()),
    deleteTrackDownload: (url: string, btn: Parameters<typeof deleteTrackDownload>[1]) =>
      deleteTrackDownload(url, btn, dlHooks()),
    checkIfMediaCached,
    playOfflineOrStream,
    anyToolActive,
    toolFlags,
    openToolsPanel,
    closeToolsPanel,
    renderInlineRating: (t: { rating?: number }, idx: number) =>
      inlineRatingHtml(t.rating, idx, cfg.ratingWriteEnabled, cfg.icStarFilled, cfg.icStarEmpty),
    openBpmAdjustMenu: (idx: number, btn: HTMLElement) =>
      openBpmAdjustMenu(idx, btn, {
        calcPath: cfg.bpmCalcApiPath,
        adjustPath: cfg.bpmAdjustApiPath,
        setPath: cfg.bpmSetApiPath,
        bpmMin: cfg.bpmMin,
        bpmMax: cfg.bpmMax,
        icons: { chevronsDown: cfg.icChevronsDown, refresh: cfg.icRefresh, chevronsUp: cfg.icChevronsUp },
        calcEnabled: () => {
          const f = toolFlags() as { active?: boolean; bpmCalc?: boolean };
          return !!(f.active && f.bpmCalc);
        },
        toast: deps().toast,
      }),
  };
}

export type TrackRenderWiring = ReturnType<typeof createTrackRenderWiring>;
