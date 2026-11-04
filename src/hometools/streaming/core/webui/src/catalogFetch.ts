/**
 * Catalog refresh orchestration: background index polling, silent refresh on
 * navigation, manual refresh. Ported from `player_js/_queue.py`
 * (scheduleBackgroundRefresh/forceBackgroundRefresh/_triggerSilentRefresh/
 * _refreshPoll/refreshCatalog). Timer + in-flight flag private; items/path via
 * htState; cache + view side effects via hooks.
 *
 * Contract (streaming.instructions.md): every successful fetch calls
 * `saveCache`; refreshCatalog calls `clearCache` + `clearLocalDeleted` first.
 */

import { getState } from "./stateBridge";
import { catalogChanged, catalogRefreshInfo, refreshToastMessage } from "./catalogRefresh";

export interface CatalogFetchHooks {
  apiPath: string;
  showIndexingToast(detail: string, cache: unknown): void;
  hideIndexingToast(): void;
  applyLocalMutations(items: LegacyMediaItem[]): LegacyMediaItem[];
  /** Invalidate dupe map + folder cache. */
  invalidateCaches(): void;
  saveCache(items: LegacyMediaItem[]): void;
  clearCache(): void;
  clearLocalDeleted(): void;
  resetRatingRefresh(): void;
  showFolderView(): void;
  itemsUnder(path: string): LegacyMediaItem[];
  applyFilter(): void;
  toast(msg: string): void;
}

let _indexRefreshTimer: ReturnType<typeof setTimeout> | null = null;
let _silentRefreshInFlight = false;

/** Cancel a pending index poll (used when the indexing toast is hidden). */
export function clearIndexRefreshTimer(): void {
  if (_indexRefreshTimer) {
    clearTimeout(_indexRefreshTimer);
    _indexRefreshTimer = null;
  }
}

function fetchJson(url: string, init?: RequestInit): Promise<any> {
  return fetch(url, init).then((r) => (r.ok ? r.json() : null));
}

function itemsOf(data: any): LegacyMediaItem[] {
  return data && Array.isArray(data.items) ? data.items : [];
}

function refreshBtn(): HTMLElement | null {
  return document.getElementById("refresh-catalog-card");
}

export function scheduleBackgroundRefresh(h: CatalogFetchHooks, delay?: number): void {
  if (_indexRefreshTimer) return;
  _indexRefreshTimer = setTimeout(
    () => {
      _indexRefreshTimer = null;
      const s = getState();
      if (!s) return;
      fetchJson(h.apiPath, { cache: "no-store" })
        .then((data) => {
          if (!data || data.error) return;
          if (data.refreshing) {
            h.showIndexingToast(data.detail || "Building index\u2026", data.cache);
            scheduleBackgroundRefresh(h);
            const newItems = itemsOf(data);
            if (newItems.length > s.allItems.length) {
              s.allItems = newItems;
              h.invalidateCaches();
              h.showFolderView();
            }
            return;
          }
          h.hideIndexingToast();
          s.allItems = h.applyLocalMutations(itemsOf(data));
          h.invalidateCaches();
          h.saveCache(s.allItems);
          console.info("Background refresh complete:", s.allItems.length, "items");
          h.showFolderView();
        })
        .catch(() => scheduleBackgroundRefresh(h));
    },
    delay !== undefined ? delay : 800
  );
}

/** Cancel pending poll and re-fetch now; only if a build is in progress. */
export function forceBackgroundRefresh(h: CatalogFetchHooks): void {
  if (!_indexRefreshTimer) return;
  clearIndexRefreshTimer();
  scheduleBackgroundRefresh(h, 0);
}

/** Silent fetch on every folder/playlist navigation; re-render only on change. */
export function triggerSilentRefresh(h: CatalogFetchHooks): void {
  const s = getState();
  if (!s || _silentRefreshInFlight) return;
  _silentRefreshInFlight = true;
  fetchJson(h.apiPath, { cache: "no-store" })
    .then((data) => {
      _silentRefreshInFlight = false;
      if (!data || data.error || data.loading) return;
      const fresh = h.applyLocalMutations(itemsOf(data));
      const changed = catalogChanged(s.allItems, fresh);
      s.allItems = fresh;
      h.invalidateCaches();
      h.saveCache(s.allItems);
      if (changed) {
        if (s.inPlaylist) {
          const newItems = h.itemsUnder(s.currentPath);
          if (newItems.length) {
            s.playlistItems = newItems;
            h.applyFilter();
          } else {
            h.showFolderView();
          }
        } else {
          h.showFolderView();
        }
      }
      if (data.refreshing) scheduleBackgroundRefresh(h);
    })
    .catch(() => {
      _silentRefreshInFlight = false;
    });
}

export function refreshPoll(h: CatalogFetchHooks): void {
  const s = getState();
  if (!s) return;
  fetchJson(h.apiPath, { cache: "no-store" })
    .then((data) => {
      const rb = refreshBtn();
      if (!data) {
        rb?.classList.remove("spinning");
        h.toast("Refresh fehlgeschlagen");
        return;
      }
      if (data.refreshing) {
        setTimeout(() => refreshPoll(h), 800);
        return;
      }
      const oldCount = s.allItems.length;
      s.allItems = itemsOf(data);
      h.invalidateCaches();
      h.saveCache(s.allItems);
      rb?.classList.remove("spinning");
      const infoEl = document.getElementById("refresh-info");
      if (infoEl) {
        const dt = new Date();
        infoEl.textContent = catalogRefreshInfo(s.allItems.length, dt);
        infoEl.title = "Letzter Katalog-Refresh: " + dt.toLocaleString();
      }
      if (s.inPlaylist) {
        const newItems = h.itemsUnder(s.currentPath);
        if (newItems.length) s.playlistItems = newItems;
        h.applyFilter();
      } else {
        h.showFolderView();
      }
      h.toast(refreshToastMessage(s.allItems.length, oldCount));
    })
    .catch(() => {
      setTimeout(() => refreshPoll(h), 2000);
    });
}

/** User-triggered: clear caches, rebuild server index, poll until done. */
export function refreshCatalog(h: CatalogFetchHooks): void {
  refreshBtn()?.classList.add("spinning");
  h.clearCache();
  h.clearLocalDeleted();
  h.resetRatingRefresh();
  const base = h.apiPath.substring(0, h.apiPath.lastIndexOf("/"));
  fetchJson(base + "/refresh", { method: "POST" })
    .then(() => refreshPoll(h))
    .catch(() => {
      refreshBtn()?.classList.remove("spinning");
      h.toast("Refresh fehlgeschlagen");
    });
}


export interface InitialCatalogHooks extends CatalogFetchHooks {
  loadCache(): LegacyMediaItem[] | null;
  showLoadingState(msg: string): void;
  showCatalogLoadError(msg: string): void;
  /** False when the tools panel turned auto-refresh off. */
  autoRefreshOn(): boolean;
}
let _retryTimer: ReturnType<typeof setTimeout> | null = null;
let _retryCount = 0;
function scheduleInitialRetry(h: InitialCatalogHooks, reason: string): void {
  if (_retryTimer) return;
  console.info("Initial catalog retry scheduled:", reason || "loading");
  _retryTimer = setTimeout(() => {
    _retryTimer = null;
    void loadInitialCatalog(h);
  }, 800);
}
/**
 * Stale-while-revalidate startup load: serve a fresh localStorage snapshot
 * instantly (silent verify fetch follows), else fetch with loading state.
 */
export function loadInitialCatalog(h: InitialCatalogHooks): Promise<LegacyMediaItem[]> {
  const s = getState();
  if (!s) return Promise.resolve([]);
  if (s.allItems.length) {
    console.info("Initial catalog already present in page payload:", s.allItems.length, "items");
    return Promise.resolve(s.allItems);
  }
  const cached = h.loadCache();
  if (cached && cached.length) {
    console.info("Initial catalog: serving", cached.length, "items from localStorage cache (background refresh follows)");
    s.allItems = cached;
    h.invalidateCaches();
    h.showFolderView();
    fetchJson(h.apiPath, { cache: "no-store" })
      .then((data) => {
        if (!data || data.error || data.loading) return;
        const fresh = h.applyLocalMutations(itemsOf(data));
        const changed = catalogChanged(s.allItems, fresh);
        s.allItems = fresh;
        h.invalidateCaches();
        h.saveCache(s.allItems);
        if (changed) h.showFolderView();
        if (data.refreshing) scheduleBackgroundRefresh(h);
      })
      .catch(() => {
        /* server offline - cached data stays visible */
      });
    return Promise.resolve(s.allItems);
  }
  _retryCount += 1;
  if (_retryCount <= 1) h.showLoadingState("Loading library\u2026");
  const t0 = Date.now();
  console.info("Initial catalog fetch started:", h.apiPath);
  return fetch(h.apiPath, { cache: "no-store" })
    .then((r) => {
      console.info("Initial catalog response received after", Date.now() - t0, "ms with status", r.status);
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then((data) => {
      if (data && data.error) throw new Error(data.error);
      if (data && data.loading && (!data.items || data.items.length === 0)) {
        const detail = data.detail || "Library cache is warming in the background.";
        console.info("Initial catalog still building (empty):", detail);
        h.showIndexingToast(detail, data.cache);
        scheduleInitialRetry(h, detail);
        return [] as LegacyMediaItem[];
      }
      if (_retryTimer) {
        clearTimeout(_retryTimer);
        _retryTimer = null;
      }
      _retryCount = 0;
      s.allItems = itemsOf(data);
      h.invalidateCaches();
      h.saveCache(s.allItems);
      console.info("Initial catalog parsed after", Date.now() - t0, "ms:", s.allItems.length, "items");
      h.showFolderView();
      if (data && data.refreshing) {
        const rd = data.detail || "Building index in background\u2026";
        console.info("Catalog served from quick scan, index still building:", rd);
        h.showIndexingToast(rd, data.cache);
        if (h.autoRefreshOn()) scheduleBackgroundRefresh(h);
      } else {
        h.hideIndexingToast();
      }
      return s.allItems;
    })
    .catch((err) => {
      console.error("Initial catalog load failed:", err);
      h.showCatalogLoadError(err && err.message ? err.message : "Library could not be loaded.");
      return [] as LegacyMediaItem[];
    });
}
/** Test helper: reset retry state. */
export function resetInitialCatalogState(): void {
  if (_retryTimer) clearTimeout(_retryTimer);
  _retryTimer = null;
  _retryCount = 0;
}
