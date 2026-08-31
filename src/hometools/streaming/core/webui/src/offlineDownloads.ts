/** Offline-download helpers. Ported from player_js/_track_render.py.
 * Pure — no window reads, no DOM. Bridged onto window by main.ts under
 * same names; call sites in _track_render.py unchanged. */

export interface OfflineDownload {
  status?: string;
  timestamp?: number;
  title?: string;
  size?: number;
  [key: string]: unknown;
}

/** Format a download timestamp for display. 'Unbekannt' on bad input. */
export function formatDate(ts: number | string | undefined): string {
  if (!ts) return "Unbekannt";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return "Unbekannt";
  }
}

/** Sort downloads by newest/oldest/title/size. Default: newest first. */
export function sortDownloads(downloads: OfflineDownload[], sortBy: string): OfflineDownload[] {
  return downloads.slice().sort((a, b) => {
    if (sortBy === "oldest") return (a.timestamp || 0) - (b.timestamp || 0);
    if (sortBy === "title") return String(a.title || "").localeCompare(String(b.title || ""));
    if (sortBy === "size") return (b.size || 0) - (a.size || 0);
    return (b.timestamp || 0) - (a.timestamp || 0);
  });
}

/** Sum bytes of all "ready" (fully downloaded) items. */
export function getAppDownloadUsage(downloads: OfflineDownload[]): number {
  return (downloads || []).reduce((sum, d) => sum + (d.status === "ready" ? Number(d.size || 0) : 0), 0);
}

export interface OfflineStorageInfo {
  downloads: OfflineDownload[];
  appUsage: number;
  softLimit: number;
  browserUsage: number | null;
  browserQuota: number | null;
  persistent: boolean | null;
}

/** Estimate app + browser storage usage. softLimit passed in (was
 * OFFLINE_SOFT_LIMIT constant in _track_render.py). */
export function estimateOfflineStorage(downloads: OfflineDownload[], softLimit: number): Promise<OfflineStorageInfo> {
  const list = downloads || [];
  const info: OfflineStorageInfo = {
    downloads: list,
    appUsage: getAppDownloadUsage(list),
    softLimit,
    browserUsage: null,
    browserQuota: null,
    persistent: null,
  };
  const tasks: Promise<unknown>[] = [];
  const storage = navigator.storage;
  if (storage && storage.estimate) {
    tasks.push(
      storage
        .estimate()
        .then((estimate) => {
          info.browserUsage = estimate && estimate.usage ? estimate.usage : 0;
          info.browserQuota = estimate && estimate.quota ? estimate.quota : 0;
        })
        .catch(() => {})
    );
  }
  if (storage && storage.persisted) {
    tasks.push(
      storage
        .persisted()
        .then((persistent) => {
          info.persistent = !!persistent;
        })
        .catch(() => {})
    );
  }
  return Promise.all(tasks).then(() => info);
}


