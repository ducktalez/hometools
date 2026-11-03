/**
 * hometools streaming player UI — entry point.
 *
 * STATUS (docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration"):
 *   Phase 1 (scaffold), Phase 2 (#ht-config extraction, in _html.py),
 *   Phase 3 (render_player_js() reads CFG.* at runtime) and Phase 4
 *   (FastAPI StaticFiles mount, see server_utils/_static.py) are done.
 *   Phase 5 (module-by-module port) has its **first slice** here: the
 *   three dependency-free pure helpers `fmtTime`/`escHtml`/`formatBytes`
 *   that used to be defined in `player_js/_core.py`. They were chosen
 *   first because they have zero references to any other identifier in
 *   the (still Python-generated) legacy script — a precondition for a
 * safe module boundary given how tightly the remaining `player_js/*.py`
 * fragments are coupled (see docs/IMPLEMENTATION_PLAN.md Design
 * Discussions for the follow-up plan on that).
 *
 * Latest slice: filterApply.ts (updateFilterChips + applyFilter pipeline, from
 * _search_filter.py; playlistItems via htState, filter state/DOM/render via hooks).
 *
 * Previous slice: trackRenderWindow.ts (windowed rendering: batch append, sentinel/
 * observer, ensureRenderedTo, markActive, from _search_filter.py + renderTracks;
 * window state private, _rgKey/row-context/decoration via hooks).
 *
 * Previous slice: playerNav.ts (jumpToCurrentTrack + updatePlayerBarActions wiring,
 * from _search_filter.py; state via htState, actions via hooks; fixes undefined
 * _deleteItem in the player-bar trash button).
 *
 * Previous slice: inlineEdit.ts (_saveInlineTableEdit, from _search_filter.py; items
 * via htState, endpoint/toast via hooks).
 *
 * Previous slice: searchView.ts (globalSearch/renderSearchResults/navigate/exit, from
 * _search_filter.py; state via htState, view effects via hooks).
 *
 * Previous slice: trackListDelegation.ts (track-list click/change/focusout/keydown/
 * dblclick delegation, from _search_filter.py; handler refs private, actions via
 * hooks; fixes dblclick listener stacking on re-wire).
 *
 * Previous slice: filterPopoverUi.ts (filter popover wiring/open/close, from
 * _search_filter.py; cleanup handle private, filter state via hooks).
 *
 * Previous slice: catalogRefresh.ts (catalogChanged, refresh toast/info texts,
 * patchRatingsInPlace — pure decisions from _queue.py; fetch/cache orchestration
 * stays legacy).
 *
 * Previous slice: queuePanelUi.ts (queue panel height sync, drag-resize, peek handle,
 * from _queue.py; DOM nodes/_queueOpen/_queueUserHeight via args+hooks).
 *
 * Previous slice: queueDragDrop.ts (queue-panel drag reorder, from _queue.py; drag
 * state + _queueDndCleanup private, move/render via hooks).
 *
 * Previous slice: bootstrap.ts (startup sequence catalog -> router -> favorites ->
 * playlists -> root view -> sync, from _drag_drop_init.py; all steps via hooks).
 *
 * Previous slice: playlistModalEvents.ts (add-to-playlist modal DOM events, from
 * _drag_drop_init.py; playlistAddPath via htState, actions via hooks).
 *
 * Previous slice: swipe.ts (swipe-right = back, from _drag_drop_init.py; state private,
 * inPlaylist/currentPath via htState, goBack via hook).
 *
 * Previous slice: playlistDragDrop.ts (initPlaylistDragDrop/destroy + private drag
 * state/_dndCleanup, from _drag_drop_init.py + _smart_playlists.py; reorder via hook).
 *
 * Previous slice: viewEntry.ts (applyHeaderState/enterTrackListView/enterFolderGridView,
 * from _folder_browse.py; DOM elements + callbacks via hooks).
 *
 * Previous slice: folderBrowseUi.ts (lang picker, filter-bar scroll reveal, header
 * search wiring, playlist kebab items, from _folder_browse.py; private state moved,
 * htState.globalSearchActive added).
 *
 * Previous slice: playlistViews.ts (showUserPlaylistView/playUserPlaylist + add-to-
 * playlist modal, from _smart_playlists.py; htState.playlistAddPath added).
 *
 * Previous slice: playlistReorder.ts (reorderPlaylistItem/_applyPlaylistUpdate, from
 * _smart_playlists.py; htState.currentPlaylistId added; movePlaylistItem was dead).
 *
 * Previous slice: smartEditor.ts (editor state/wiring/save, from
 * _smart_playlists.py; _smartEditorState now module-private).
 *
 * Previous slice: playlistActions.ts (delete/rename/add/createAndAdd with optimistic
 * UI, from _smart_playlists.py; view side effects via hooks object).
 *
 * Previous slice: playlistSync.ts (loadUserPlaylists/sync polling/snapshot,
 * from _playlists.py; htState.userPlaylists+playlistRevision added, timer
 * private). _playlists.py now only holds thin wrappers + refreshSmartPlaylist.
 *
 * Previous slice: resume.ts (findResumeLocal/findResumeRecent, from
 * _folder_browse.py::_restoreLastEpisode). New pytest tests/test_webui_bridges.py
 * checks every `window._x(` call in player_js/*.py is bridged here.
 *
 * Previous slice: collectAllPlaylistRelPaths/resolveAllPlaylistItems/
 * buildSmartSubmit (smartPlaylist.ts, from _smart_playlists.py).
 *
 * Previous slice: resolvePlaylistItems (smartPlaylist.ts, from _playlists.py;
 * globals explicit, legacy keeps thin wrapper).
 *
 * Previous slice: evictForBudget (offlineDb.ts) + pickEvictionVictims
 * (offlineDownloads.ts), from _track_render.py::pruneOldDownloads. Legacy
 * keeps pruneOldDownloads as thin wrapper (UI refresh).
 *
 * Previous slice: offlineDb.ts (IndexedDB layer from _track_render.py;
 * downloadDB handle moved as private state). Tested with fake-indexeddb.
 *
 * Previous slice: folderContents.ts (contentsAt, from _queue.py — allItems +
 * LANG_GROUPS explicit; legacy keeps bare-name wrapper). First port with a
 * vitest behaviour test (test/folderContents.test.ts).
 *
 * Previous slice: resolveNext (queue.ts, from _library_tools.py::
 * _resolveNextForCrossfade) + replaceItemFields (catalogQuery.ts, from
 * _patchAllItemsRating — arrays explicit). Lyrics double-listener removed.
 *
 * Previous slice: queue.ts (queueIndexOf/queueAdd/queueRemoveAt/queueClear,
 * data half of _core.py's queue block). htState.userQueue added (getter+
 * setter) — clearQueue reassigns, so plain window-bridge was not enough.
 *
 * Previous slice: intro.ts (parseIntro/introButtonMode/patchIntroLocal, from
 * _core.py's skip-intro block). Pure decision/parse logic only; DOM, fetch
 * and _intro* IIFE vars stay in _core.py.
 *
 * Previous slice: filterChain.ts (applyFilterChain, from
 * _search_filter.py::applyFilter()'s normal-mode + DEBUG_FILTER-mode
 * rating/favorite/genre/search annotate-and-filter chain). showHidden/
 * filterRating/filterFav/filterGenre/_effectiveThreshold/_justRatedPath/
 * _savedFavorites/DEBUG_FILTER bundled into one explicit options object
 * (FilterChainOptions) instead of closure reads; the DOM reads
 * (searchInput.value/sortField.value) and renderTracks() call stay in
 * applyFilter() itself.
 *
 * Previous slice: search.ts (buildFolderMatches/searchItems, from
 * _search_filter.py::globalSearch()'s folder-match + item-match halves).
 * allItems/hiddenActive/_effectiveThreshold now explicit params; the DOM/
 * state-mutation half (playlistItems/filteredItems/_enterTrackListView/
 * renderSearchResults) stays in globalSearch() itself.
 *
 * Previous slice: sortTracks added to catalogQuery.ts (from
 * _search_filter.py::applyFilter()'s inline comparator). Explicit params
 * sortBy/hasCustomPlaylist (was sortField.value DOM read + _currentPlaylistId
 * global read).
 *
 * Previous slice: offlineUrl.ts (getOfflineUrl/currentOfflineUrl, from
 * _track_render.py + the currentOfflineUrl var in _core.py). State-mitnehmen
 * pattern: currentOfflineUrl lived in _core.py but was only read/written by
 * these two functions in _track_render.py — moved here as module-private
 * state, no htState bridge needed. Only getOfflineUrl is called from
 * not-yet-ported code (playOfflineOrStream), so only it is bridged.
 *
 * Previous slice: shuffle.ts (fisherYates/buildWeightedQueue/buildNormalQueue/
 * rebuildShuffleQueue/nextIndex/prevIndex, from _library_tools.py) — first
 * consumer of the htState getter/setter bridge (stateBridge.ts): these
 * read AND write shuffleQueue/shufflePos, so explicit params were not
 * enough. Legacy code keeps mutating the same vars directly.
 *
 * Previous slice: toast.ts (showToast, from _core.py) and folderCache.ts
 * (_getAllFolders/_invalidateFolderCache + its cache var, from
 * _library_tools.py) — both had module-private state, moved with the code.
 *
 * Previous slice: clickGuard.ts (wasDrag + its private pointer state and
 * capture listeners, from _core.py) and collectGenres in catalogQuery.ts
 * (from _search_filter.py, playlistItems now explicit param).
 *
 * Previous slice: itemsUnder added to catalogQuery.ts (from _queue.py).
 * allItems explicit param (was closure read) — _queue.py keeps a thin
 * bare-name wrapper forwarding to window._itemsUnder(path, allItems), so
 * all 13 existing call sites across other player_js/*.py fragments stay
 * unchanged.
 *
 * Previous slice: smartRenderRuleRow added to smartPlaylist.ts (from
 * _playlists.py). userPlaylists/ownId/escHtmlFn now explicit params (was
 * _userPlaylists/_smartEditorState reads + bare escHtml call).
 *
 * Previous slice: estimateOfflineStorage added to offlineDownloads.ts (from
 * _track_render.py). softLimit now explicit param (was OFFLINE_SOFT_LIMIT
 * global) — call sites pass it in.
 *
 * Previous slice: episodeGaps.ts (withMissingEpisodes, from _search_filter.py).
 * Pure array transform, no window reads.
 *
 * Previous slice: langDetect.ts (detectLangFromName/detectSubLangFromName,
 * from _queue.py). Pure regex tables. langBadgesHtml/compositeFlagHtml stay
 * Python — need LANG_TO_FLAG SVG markup, single source _svg.py.
 *
 * Previous slice: offlineDownloads.ts (formatDate/sortDownloads/
 * getAppDownloadUsage, from _track_render.py). Pure data helpers, no window
 * reads.
 *
 * Previous slice: `_smartFieldType`/`_smartOpsFor` + `SMART_FIELDS`/
 * `SMART_OPS_BY_TYPE` (formerly in `player_js/_playlists.py`), added to the
 * existing `smartPlaylist.ts` module. Read-only constants/pure lookups —
 * bridged with a plain assignment (like `originalTitle`), not the explicit-
 * parameter pattern `evaluateSmartPlaylist` uses, since nothing mutates them.
 *
 * Previous slice: catalogCache.ts (`_saveCatalogCache`/`_loadCatalogCache`/
 * `_clearCatalogCache`/`_saveLastPlayedLocal`/`_loadLastPlayedLocal`/
 * `_applyLocalMutations`, formerly in `player_js/_core.py`). These read the
 * `#ht-config` `apiPath` (already parsed as `cfg` below) instead of the
 * legacy `API_PATH` var, and `_applyLocalMutations` takes
 * `window._locallyDeletedPaths` explicitly — `_core.py` now bridges that
 * object onto `window` right after declaring it (see that file and
 * `legacy-globals.d.ts`).
 *
 * Bridge pattern while the migration is incomplete: this bundle is built
 * in IIFE format (see vite.config.ts), NOT as an ES module, and every
 * ported symbol is explicitly assigned onto `window` at the bottom of
 * this file. `_html.py` renders this bundle's `<script src="...">` tag
 * BEFORE the remaining Python-generated inline `<script>{js}</script>`,
 * so bare identifier references like `fmtTime(...)` inside that legacy
 * script resolve through the normal JS scope chain to `window.fmtTime`
 * — exactly as if it had been declared locally. Do NOT rename these
 * functions here without also updating every call site still living in
 * `player_js/*.py` (grep for the identifier first).
 *
 * Remaining migration plan:
 *   5. Port the rest of player_js/_core.py, _folder_browse.py, etc. one
 *      at a time, keeping tests/test_feature_parity.py and
 *      tests/test_streaming_player_ui.py green after each module.
 *   6. Delete the corresponding Python string-generator module once its
 *      .ts replacement has full parity, then delete _player_js.py/_css.py
 *      and the esprima-based tests/test_js_syntax.py entirely.
 */

import { renderBpmPill } from "./metricPill";
import { needsConversion, filenameFromPath, parentPath, leafName, currentFolderOf } from "./pathUtils";
import { _fmtDuration, _fmtFileSize, _fmtDate, _normalizeStem, _dupeKey, _isDupeGroupSafe } from "./dupeUtils";
import { cleanFolderName, renderBreadcrumbHtml } from "./breadcrumb";
import { formatDate, sortDownloads, getAppDownloadUsage, estimateOfflineStorage, storageSummaryView, readyStreamUrls, offlineDownloadListHtml } from "./offlineDownloads";
import type { OfflineStorageInfo, StorageSummaryView } from "./offlineDownloads";
import { detectLangFromName, detectSubLangFromName, langBadgesHtml, compositeFlagHtml } from "./langDetect";
import {
  progressApiBase,
  buildProgressPayload,
  getProgressPath,
  setProgressPath,
  cancelProgressTimer,
  saveProgressNow,
  saveProgressDebounced,
  clearProgressFor,
  loadAndSeekProgress,
} from "./progress";
import { filterPopoverBodyHtml, filterCombinedChipView, filterHiddenChipView } from "./filterPopover";
import { FAVORITES_ORDER_KEY, folderOrderKey, loadOrder, sortByOrder } from "./customOrder";
import { buildDuplicateIndex } from "./dupeUtils";
import { nextShuffleMode, nextRepeatMode, shuffleBtnView, repeatBtnView, playerRatingStars, ratingBarWidthPct, editModalRatingStars, toggleEditRating, favoriteBtnView } from "./playerControls";
import { withMissingEpisodes } from "./episodeGaps";
import {
  evaluateSmartPlaylist,
  smartFieldType,
  smartOpsFor,
  smartRenderRuleRow,
  resolvePlaylistItems,
  collectAllPlaylistRelPaths,
  resolveAllPlaylistItems,
  buildSmartSubmit,
  SMART_FIELDS,
  SMART_OPS_BY_TYPE,
} from "./smartPlaylist";
import { getRecentMoveTargets, saveRecentMoveTarget } from "./recentMoveTargets";
import { itemsUnder, collectGenres, sortTracks, replaceItemFields, findItemByStreamUrl, indexOfPath, ratingToastLabel, withoutPath, isBeforeIndex } from "./catalogQuery";
import { buildFolderMatches, searchItems } from "./search";
import { applyFilterChain } from "./filterChain";
import { parseIntro, introButtonMode, patchIntroLocal } from "./intro";
import { queueIndexOf, queueAdd, queueRemoveAt, queueClear, queueMove, resolveNext } from "./queue";
import { contentsAt } from "./folderContents";
import { folderCardHtml, fileCardHtml } from "./folderCards";
import { trackRowsHtml, searchFolderRowHtml, searchResultRowHtml } from "./trackRows";
import { inlineRatingHtml, moveWidgetHtml } from "./inlineWidgets";
import { dupePanelBodyHtml, queuePanelHtml, ctxMenuHtml } from "./panelBodies";
import { playerBarActionsHtml, bpmAdjustMenuHtml } from "./playerBarHtml";
import { toolsRowHtml, favoritesCardHtml, playlistCardHtml } from "./rootCards";
import { smartEditorModalHtml, playlistModalListHtml } from "./smartEditorModal";
import { batchEnd, renderTargetFor, jumpTarget } from "./renderWindow";
import { indexingToastHtml, TRACK_TABLE_HEADER_HTML, viewToggleView } from "./chromeHtml";
import { initLyricsPanel } from "./lyricsPanel";
import { closeCtxMenu, openCtxMenu, revealInExplorer } from "./ctxMenu";
import { openDupePanel, closeDupePanel, collectDupeItems } from "./dupePanel";
import { deleteTrackFromList, deleteDuplicateFile, removeGoneTrack, moveFileToFolder } from "./libraryOps";
import { loadFavorites, updateFavoriteButtons, toggleFavorite } from "./favorites";
import { loadExtraFolders, addExtraFolder, removeExtraFolder, addExtraFolderPlaceholders, markExtraFolderCards, extraFolderAliases } from "./extraFolders";
import { isCrossfading, crossfadeCleanup, startCrossfade, finishCrossfade } from "./crossfade";
import { initPip, isPipActive, exitPip } from "./pip";
import { playAllCurrent } from "./playAll";
import { wasPlaying, setWasPlaying, initBackgroundPlayback } from "./bgPlayback";
import { activeMedia, updateMediaSession } from "./mediaSession";
import { syncShufflePosition, beginPlayback } from "./playbackStart";
import { showNowPlaying } from "./nowPlaying";
import { togglePlay, handlePreviousTrack } from "./transport";
import { getBgAudio, bgAudioIsActive, stopBgSync, startBgMirror } from "./bgAudio";
import { initEditModalRatingEvents, openEditModal, closeEditModal, submitEditModal } from "./editModal";
import { renderPlayerRating, patchAllItemsRating, updateTrackRatingBar, setRating, undoRating } from "./rating";
import { recentCardsHtml, recentPlayContext } from "./recentlyPlayed";
import {
  initDownloadDB,
  getDownloadByStreamUrl,
  getAllDownloads,
  deleteDownloadById,
  deleteDownloadByStreamUrl,
  isDownloadDbReady,
  addDownloadRecord,
  evictForBudget,
} from "./offlineDb";
import { installClickGuard, wasDrag } from "./clickGuard";
import { installHoverPreview } from "./hoverPreview";
import { showToast } from "./toast";
import { getAllFolders, invalidateFolderCache } from "./folderCache";
import { fisherYates, buildWeightedQueue, buildNormalQueue, rebuildShuffleQueue, nextIndex, prevIndex } from "./shuffle";
import { getOfflineUrl, revokeOfflineUrl } from "./offlineUrl";
import { findResumeLocal, findResumeRecent } from "./resume";
import { openSmartPlaylistEditor } from "./smartEditor";
import { reorderPlaylistItem } from "./playlistReorder";
import { applyHeaderState, enterTrackListView, enterFolderGridView } from "./viewEntry";
import { closeLangPicker, showLangPicker, initFilterBarScrollReveal, initGlobalSearch, hideGlobalSearch, playlistCtxMenuItems } from "./folderBrowseUi";
import { initPlaylistDragDrop, destroyPlaylistDragDrop } from "./playlistDragDrop";
import { initSwipeGestures } from "./swipe";
import { initPlaylistModalEvents } from "./playlistModalEvents";
import { bootstrapApp } from "./bootstrap";
import { initQueueDragDrop, destroyQueueDragDrop } from "./queueDragDrop";
import { syncQueueBottom, initQueueResize, initQueuePeekHandle } from "./queuePanelUi";
import { catalogChanged, refreshToastMessage, catalogRefreshInfo, ratingRefreshInfo, patchRatingsInPlace } from "./catalogRefresh";
import { renderFilterPopoverBody, closeFilterPopover, toggleFilterPopover } from "./filterPopoverUi";
import { wireTrackListDelegation } from "./trackListDelegation";
import { globalSearch, exitGlobalSearch } from "./searchView";
import { saveInlineTableEdit } from "./inlineEdit";
import { jumpToCurrentTrack, updatePlayerBarActions } from "./playerNav";
import { stopRenderObserver, appendTrackBatch, ensureRenderedTo, markActive, startWindowedRender } from "./trackRenderWindow";
import { updateFilterChips, applyFilter } from "./filterApply";
import { showUserPlaylistView, playUserPlaylist, openPlaylistModal, closePlaylistModal } from "./playlistViews";
import { deleteUserPlaylist, renameUserPlaylist, addToPlaylist, createAndAddToPlaylist } from "./playlistActions";
import {
  loadUserPlaylists,
  startPlaylistSync,
  stopPlaylistSync,
  snapshotPlaylists,
  restorePlaylists,
} from "./playlistSync";

// CSS ports: Vite bundles these into one stylesheet, _html.py links it
// AFTER the legacy inline <style> (later wins at equal specificity).
import "./styles/metaPill.css";
import "./styles/root.css";
import "./styles/toolsPanel.css";
import "./styles/modals.css";
import "./styles/playlistCards.css";
import "./styles/playerBar.css";
import "./styles/tableView.css";
import "./styles/trackList.css";
import "./styles/videoOverlay.css";
import {
  saveCatalogCache,
  loadCatalogCache,
  clearCatalogCache,
  saveLastPlayedLocal,
  loadLastPlayedLocal,
  applyLocalMutations,
} from "./catalogCache";

export interface PlayerConfig {
  itemNoun: string;
  fileEmoji: string;
  apiPath: string;
  enableOffline: boolean;
  enableShuffle: boolean;
  enableRepeat: boolean;
  enableSkipIntro: boolean;
  enableRatingWrite: boolean;
  minRating: number;
  debugFilter: boolean;
  enableRecent: boolean;
  enableAutoResume: boolean;
  crossfadeDuration: number;
  enableMetadataEdit: boolean;
  enableLyrics: boolean;
  enablePlaylists: boolean;
  playlistSyncIntervalMs: number;
  languageGroups: Record<string, string[]>;
  defaultLanguage: string;
  audiobookDirs: string[];
  playerBarStyle: "classic" | "waveform";
  bpmMin: number;
  bpmMax: number;
}

function readConfig(): PlayerConfig | null {
  const el = document.getElementById("ht-config");
  if (!el || !el.textContent) return null;
  try {
    return JSON.parse(el.textContent) as PlayerConfig;
  } catch {
    return null;
  }
}

// Read once — currently informational only (no ported module consumes CFG
// yet); kept from the Phase 1 scaffold so the toolchain still exercises the
// #ht-config contract end-to-end.
const cfg = readConfig();
if (cfg) {
  // eslint-disable-next-line no-console
  console.debug("[hometools webui] config loaded", cfg.apiPath);
}

// Initialize legacy player JS (from player_js/*.py modules)
// eval() bulk-port was tried and reverted 2026-08-06 (broke prod, see
// git log). Do not add a legacy.ts import/call here again without first
// reading docs/IMPLEMENTATION_PLAN.md → Vite/TypeScript migration.

/**
 * Format a duration in seconds as `m:ss` or `h:mm:ss`.
 *
 * Ported verbatim from `player_js/_core.py::render_core_js()`'s
 * `function fmtTime(s) { ... }` — see this file's header for the
 * migration/bridge context. Behavior must stay byte-for-byte identical
 * (many toast messages and the progress bar display depend on it).
 */
export function fmtTime(s: number): string {
  if (!isFinite(s)) return "0:00";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(Math.floor(s % 60)).padStart(2, "0");
  return h > 0 ? h + ":" + String(m).padStart(2, "0") + ":" + sec : m + ":" + sec;
}

/**
 * Escape `&`, `<`, `>`, `"` for safe interpolation into `innerHTML`.
 *
 * Ported verbatim from `player_js/_core.py::render_core_js()`'s
 * `function escHtml(s) { ... }`. Used pervasively when building track/
 * folder card markup as HTML strings — do not change escaping behavior
 * without auditing every `escHtml(...)` call site in `player_js/*.py`.
 */
export function escHtml(s: unknown): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Format a byte count as a human-readable size (`"12.3 MB"`).
 *
 * Ported verbatim from `player_js/_core.py::render_core_js()`'s
 * `function formatBytes(bytes) { ... }` (offline-download size display).
 */
export function formatBytes(bytes: number): string {
  const value = Number(bytes || 0);
  if (value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let v = value;
  let idx = 0;
  while (v >= 1024 && idx < units.length - 1) {
    v /= 1024;
    idx++;
  }
  return (idx === 0 ? String(v) : v.toFixed(1)) + " " + units[idx];
}

declare global {
  interface Window {
    fmtTime: typeof fmtTime;
    escHtml: typeof escHtml;
    formatBytes: typeof formatBytes;
    renderBpmPill: typeof renderBpmPill;
    needsConversion: typeof needsConversion;
    filenameFromPath: typeof filenameFromPath;
    parentPath: typeof parentPath;
    leafName: typeof leafName;
    _currentFolderOf: typeof currentFolderOf;
    _fmtDuration: typeof _fmtDuration;
    _fmtFileSize: typeof _fmtFileSize;
    _fmtDate: typeof _fmtDate;
    _normalizeStem: typeof _normalizeStem;
    _dupeKey: typeof _dupeKey;
    _isDupeGroupSafe: typeof _isDupeGroupSafe;
    cleanFolderName: typeof cleanFolderName;
    renderBreadcrumbHtml: typeof renderBreadcrumbHtml;
    _evaluateSmartPlaylist: typeof evaluateSmartPlaylist;
    _smartFieldType: typeof smartFieldType;
    _smartOpsFor: typeof smartOpsFor;
    _smartRenderRuleRow: typeof smartRenderRuleRow;
    _resolvePlaylistItems: typeof resolvePlaylistItems;
    _collectAllPlaylistRelPaths: typeof collectAllPlaylistRelPaths;
    _resolveAllPlaylistItemsFrom: typeof resolveAllPlaylistItems;
    _buildSmartSubmit: typeof buildSmartSubmit;
    _findResumeLocal: typeof findResumeLocal;
    _findResumeRecent: typeof findResumeRecent;
    SMART_FIELDS: typeof SMART_FIELDS;
    SMART_OPS_BY_TYPE: typeof SMART_OPS_BY_TYPE;
    _getRecentMoveTargets: typeof getRecentMoveTargets;
    _saveRecentMoveTarget: typeof saveRecentMoveTarget;
    _saveCatalogCache(items: LegacyMediaItem[]): void;
    _loadCatalogCache(): LegacyMediaItem[] | null;
    _clearCatalogCache(): void;
    _saveLastPlayedLocal(rp: string, pos: number): void;
    _loadLastPlayedLocal(): ReturnType<typeof loadLastPlayedLocal>;
    _applyLocalMutations(items: LegacyMediaItem[]): LegacyMediaItem[];
    formatDate: typeof formatDate;
    sortDownloads: typeof sortDownloads;
    getAppDownloadUsage: typeof getAppDownloadUsage;
    estimateOfflineStorage: typeof estimateOfflineStorage;
    _storageSummaryView(info: OfflineStorageInfo): StorageSummaryView;
    _readyStreamUrls: typeof readyStreamUrls;
    _offlineDownloadListHtml: typeof offlineDownloadListHtml;
    detectLangFromName: typeof detectLangFromName;
    detectSubLangFromName: typeof detectSubLangFromName;
    _langBadgesHtml: typeof langBadgesHtml;
    _compositeFlagHtml: typeof compositeFlagHtml;
    _findItemByStreamUrl: typeof findItemByStreamUrl;
    _progressApiBase: typeof progressApiBase;
    _getProgressPath: typeof getProgressPath;
    _setProgressPath: typeof setProgressPath;
    _cancelProgressTimer: typeof cancelProgressTimer;
    _saveProgressNow: typeof saveProgressNow;
    _saveProgressDebounced: typeof saveProgressDebounced;
    _clearProgressFor: typeof clearProgressFor;
    _loadAndSeekProgress: typeof loadAndSeekProgress;
    _filterPopoverBodyHtml: typeof filterPopoverBodyHtml;
    _folderOrderKey: typeof folderOrderKey;
    _loadOrder: typeof loadOrder;
    _sortByOrder: typeof sortByOrder;
    FAVORITES_ORDER_KEY: string;
    _nextShuffleMode: typeof nextShuffleMode;
    _nextRepeatMode: typeof nextRepeatMode;
    _shuffleBtnView: typeof shuffleBtnView;
    _repeatBtnView: typeof repeatBtnView;
    _playerRatingStars: typeof playerRatingStars;
    _ratingBarWidthPct: typeof ratingBarWidthPct;
    _editModalRatingStars: typeof editModalRatingStars;
    _toggleEditRating: typeof toggleEditRating;
    _favoriteBtnView: typeof favoriteBtnView;
    _buildDuplicateIndex: typeof buildDuplicateIndex;
    _filterCombinedChipView: typeof filterCombinedChipView;
    _filterHiddenChipView: typeof filterHiddenChipView;
    _buildProgressPayload: typeof buildProgressPayload;
    withMissingEpisodes: typeof withMissingEpisodes;
    _itemsUnder(path: string, allItems: LegacyMediaItem[]): LegacyMediaItem[];
    _collectGenres: typeof collectGenres;
    _sortTracks: typeof sortTracks;
    _buildFolderMatches: typeof buildFolderMatches;
    _searchItems: typeof searchItems;
    _applyFilterChain: typeof applyFilterChain;
    _parseIntro: typeof parseIntro;
    _introButtonMode: typeof introButtonMode;
    _patchIntroLocal: typeof patchIntroLocal;
    _queueIndexOf: typeof queueIndexOf;
    _queueAdd: typeof queueAdd;
    _queueRemoveAt: typeof queueRemoveAt;
    _queueClear: typeof queueClear;
    _queueMove: typeof queueMove;
    _resolveNext: typeof resolveNext;
    _replaceItemFields: typeof replaceItemFields;
    _contentsAt: typeof contentsAt;
    _folderCardHtml: typeof folderCardHtml;
    _fileCardHtml: typeof fileCardHtml;
    _trackRowsHtml: typeof trackRowsHtml;
    _searchFolderRowHtml: typeof searchFolderRowHtml;
    _searchResultRowHtml: typeof searchResultRowHtml;
    _inlineRatingHtml: typeof inlineRatingHtml;
    _moveWidgetHtml: typeof moveWidgetHtml;
    _dupePanelBodyHtml: typeof dupePanelBodyHtml;
    _queuePanelHtml: typeof queuePanelHtml;
    _ctxMenuHtml: typeof ctxMenuHtml;
    _playerBarActionsHtml: typeof playerBarActionsHtml;
    _bpmAdjustMenuHtml: typeof bpmAdjustMenuHtml;
    _toolsRowHtml: typeof toolsRowHtml;
    _favoritesCardHtml: typeof favoritesCardHtml;
    _playlistCardHtml: typeof playlistCardHtml;
    _smartEditorModalHtml: typeof smartEditorModalHtml;
    _playlistModalListHtml: typeof playlistModalListHtml;
    _batchEnd: typeof batchEnd;
    _initLyricsPanel: typeof initLyricsPanel;
    _closeCtxMenu: typeof closeCtxMenu;
    _openCtxMenu: typeof openCtxMenu;
    _revealInExplorer: typeof revealInExplorer;
    _openDupePanel: typeof openDupePanel;
    _closeDupePanel: typeof closeDupePanel;
    _collectDupeItems: typeof collectDupeItems;
    _deleteTrackFromList: typeof deleteTrackFromList;
    _deleteDuplicateFile: typeof deleteDuplicateFile;
    _removeGoneTrack: typeof removeGoneTrack;
    _moveFileToFolder: typeof moveFileToFolder;
    _loadFavorites: typeof loadFavorites;
    _loadExtraFolders: typeof loadExtraFolders;
    _addExtraFolder: typeof addExtraFolder;
    _removeExtraFolder: typeof removeExtraFolder;
    _addExtraFolderPlaceholders: typeof addExtraFolderPlaceholders;
    _markExtraFolderCards: typeof markExtraFolderCards;
    _extraFolderAliases: typeof extraFolderAliases;
    _updateFavoriteButtons: typeof updateFavoriteButtons;
    _toggleFavorite: typeof toggleFavorite;
    _renderPlayerRating: typeof renderPlayerRating;
    _patchAllItemsRating: typeof patchAllItemsRating;
    _updateTrackRatingBar: typeof updateTrackRatingBar;
    _setRating: typeof setRating;
    _undoRating: typeof undoRating;
    _isCrossfading: typeof isCrossfading;
    _crossfadeCleanup: typeof crossfadeCleanup;
    _startCrossfade: typeof startCrossfade;
    _finishCrossfade: typeof finishCrossfade;
    _initPip: typeof initPip;
    _isPipActive: typeof isPipActive;
    _exitPip: typeof exitPip;
    _playAllCurrent: typeof playAllCurrent;
    _getBgAudio: typeof getBgAudio;
    _togglePlay: typeof togglePlay;
    _handlePreviousTrack: typeof handlePreviousTrack;
    _showNowPlaying: typeof showNowPlaying;
    _syncShufflePosition: typeof syncShufflePosition;
    _beginPlayback: typeof beginPlayback;
    _activeMedia: typeof activeMedia;
    _updateMediaSession: typeof updateMediaSession;
    _wasPlaying: typeof wasPlaying;
    _setWasPlaying: typeof setWasPlaying;
    _initBackgroundPlayback: typeof initBackgroundPlayback;
    _bgAudioIsActive: typeof bgAudioIsActive;
    _stopBgSync: typeof stopBgSync;
    _startBgMirror: typeof startBgMirror;
    _initEditModalRatingEvents: typeof initEditModalRatingEvents;
    _openEditModal: typeof openEditModal;
    _closeEditModal: typeof closeEditModal;
    _submitEditModal: typeof submitEditModal;
    _indexingToastHtml: typeof indexingToastHtml;
    _trackTableHeaderHtml: string;
    _viewToggleView: typeof viewToggleView;
    _indexOfPath: typeof indexOfPath;
    _withoutPath: typeof withoutPath;
    _isBeforeIndex: typeof isBeforeIndex;
    _ratingToastLabel: typeof ratingToastLabel;
    _renderTargetFor: typeof renderTargetFor;
    _jumpTarget: typeof jumpTarget;
    _recentCardsHtml: typeof recentCardsHtml;
    _recentPlayContext: typeof recentPlayContext;
    initDownloadDB: typeof initDownloadDB;
    getDownloadByStreamUrl: typeof getDownloadByStreamUrl;
    getAllDownloads: typeof getAllDownloads;
    deleteDownloadById: typeof deleteDownloadById;
    deleteDownloadByStreamUrl: typeof deleteDownloadByStreamUrl;
    isDownloadDbReady: typeof isDownloadDbReady;
    addDownloadRecord: typeof addDownloadRecord;
    _evictForBudget: typeof evictForBudget;
    wasDrag: typeof wasDrag;
    _getAllFoldersFrom: typeof getAllFolders;
    _invalidateFolderCache: typeof invalidateFolderCache;
    fisherYates: typeof fisherYates;
    buildWeightedQueue: typeof buildWeightedQueue;
    buildNormalQueue: typeof buildNormalQueue;
    nextIndex: typeof nextIndex;
    prevIndex: typeof prevIndex;
    getOfflineUrl: typeof getOfflineUrl;
    revokeOfflineUrl: typeof revokeOfflineUrl;
    _loadUserPlaylists: typeof loadUserPlaylists;
    _startPlaylistSync: typeof startPlaylistSync;
    _stopPlaylistSync: typeof stopPlaylistSync;
    _snapshotPlaylists: typeof snapshotPlaylists;
    _restorePlaylists: typeof restorePlaylists;
    _openSmartPlaylistEditor: typeof openSmartPlaylistEditor;
    _reorderPlaylistItem: typeof reorderPlaylistItem;
    _initPlaylistDragDrop: typeof initPlaylistDragDrop;
    _destroyPlaylistDragDrop: typeof destroyPlaylistDragDrop;
    _initSwipeGestures: typeof initSwipeGestures;
    _initPlaylistModalEvents: typeof initPlaylistModalEvents;
    _bootstrapApp: typeof bootstrapApp;
    _initQueueDragDrop: typeof initQueueDragDrop;
    _destroyQueueDragDrop: typeof destroyQueueDragDrop;
    _syncQueueBottom: typeof syncQueueBottom;
    _initQueueResize: typeof initQueueResize;
    _initQueuePeekHandle: typeof initQueuePeekHandle;
    _catalogChanged: typeof catalogChanged;
    _refreshToastMessage: typeof refreshToastMessage;
    _catalogRefreshInfo: typeof catalogRefreshInfo;
    _ratingRefreshInfo: typeof ratingRefreshInfo;
    _patchRatingsInPlace: typeof patchRatingsInPlace;
    _renderFilterPopoverBody: typeof renderFilterPopoverBody;
    _closeFilterPopover: typeof closeFilterPopover;
    _toggleFilterPopover: typeof toggleFilterPopover;
    _wireTrackListDelegation: typeof wireTrackListDelegation;
    _globalSearch: typeof globalSearch;
    _exitGlobalSearch: typeof exitGlobalSearch;
    _saveInlineTableEdit: typeof saveInlineTableEdit;
    _jumpToCurrentTrack: typeof jumpToCurrentTrack;
    _updatePlayerBarActions: typeof updatePlayerBarActions;
    _stopRenderObserver: typeof stopRenderObserver;
    _appendTrackBatch: typeof appendTrackBatch;
    _ensureRenderedTo: typeof ensureRenderedTo;
    _markActive: typeof markActive;
    _startWindowedRender: typeof startWindowedRender;
    _updateFilterChips: typeof updateFilterChips;
    _applyFilter: typeof applyFilter;
    _showUserPlaylistView: typeof showUserPlaylistView;
    _playUserPlaylist: typeof playUserPlaylist;
    _openPlaylistModal: typeof openPlaylistModal;
    _closePlaylistModal: typeof closePlaylistModal;
    _closeLangPicker: typeof closeLangPicker;
    _applyHeaderState: typeof applyHeaderState;
    _enterTrackListView: typeof enterTrackListView;
    _enterFolderGridView: typeof enterFolderGridView;
    _showLangPicker: typeof showLangPicker;
    _initFilterBarScrollReveal: typeof initFilterBarScrollReveal;
    _initGlobalSearch: typeof initGlobalSearch;
    _hideGlobalSearch: typeof hideGlobalSearch;
    _playlistCtxMenuItems: typeof playlistCtxMenuItems;
    _deleteUserPlaylist: typeof deleteUserPlaylist;
    _renameUserPlaylist: typeof renameUserPlaylist;
    _addToPlaylist: typeof addToPlaylist;
    _createAndAddToPlaylist: typeof createAndAddToPlaylist;
  }
}

// `apiPath` used to derive the cache keys below — falls back to '' exactly
// like the legacy `var API_PATH = CFG.apiPath || '';` in _player_js.py.
const _apiPathForCache = (cfg && cfg.apiPath) || "";

// Bridge for the legacy Python-generated inline <script> (still one shared
// non-strict function scope, not an ES module) — see header comment.
// Phase 5 opportunistic-migration slice (docs/IMPLEMENTATION_PLAN.md):
// needsConversion/filenameFromPath (pathUtils.ts), the five dupe-detection
// helpers (dupeUtils.ts), and cleanFolderName/renderBreadcrumbHtml
// (breadcrumb.ts) were ported alongside this file's existing three leaf
// helpers — see each module's header comment for why they qualified as
// safe, dependency-free ports. evaluateSmartPlaylist (smartPlaylist.ts) is
// a deliberate, larger slice (not opportunistic) — see that module's
// header comment for why it stayed pure (explicit params instead of
// reading the mutable allItems/_userPlaylists/_savedFavorites globals).
window.fmtTime = fmtTime;
window.escHtml = escHtml;
window.formatBytes = formatBytes;
window.renderBpmPill = renderBpmPill;
window.needsConversion = needsConversion;
window.filenameFromPath = filenameFromPath;
window.parentPath = parentPath;
window.leafName = leafName;
window._currentFolderOf = currentFolderOf;
window._fmtDuration = _fmtDuration;
window._fmtFileSize = _fmtFileSize;
window._fmtDate = _fmtDate;
window._normalizeStem = _normalizeStem;
window._dupeKey = _dupeKey;
window._isDupeGroupSafe = _isDupeGroupSafe;
window.cleanFolderName = cleanFolderName;
window.renderBreadcrumbHtml = renderBreadcrumbHtml;
window._evaluateSmartPlaylist = evaluateSmartPlaylist;
// _smartFieldType/_smartOpsFor + their backing constants: read-only after
// init, so the plain-assignment bridge (like originalTitle) is safe — still
// called by _smartRenderRuleRow in player_js/_playlists.py (not ported).
window._smartFieldType = smartFieldType;
window._smartOpsFor = smartOpsFor;
window._smartRenderRuleRow = smartRenderRuleRow;
window._resolvePlaylistItems = resolvePlaylistItems;
window._collectAllPlaylistRelPaths = collectAllPlaylistRelPaths;
window._resolveAllPlaylistItemsFrom = resolveAllPlaylistItems;
window._buildSmartSubmit = buildSmartSubmit;
window._findResumeLocal = findResumeLocal;
window._findResumeRecent = findResumeRecent;
window.SMART_FIELDS = SMART_FIELDS;
window.SMART_OPS_BY_TYPE = SMART_OPS_BY_TYPE;
window._getRecentMoveTargets = getRecentMoveTargets;
window._saveRecentMoveTarget = saveRecentMoveTarget;
// Bridged with apiPath baked in via closure — see _apiPathForCache above and
// catalogCache.ts's header comment on why the module itself stays pure
// (explicit apiPath parameter instead of a window/global read).
window._saveCatalogCache = function (items) {
  saveCatalogCache(items, _apiPathForCache);
};
window._loadCatalogCache = function () {
  return loadCatalogCache(_apiPathForCache);
};
window._clearCatalogCache = function () {
  clearCatalogCache(_apiPathForCache);
};
window._saveLastPlayedLocal = function (rp, pos) {
  saveLastPlayedLocal(rp, pos, _apiPathForCache);
};
window._loadLastPlayedLocal = function () {
  return loadLastPlayedLocal(_apiPathForCache);
};
window._applyLocalMutations = function (items) {
  return applyLocalMutations(items, window._locallyDeletedPaths);
};
window.formatDate = formatDate;
window.sortDownloads = sortDownloads;
window.getAppDownloadUsage = getAppDownloadUsage;
window.estimateOfflineStorage = estimateOfflineStorage;
window._storageSummaryView = function (info) { return storageSummaryView(info, formatBytes); };
window._readyStreamUrls = readyStreamUrls;
window._offlineDownloadListHtml = offlineDownloadListHtml;
window.detectLangFromName = detectLangFromName;
window.detectSubLangFromName = detectSubLangFromName;
window._langBadgesHtml = langBadgesHtml;
window._compositeFlagHtml = compositeFlagHtml;
window._findItemByStreamUrl = findItemByStreamUrl;
window._progressApiBase = progressApiBase;
window._getProgressPath = getProgressPath;
window._setProgressPath = setProgressPath;
window._cancelProgressTimer = cancelProgressTimer;
window._saveProgressNow = saveProgressNow;
window._saveProgressDebounced = saveProgressDebounced;
window._clearProgressFor = clearProgressFor;
window._loadAndSeekProgress = loadAndSeekProgress;
window._filterPopoverBodyHtml = filterPopoverBodyHtml;
window._folderOrderKey = folderOrderKey;
window._loadOrder = loadOrder;
window._sortByOrder = sortByOrder;
window.FAVORITES_ORDER_KEY = FAVORITES_ORDER_KEY;
window._nextShuffleMode = nextShuffleMode;
window._nextRepeatMode = nextRepeatMode;
window._shuffleBtnView = shuffleBtnView;
window._repeatBtnView = repeatBtnView;
window._playerRatingStars = playerRatingStars;
window._ratingBarWidthPct = ratingBarWidthPct;
window._editModalRatingStars = editModalRatingStars;
window._toggleEditRating = toggleEditRating;
window._favoriteBtnView = favoriteBtnView;
window._buildDuplicateIndex = buildDuplicateIndex;
window._filterCombinedChipView = filterCombinedChipView;
window._filterHiddenChipView = filterHiddenChipView;
window._buildProgressPayload = buildProgressPayload;
window.withMissingEpisodes = withMissingEpisodes;
window._itemsUnder = itemsUnder;
window._collectGenres = collectGenres;
window._sortTracks = sortTracks;
window._buildFolderMatches = buildFolderMatches;
window._searchItems = searchItems;
window._applyFilterChain = applyFilterChain;
window._parseIntro = parseIntro;
window._introButtonMode = introButtonMode;
window._patchIntroLocal = patchIntroLocal;
// Queue data ops — htState.userQueue bridge (see queue.ts header).
window._queueIndexOf = queueIndexOf;
window._queueAdd = queueAdd;
window._queueRemoveAt = queueRemoveAt;
window._queueClear = queueClear;
window._queueMove = queueMove;
window._resolveNext = resolveNext;
window._replaceItemFields = replaceItemFields;
window._contentsAt = contentsAt;
window._folderCardHtml = folderCardHtml;
window._fileCardHtml = fileCardHtml;
window._trackRowsHtml = trackRowsHtml;
window._searchFolderRowHtml = searchFolderRowHtml;
window._searchResultRowHtml = searchResultRowHtml;
window._inlineRatingHtml = inlineRatingHtml;
window._moveWidgetHtml = moveWidgetHtml;
window._dupePanelBodyHtml = dupePanelBodyHtml;
window._queuePanelHtml = queuePanelHtml;
window._ctxMenuHtml = ctxMenuHtml;
window._playerBarActionsHtml = playerBarActionsHtml;
window._bpmAdjustMenuHtml = bpmAdjustMenuHtml;
window._toolsRowHtml = toolsRowHtml;
window._favoritesCardHtml = favoritesCardHtml;
window._playlistCardHtml = playlistCardHtml;
window._smartEditorModalHtml = smartEditorModalHtml;
window._playlistModalListHtml = playlistModalListHtml;
window._batchEnd = batchEnd;
window._initLyricsPanel = initLyricsPanel;
window._closeCtxMenu = closeCtxMenu;
window._openCtxMenu = openCtxMenu;
window._revealInExplorer = revealInExplorer;
window._openDupePanel = openDupePanel;
window._closeDupePanel = closeDupePanel;
window._collectDupeItems = collectDupeItems;
window._deleteTrackFromList = deleteTrackFromList;
window._deleteDuplicateFile = deleteDuplicateFile;
window._removeGoneTrack = removeGoneTrack;
window._moveFileToFolder = moveFileToFolder;
window._loadFavorites = loadFavorites;
window._loadExtraFolders = loadExtraFolders;
window._addExtraFolder = addExtraFolder;
window._removeExtraFolder = removeExtraFolder;
window._addExtraFolderPlaceholders = addExtraFolderPlaceholders;
window._markExtraFolderCards = markExtraFolderCards;
window._extraFolderAliases = extraFolderAliases;
window._updateFavoriteButtons = updateFavoriteButtons;
window._toggleFavorite = toggleFavorite;
window._renderPlayerRating = renderPlayerRating;
window._patchAllItemsRating = patchAllItemsRating;
window._updateTrackRatingBar = updateTrackRatingBar;
window._setRating = setRating;
window._undoRating = undoRating;
window._isCrossfading = isCrossfading;
window._crossfadeCleanup = crossfadeCleanup;
window._startCrossfade = startCrossfade;
window._finishCrossfade = finishCrossfade;
window._initPip = initPip;
window._isPipActive = isPipActive;
window._exitPip = exitPip;
window._playAllCurrent = playAllCurrent;
window._getBgAudio = getBgAudio;
window._togglePlay = togglePlay;
window._handlePreviousTrack = handlePreviousTrack;
window._showNowPlaying = showNowPlaying;
window._syncShufflePosition = syncShufflePosition;
window._beginPlayback = beginPlayback;
window._activeMedia = activeMedia;
window._updateMediaSession = updateMediaSession;
window._wasPlaying = wasPlaying;
window._setWasPlaying = setWasPlaying;
window._initBackgroundPlayback = initBackgroundPlayback;
window._bgAudioIsActive = bgAudioIsActive;
window._stopBgSync = stopBgSync;
window._startBgMirror = startBgMirror;
window._initEditModalRatingEvents = initEditModalRatingEvents;
window._openEditModal = openEditModal;
window._closeEditModal = closeEditModal;
window._submitEditModal = submitEditModal;
window._indexingToastHtml = indexingToastHtml;
window._trackTableHeaderHtml = TRACK_TABLE_HEADER_HTML;
window._viewToggleView = viewToggleView;
window._indexOfPath = indexOfPath;
window._withoutPath = withoutPath;
window._isBeforeIndex = isBeforeIndex;
window._ratingToastLabel = ratingToastLabel;
window._renderTargetFor = renderTargetFor;
window._jumpTarget = jumpTarget;
window._recentCardsHtml = recentCardsHtml;
window._recentPlayContext = recentPlayContext;
// IndexedDB layer — same names as legacy (bare call sites unchanged).
window.initDownloadDB = initDownloadDB;
window.getDownloadByStreamUrl = getDownloadByStreamUrl;
window.getAllDownloads = getAllDownloads;
window.deleteDownloadById = deleteDownloadById;
window.deleteDownloadByStreamUrl = deleteDownloadByStreamUrl;
window.isDownloadDbReady = isDownloadDbReady;
window.addDownloadRecord = addDownloadRecord;
window._evictForBudget = evictForBudget;
window.wasDrag = wasDrag;
// showToast already typed in legacy-globals.d.ts — no re-declare here.
window.showToast = showToast;
window._getAllFoldersFrom = getAllFolders;
window._invalidateFolderCache = invalidateFolderCache;
// Shuffle engine — first htState-bridge consumer (see shuffle.ts header).
// rebuildShuffleQueue already typed in legacy-globals.d.ts.
window.fisherYates = fisherYates;
window.buildWeightedQueue = buildWeightedQueue;
window.buildNormalQueue = buildNormalQueue;
window.rebuildShuffleQueue = rebuildShuffleQueue;
window.nextIndex = nextIndex;
window.prevIndex = prevIndex;
window.getOfflineUrl = getOfflineUrl;
// revokeOfflineUrl: still called bare from playItem() (_library_tools.py,
// not yet ported) — must be bridged, see offlineUrl.ts header comment.
window.revokeOfflineUrl = revokeOfflineUrl;
// Playlist load/sync — state via htState.userPlaylists/playlistRevision,
// timer private to playlistSync.ts (see its header).
window._loadUserPlaylists = loadUserPlaylists;
window._startPlaylistSync = startPlaylistSync;
window._stopPlaylistSync = stopPlaylistSync;
window._snapshotPlaylists = snapshotPlaylists;
window._restorePlaylists = restorePlaylists;
window._openSmartPlaylistEditor = openSmartPlaylistEditor;
window._reorderPlaylistItem = reorderPlaylistItem;
window._initPlaylistDragDrop = initPlaylistDragDrop;
window._destroyPlaylistDragDrop = destroyPlaylistDragDrop;
window._initSwipeGestures = initSwipeGestures;
window._initPlaylistModalEvents = initPlaylistModalEvents;
window._bootstrapApp = bootstrapApp;
window._initQueueDragDrop = initQueueDragDrop;
window._destroyQueueDragDrop = destroyQueueDragDrop;
window._syncQueueBottom = syncQueueBottom;
window._initQueueResize = initQueueResize;
window._initQueuePeekHandle = initQueuePeekHandle;
window._catalogChanged = catalogChanged;
window._refreshToastMessage = refreshToastMessage;
window._catalogRefreshInfo = catalogRefreshInfo;
window._ratingRefreshInfo = ratingRefreshInfo;
window._patchRatingsInPlace = patchRatingsInPlace;
window._renderFilterPopoverBody = renderFilterPopoverBody;
window._closeFilterPopover = closeFilterPopover;
window._toggleFilterPopover = toggleFilterPopover;
window._wireTrackListDelegation = wireTrackListDelegation;
window._globalSearch = globalSearch;
window._exitGlobalSearch = exitGlobalSearch;
window._saveInlineTableEdit = saveInlineTableEdit;
window._jumpToCurrentTrack = jumpToCurrentTrack;
window._updatePlayerBarActions = updatePlayerBarActions;
window._stopRenderObserver = stopRenderObserver;
window._appendTrackBatch = appendTrackBatch;
window._ensureRenderedTo = ensureRenderedTo;
window._markActive = markActive;
window._startWindowedRender = startWindowedRender;
window._updateFilterChips = updateFilterChips;
window._applyFilter = applyFilter;
window._showUserPlaylistView = showUserPlaylistView;
window._playUserPlaylist = playUserPlaylist;
window._openPlaylistModal = openPlaylistModal;
window._closePlaylistModal = closePlaylistModal;
window._closeLangPicker = closeLangPicker;
window._applyHeaderState = applyHeaderState;
window._enterTrackListView = enterTrackListView;
window._enterFolderGridView = enterFolderGridView;
window._showLangPicker = showLangPicker;
window._initFilterBarScrollReveal = initFilterBarScrollReveal;
window._initGlobalSearch = initGlobalSearch;
window._hideGlobalSearch = hideGlobalSearch;
window._playlistCtxMenuItems = playlistCtxMenuItems;
window._deleteUserPlaylist = deleteUserPlaylist;
window._renameUserPlaylist = renameUserPlaylist;
window._addToPlaylist = addToPlaylist;
window._createAndAddToPlaylist = createAndAddToPlaylist;


// Click-guard owns its own pointer state now (was _mdX/_mdY in _core.py) —
// listeners must be live before the legacy script wires any click handler.
installClickGuard();

// Video thumbnail hover preview (sprite-sheet frames); no-op for audio/touch.
installHoverPreview({ enabled: !!document.getElementById("player") && document.getElementById("player")!.tagName === "VIDEO" });
