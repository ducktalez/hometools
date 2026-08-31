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

