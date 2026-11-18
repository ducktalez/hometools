/**
 * Catalog/queue hook wiring. Replaces the hook-builder glue formerly in
 * `player_js/_queue.py`: play-next, catalog fetch/refresh, extra folders and
 * lazy folder rating refresh. Legacy callbacks come in via `deps` (thunk,
 * resolved per call).
 */

import { getDom } from "./dom";
import { dequeueNext, playNextItem, type PlayNextHooks } from "./playNext";
import {
  scheduleBackgroundRefresh,
  forceBackgroundRefresh,
  triggerSilentRefresh,
  refreshPoll,
  refreshCatalog,
  type CatalogFetchHooks,
} from "./catalogFetch";
import { loadExtraFolders, addExtraFolder, removeExtraFolder, type ExtraFolderHooks } from "./extraFolders";
import { refreshFolderRatings, resetRatingRefresh } from "./ratingRefresh";
import { setWasPlaying } from "./bgPlayback";

export interface CatalogCfg {
  apiPath: string;
  apiBase: string;
  isVideo: boolean;
  ratingWriteEnabled: boolean;
  icPlay: string;
}

export interface CatalogDeps {
  playFromQueue(i: number): void;
  playTrack(i: number): void;
  showIndexingToast(detail: string, cache: unknown): void;
  hideIndexingToast(): void;
  applyLocalMutations(items: LegacyMediaItem[]): LegacyMediaItem[];
  invalidateDupeMap(): void;
  invalidateFolderCache(): void;
  saveCatalogCache(items: LegacyMediaItem[]): void;
  clearCatalogCache(): void;
  /** Clear in place: window._locallyDeletedPaths must keep its identity. */
  clearLocalDeleted(): void;
  showFolderView(): void;
  itemsUnder(path: string): LegacyMediaItem[];
  applyFilter(): void;
  toast(msg: string): void;
}

export function createCatalogWiring(cfg: CatalogCfg, deps: () => CatalogDeps) {
  const playNextHooks = (): PlayNextHooks => {
    const d = deps();
    const dom = getDom();
    return {
      player: dom.player as unknown as PlayNextHooks["player"],
      playFromQueue: d.playFromQueue,
      playTrack: d.playTrack,
      setWasPlaying,
      showStopped: () => {
        if (dom.btnPlay) dom.btnPlay.innerHTML = cfg.icPlay;
      },
    };
  };

  const fetchHooks = (): CatalogFetchHooks => {
    const d = deps();
    return {
      apiPath: cfg.apiPath,
      showIndexingToast: d.showIndexingToast,
      hideIndexingToast: d.hideIndexingToast,
      applyLocalMutations: d.applyLocalMutations,
      invalidateCaches: () => {
        d.invalidateDupeMap();
        d.invalidateFolderCache();
      },
      saveCache: d.saveCatalogCache,
      clearCache: d.clearCatalogCache,
      clearLocalDeleted: d.clearLocalDeleted,
      resetRatingRefresh,
      showFolderView: d.showFolderView,
      itemsUnder: d.itemsUnder,
      applyFilter: d.applyFilter,
      toast: d.toast,
    };
  };

  const extraHooks = (): ExtraFolderHooks => {
    const d = deps();
    return {
      apiBase: cfg.apiBase,
      isVideo: cfg.isVideo,
      toast: d.toast,
      refreshCatalog: () => refreshCatalog(fetchHooks()),
      showFolderView: d.showFolderView,
    };
  };

  return {
    dequeueNext: (): boolean => dequeueNext(playNextHooks()),
    playNextItem: (): void => playNextItem(playNextHooks()),
    scheduleBackgroundRefresh: (delay?: number): void => scheduleBackgroundRefresh(fetchHooks(), delay),
    forceBackgroundRefresh: (): void => forceBackgroundRefresh(fetchHooks()),
    triggerSilentRefresh: (): void => triggerSilentRefresh(fetchHooks()),
    refreshPoll: (): void => refreshPoll(fetchHooks()),
    refreshCatalog: (): void => refreshCatalog(fetchHooks()),
    fetchHooks,
    loadExtraFolders: (cb?: () => void): Promise<void> => loadExtraFolders(extraHooks(), cb),
    addExtraFolder: (): void => addExtraFolder(extraHooks()),
    removeExtraFolder: (): void => removeExtraFolder(extraHooks()),
    refreshFolderRatings: (folderItems: Array<{ relative_path: string }>): void =>
      refreshFolderRatings(folderItems, {
        enabled: cfg.ratingWriteEnabled,
        apiBase: cfg.apiBase,
        applyFilter: deps().applyFilter,
      }),
  };
}

export type CatalogWiring = ReturnType<typeof createCatalogWiring>;
