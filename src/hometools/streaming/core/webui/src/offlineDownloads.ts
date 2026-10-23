/** Offline-download helpers. Ported from player_js/_track_render.py.
 * Pure — no window reads, no DOM. Bridged onto window by main.ts under
 * same names; call sites in _track_render.py unchanged. */

export interface OfflineDownload {
  status?: string;
  timestamp?: number;
  title?: string;
  size?: number;
  streamUrl?: string;
  thumbnailUrl?: string;
  artist?: string;
  relativePath?: string;
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

/**
 * Oldest-first eviction plan to fit `requiredBytes` under `softLimit`.
 * Only "ready" items, never `protectedStreamUrl` (the one being downloaded/
 * played). Returns [] if already fits, null if impossible even after
 * evicting all candidates (caller must then delete nothing).
 *
 * Ported from `_track_render.py::pruneOldDownloads` (selection half).
 */
export function pickEvictionVictims<T extends OfflineDownload>(
  downloads: T[],
  requiredBytes: number,
  softLimit: number,
  protectedStreamUrl?: string | null
): T[] | null {
  let total = getAppDownloadUsage(downloads);
  const candidates = (downloads || [])
    .filter((d) => d.status === "ready" && d.streamUrl !== protectedStreamUrl)
    .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  const victims: T[] = [];
  while (total + requiredBytes > softLimit && candidates.length) {
    const victim = candidates.shift() as T;
    victims.push(victim);
    total -= Number(victim.size || 0);
  }
  return total + requiredBytes > softLimit ? null : victims;
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

/** Set (as object) of streamUrls with a fully downloaded ("ready") entry.
 * Ported from `_track_render.py::updateAllDownloadButtons`. */
export function readyStreamUrls(downloads: OfflineDownload[]): Record<string, true> {
  const cached: Record<string, true> = {};
  (downloads || []).forEach((d) => {
    const url = d.streamUrl;
    if (typeof url === "string" && url && d.status === "ready") cached[url] = true;
  });
  return cached;
}

export interface StorageSummaryView {
  warn: boolean;
  summary: string;
  detail: string;
  pill: string;
  hasDownloads: boolean;
}
/** Texts/flags for the offline-storage summary. DOM writes stay legacy;
 * formatBytes passed in (lives in main.ts). */
export function storageSummaryView(info: OfflineStorageInfo, formatBytes: (n: number) => string): StorageSummaryView {
  const n = info.downloads.length;
  const warn = !!(
    info.appUsage >= info.softLimit * 0.8 ||
    (info.browserQuota && (info.browserUsage || 0) >= info.browserQuota * 0.8)
  );
  const summary = n
    ? n + " Offline-Download" + (n !== 1 ? "s" : "") + " \u00b7 " + formatBytes(info.appUsage) + " lokal gespeichert"
    : "Noch keine Offline-Downloads.";
  const parts = ["App-Budget " + formatBytes(info.appUsage) + " / " + formatBytes(info.softLimit)];
  if (info.browserQuota) {
    parts.push("Browser " + formatBytes(info.browserUsage || 0) + " / " + formatBytes(info.browserQuota));
  }
  if (info.persistent !== null) {
    parts.push(info.persistent ? "Persistent aktiv" : "Nicht persistent");
  }
  return { warn, summary, detail: parts.join(" \u00b7 "), pill: "Downloaded (" + n + ")", hasDownloads: n > 0 };
}

/** `<li>` HTML of the offline library list. Ported from `renderOfflineDownloadList`. */
export function offlineDownloadListHtml(
  downloads: OfflineDownload[],
  escHtml: (s: unknown) => string,
  formatBytes: (n: number) => string,
  placeholder: string
): string {
  if (!downloads || !downloads.length) {
    return '<li class="empty-downloads">Noch keine Offline-Downloads gespeichert.</li>';
  }
  return downloads
    .map((d) => {
      const thumbSrc = d.thumbnailUrl || placeholder;
      const subtitle = d.artist || d.relativePath || "";
      const statusText = d.status === "ready" ? "Offline bereit" : d.status || "unbekannt";
      return (
        '<li class="offline-download-item" data-stream-url="' + escHtml(d.streamUrl) + '">' +
        '<img class="offline-download-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="offline-download-meta">' +
        '<div class="offline-download-title">' + escHtml(d.title || "Unbenannter Download") + "</div>" +
        '<div class="offline-download-sub">' + escHtml(subtitle) + "</div>" +
        '<div class="offline-download-size">' + escHtml(statusText) + " \u00b7 " +
        escHtml(formatBytes(d.size || 0)) + " \u00b7 " + escHtml(formatDate(d.timestamp)) + "</div>" +
        "</div>" +
        '<button class="offline-download-delete" data-stream-url="' + escHtml(d.streamUrl) + '" title="Entfernen">Entfernen</button>' +
        "</li>"
      );
    })
    .join("");
}
