/**
 * Folder-browse hook wiring. Replaces the hook-builder glue formerly in
 * `player_js/_folder_browse.py`: folder view, language picker, folder
 * navigation, view-entry/header state, folder playlist, resume, back and
 * global-search wiring. The modules reference each other directly here, so
 * only the remaining legacy callbacks come in via `deps` (a thunk, resolved
 * per call, so declaration order in the closure script does not matter).
 */

import { getState } from "./stateBridge";
import { getDom } from "./dom";
import { showFolderView, type FolderViewHooks, type FolderViewIcons } from "./folderView";
import {
  closeLangPicker,
  showLangPicker,
  initGlobalSearch,
  hideGlobalSearch,
  initFilterBarScrollReveal,
  type LangPickerHooks,
  type GlobalSearchHooks,
} from "./folderBrowseUi";
import { navigateInto, playAllIn, showPlaylist, type FolderNavHooks, type ShowPlaylistHooks } from "./playAll";
import { applyHeaderState, enterTrackListView, enterFolderGridView, type ViewHooks } from "./viewEntry";
import { restoreLastEpisode } from "./resume";
import { goBack, type BackHooks } from "./backNav";
import type { FolderCardOpts } from "./folderCards";

export interface FolderWiringCfg {
  itemNoun: string;
  defaultLang: string;
  playlistsEnabled: boolean;
  offlineEnabled: boolean;
  recentEnabled: boolean;
  playlistsApiPath: string;
  recentApiPath: string;
  icons: FolderViewIcons;
  audiobookDirs: string[];
  langNames: Record<string, string>;
  langToFlag: Record<string, string>;
  folderPlaceholder: string;
  filePlaceholder: string;
  /** Page title captured at startup. */
  originalTitle: string;
}

export type FolderWiringDeps = Pick<
  FolderViewHooks,
  | "esc"
  | "toast"
  | "toolActive"
  | "contentsAt"
  | "loadRecentlyPlayed"
  | "openOfflineLibrary"
  | "updateOfflineFolderCount"
  | "triggerSilentRefresh"
  | "destroyPlaylistDragDrop"
  | "showUserPlaylistView"
  | "playUserPlaylist"
  | "openSmartPlaylistEditor"
  | "refreshSmartPlaylist"
  | "renameUserPlaylist"
  | "deleteUserPlaylist"
> &
  Pick<FolderNavHooks, "loadLastPlayedLocal"> &
  Pick<
    ShowPlaylistHooks,
    "sortByFolderOrder" | "refreshFolderRatings" | "playTrack" | "loadFolderOrderAsync" | "loadFolderOrder" | "applyFilter" | "routerUpdate"
  > &
  Pick<ViewHooks, "renderBreadcrumb" | "applyViewMode"> &
  Pick<BackHooks, "exitGlobalSearch"> &
  Pick<GlobalSearchHooks, "globalSearch"> &
  Pick<LangPickerHooks, "cleanFolderName"> & {
    markActive(): void;
    fmtTime(sec: number): string;
    /** `_view.viewMode` */
    viewMode(): string;
    compositeFlagHtml: FolderCardOpts["compositeFlagHtml"];
    langBadgesHtml: FolderCardOpts["langBadgesHtml"];
  };

export function createFolderWiring(cfg: FolderWiringCfg, deps: () => FolderWiringDeps) {
  const el = (k: keyof ReturnType<typeof getDom>) => getDom()[k] as HTMLElement;

  const viewHooks = (): ViewHooks => {
    const d = deps();
    return {
      dom: {
        headerTitle: el("headerTitle"),
        backBtn: el("backBtn"),
        playAllBtn: el("playAllBtn"),
        folderGrid: el("folderGrid"),
        trackView: el("trackView"),
        filterBar: el("filterBar"),
        playerBar: el("playerBar"),
        trackCount: el("trackCount"),
        searchInput: el("searchInput") as HTMLInputElement,
        player: el("player") as HTMLMediaElement,
      },
      originalTitle: cfg.originalTitle,
      renderBreadcrumb: d.renderBreadcrumb,
      applyViewMode: d.applyViewMode,
      initGlobalSearch: () => initGlobalSearch({ globalSearch: d.globalSearch, exitGlobalSearch: d.exitGlobalSearch }),
      hideGlobalSearch,
      initFilterBarScrollReveal: () => initFilterBarScrollReveal(el("filterBar")),
      applyFilter: () => d.applyFilter(),
      routerUpdate: d.routerUpdate,
    };
  };

  const enterTrackList: ViewHooksOpts<"track"> = (o) => enterTrackListView(o, viewHooks());
  const enterFolderGrid: ViewHooksOpts<"grid"> = (o) => enterFolderGridView(o, viewHooks());

  const navHooks = (): FolderNavHooks => {
    const d = deps();
    return {
      showFolderView: showFolderViewW,
      triggerSilentRefresh: d.triggerSilentRefresh,
      loadLastPlayedLocal: d.loadLastPlayedLocal,
      showPlaylist: showPlaylistW,
    };
  };

  const navInto = (name: string) => navigateInto(name, navHooks());
  const playAll = (name: string) => playAllIn(name, navHooks());

  const langPicker = (card: HTMLElement, variants: Parameters<typeof showLangPicker>[1], playMode: boolean): void => {
    const d = deps();
    showLangPicker(card, variants, playMode, {
      esc: d.esc,
      itemNoun: cfg.itemNoun,
      langToFlag: cfg.langToFlag,
      langNames: cfg.langNames,
      cleanFolderName: d.cleanFolderName,
      playAllIn: playAll,
      navigateInto: navInto,
    });
  };

  function showFolderViewW(): void {
    const d = deps();
    showFolderView({
      folderGrid: el("folderGrid"),
      itemNoun: cfg.itemNoun,
      defaultLang: cfg.defaultLang,
      playlistsEnabled: cfg.playlistsEnabled,
      offlineEnabled: cfg.offlineEnabled,
      recentEnabled: cfg.recentEnabled,
      playlistsApiPath: cfg.playlistsApiPath,
      icons: cfg.icons,
      esc: d.esc,
      toast: d.toast,
      cardOpts: (showOrigNames) => ({
        escHtml: d.esc,
        viewMode: d.viewMode(),
        showOrigNames,
        isVideo: cfg.itemNoun === "video",
        itemNoun: cfg.itemNoun,
        defaultLang: cfg.defaultLang,
        audiobookDirs: cfg.audiobookDirs,
        langNames: cfg.langNames,
        folderPlaceholder: cfg.folderPlaceholder,
        filePlaceholder: cfg.filePlaceholder,
        icStar: cfg.icons.star,
        icFolderPlay: cfg.icons.folderPlay,
        compositeFlagHtml: d.compositeFlagHtml,
        langBadgesHtml: d.langBadgesHtml,
      }),
      toolActive: d.toolActive,
      contentsAt: d.contentsAt,
      destroyPlaylistDragDrop: d.destroyPlaylistDragDrop,
      enterFolderGridView: enterFolderGrid,
      showPlaylist: showPlaylistW,
      loadRecentlyPlayed: d.loadRecentlyPlayed,
      openOfflineLibrary: d.openOfflineLibrary,
      updateOfflineFolderCount: d.updateOfflineFolderCount,
      showUserPlaylistView: d.showUserPlaylistView,
      playUserPlaylist: d.playUserPlaylist,
      openSmartPlaylistEditor: d.openSmartPlaylistEditor,
      refreshSmartPlaylist: d.refreshSmartPlaylist,
      renameUserPlaylist: d.renameUserPlaylist,
      deleteUserPlaylist: d.deleteUserPlaylist,
      navigateInto: navInto,
      playAllIn: playAll,
      showLangPicker: langPicker,
      triggerSilentRefresh: d.triggerSilentRefresh,
    });
  }

  function restoreEpisode(): void {
    const d = deps();
    restoreLastEpisode({
      loadLastPlayedLocal: d.loadLastPlayedLocal as never,
      recentEnabled: cfg.recentEnabled,
      recentApiPath: cfg.recentApiPath,
      selectResume: (idx) => {
        const st = getState();
        if (st) st.currentIndex = idx;
        d.markActive();
        const li = el("trackList").querySelector('[data-index="' + idx + '"]');
        if (li) li.scrollIntoView({ block: "center", behavior: "smooth" });
      },
      toast: d.toast as never,
      fmtTime: d.fmtTime,
    });
  }

  function showPlaylistW(items: LegacyMediaItem[], autoplay?: boolean, startIdx?: number): void {
    const d = deps();
    showPlaylist(items, autoplay, startIdx, {
      destroyPlaylistDragDrop: d.destroyPlaylistDragDrop,
      sortByFolderOrder: d.sortByFolderOrder,
      enterTrackListView: enterTrackList,
      refreshFolderRatings: d.refreshFolderRatings,
      playTrack: d.playTrack,
      restoreLastEpisode: restoreEpisode,
      loadFolderOrderAsync: d.loadFolderOrderAsync,
      loadFolderOrder: d.loadFolderOrder,
      applyFilter: () => d.applyFilter(),
      routerUpdate: d.routerUpdate,
    });
  }

  return {
    showFolderView: showFolderViewW,
    closeLangPicker,
    showLangPicker: langPicker,
    navigateInto: navInto,
    playAllIn: playAll,
    applyHeaderState: (o: Parameters<typeof applyHeaderState>[0]) => applyHeaderState(o, viewHooks()),
    enterTrackListView: enterTrackList,
    enterFolderGridView: enterFolderGrid,
    showPlaylist: showPlaylistW,
    restoreLastEpisode: restoreEpisode,
    goBack(): void {
      const d = deps();
      goBack({ exitGlobalSearch: d.exitGlobalSearch, showFolderView: showFolderViewW, contentsAt: d.contentsAt });
    },
    initGlobalSearch(): void {
      const d = deps();
      initGlobalSearch({ globalSearch: d.globalSearch, exitGlobalSearch: d.exitGlobalSearch });
    },
    hideGlobalSearch,
    initFilterBarScrollReveal: () => initFilterBarScrollReveal(el("filterBar")),
  };
}

type ViewHooksOpts<K extends "track" | "grid"> = (
  o: K extends "track" ? Parameters<typeof enterTrackListView>[0] : Parameters<typeof enterFolderGridView>[0],
) => void;

export type FolderWiring = ReturnType<typeof createFolderWiring>;
