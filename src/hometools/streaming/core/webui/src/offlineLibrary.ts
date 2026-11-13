/**
 * Offline library controller (downloaded items as a virtual playlist):
 * refresh/open, storage budget + prune, persistent storage, play stored
 * download, SW message listener, pill/close/sort/persist/prune wiring.
 * Ported from `player_js/_track_render.py`. Shared state via htState.
 */

import { getState } from "./stateBridge";
import { getAllDownloads, evictForBudget, type DownloadRecord } from "./offlineDb";
import { sortDownloads, estimateOfflineStorage, getAppDownloadUsage, type OfflineDownload } from "./offlineDownloads";
import { updateOfflineFolderCount } from "./offlineCount";
import { closeOfflineLibrary, OFFLINE_PATH } from "./backNav";

export interface OfflineLibraryCfg {
  itemNoun: string;
  softLimit: number;
  formatBytes(n: number): string;
  currentStreamUrl(): string;
  updateDownloadButtons(): void;
  applyFilter(): void;
  showFolderView(): void;
  enterTrackListView(o: Record<string, unknown>): void;
  destroyPlaylistDragDrop(): void;
}

export interface OfflineLibrary {
  refresh(): Promise<DownloadRecord[]>;
  open(): void;
  ensureStorageBudget(requiredBytes: number, protectedStreamUrl?: string | null): Promise<boolean>;
}

/** Download record -> playlist item. */
export function downloadToItem(d: OfflineDownload, itemNoun: string): LegacyMediaItem {
  return {
    title: d.title || "Offline-Download",
    artist: d.artist || "",
    relative_path: d.relativePath || d.title || d.streamUrl || "",
    stream_url: d.streamUrl || "",
    thumbnail_url: d.thumbnailUrl || "",
    media_type: (d.mediaType as string | undefined) || itemNoun,
    rating: 0,
  } as LegacyMediaItem;
}

/** Ready downloads sorted per the offline sort select. */
export function readyItems(downloads: OfflineDownload[], sortBy: string, itemNoun: string): { ready: OfflineDownload[]; items: LegacyMediaItem[] } {
  const ready = downloads.filter((d) => d.status === "ready");
  return { ready, items: sortDownloads(ready, sortBy).map((d) => downloadToItem(d, itemNoun)) };
}

/** "N download(s) · size" label. */
export function usageLabel(count: number, bytes: number, formatBytes: (n: number) => string): string {
  return count + " download" + (count !== 1 ? "s" : "") + " \u00b7 " + formatBytes(bytes);
}

function el(id: string): HTMLElement | null {
  return document.getElementById(id);
}

export function initOfflineLibrary(cfg: OfflineLibraryCfg): OfflineLibrary {
  const pill = (): HTMLElement | null => el("downloaded-pill");
  const sortValue = (): string => (el("offline-sort") as HTMLSelectElement | null)?.value || "newest";

  function showUsage(ready: OfflineDownload[]): void {
    estimateOfflineStorage(ready, cfg.softLimit).then((info) => {
      if (info && info.appUsage > 0) {
        const tc = el("track-count");
        if (tc) tc.textContent = usageLabel(ready.length, info.appUsage, cfg.formatBytes);
      }
    });
  }

  function refresh(): Promise<DownloadRecord[]> {
    return getAllDownloads().then((downloads) => {
      const s = getState();
      if (s && s.currentPath === OFFLINE_PATH) {
        const { ready, items } = readyItems(downloads, sortValue(), cfg.itemNoun);
        s.playlistItems = items;
        cfg.applyFilter();
        showUsage(ready);
      }
      updateOfflineFolderCount(pill());
      return downloads;
    });
  }

  function open(): void {
    getAllDownloads().then((downloads) => {
      const s = getState();
      if (!s) return;
      const { ready, items } = readyItems(downloads, sortValue(), cfg.itemNoun);
      s.currentPath = OFFLINE_PATH;
      /* Enter via the shared track-list entry point (no showPlaylist + title patch,
         no folder-order fetch for a virtual list). */
      cfg.destroyPlaylistDragDrop();
      s.inPlaylist = true;
      s.currentPlaylistId = OFFLINE_PATH;
      s.playlistItems = items;
      cfg.enterTrackListView({ title: "Downloaded", backDisabled: false, resetIndex: true });
      showUsage(ready);
    });
  }

  function prune(requiredBytes: number, protectedStreamUrl?: string | null): Promise<boolean> {
    return evictForBudget(requiredBytes, cfg.softLimit, protectedStreamUrl).then((ok) => {
      cfg.updateDownloadButtons();
      refresh();
      return ok;
    });
  }

  function ensureStorageBudget(requiredBytes: number, protectedStreamUrl?: string | null): Promise<boolean> {
    return getAllDownloads().then((downloads) => {
      const total = getAppDownloadUsage(downloads);
      if (total + requiredBytes <= cfg.softLimit) return true;
      return prune(requiredBytes, protectedStreamUrl);
    });
  }

  function requestPersistentStorage(): Promise<boolean> {
    const btn = el("offline-persist-btn");
    if (!(navigator.storage && navigator.storage.persist)) return Promise.resolve(false);
    if (btn) btn.textContent = "Pr\u00fcfe persistenten Speicher\u2026";
    return navigator.storage
      .persist()
      .then((persistent) => {
        if (btn) btn.textContent = persistent ? "Persistenter Speicher aktiv" : "Persistenz nicht verf\u00fcgbar";
        return refresh().then(() => persistent);
      })
      .catch(() => {
        if (btn) btn.textContent = "Persistenz fehlgeschlagen";
        return false;
      });
  }

  /* SW download notifications */
  if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener("message", (e: MessageEvent) => {
      if (e.data && (e.data.type === "DOWNLOAD_CACHED" || e.data.type === "DOWNLOAD_DELETED")) {
        cfg.updateDownloadButtons();
        refresh();
      }
    });
  }

  const close = (): void => closeOfflineLibrary({ showFolderView: cfg.showFolderView });
  pill()?.addEventListener("click", open);
  el("offline-close")?.addEventListener("click", close);
  const lib = el("offline-library");
  lib?.addEventListener("click", (e) => {
    if (e.target === lib) close();
  });
  el("offline-sort")?.addEventListener("change", () => void refresh());
  const persistBtn = el("offline-persist-btn");
  if (persistBtn) {
    if (!(navigator.storage && navigator.storage.persist)) persistBtn.hidden = true;
    else persistBtn.addEventListener("click", () => void requestPersistentStorage());
  }
  el("offline-prune-btn")?.addEventListener("click", () => void prune(0, cfg.currentStreamUrl()));
  window.addEventListener("online", () => void refresh());
  window.addEventListener("offline", () => void refresh());

  return { refresh, open, ensureStorageBudget };
}

