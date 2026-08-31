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
 * Latest slice: clickGuard.ts (wasDrag + its private pointer state and
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
import { formatDate, sortDownloads, getAppDownloadUsage, estimateOfflineStorage } from "./offlineDownloads";
import { detectLangFromName, detectSubLangFromName } from "./langDetect";
import { withMissingEpisodes } from "./episodeGaps";
import {
  evaluateSmartPlaylist,
  smartFieldType,
  smartOpsFor,
  smartRenderRuleRow,
  SMART_FIELDS,
  SMART_OPS_BY_TYPE,
} from "./smartPlaylist";
import { getRecentMoveTargets, saveRecentMoveTarget } from "./recentMoveTargets";
import { itemsUnder, collectGenres } from "./catalogQuery";
import { installClickGuard, wasDrag } from "./clickGuard";
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
    detectLangFromName: typeof detectLangFromName;
    detectSubLangFromName: typeof detectSubLangFromName;
    withMissingEpisodes: typeof withMissingEpisodes;
    _itemsUnder(path: string, allItems: LegacyMediaItem[]): LegacyMediaItem[];
    _collectGenres: typeof collectGenres;
    wasDrag: typeof wasDrag;
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
window.detectLangFromName = detectLangFromName;
window.detectSubLangFromName = detectSubLangFromName;
window.withMissingEpisodes = withMissingEpisodes;
window._itemsUnder = itemsUnder;
window._collectGenres = collectGenres;
window.wasDrag = wasDrag;

// Click-guard owns its own pointer state now (was _mdX/_mdY in _core.py) —
// listeners must be live before the legacy script wires any click handler.
installClickGuard();

