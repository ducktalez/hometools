/**
 * Offline-download counters (folder card badge + "Downloaded (n)" pill).
 * Ported from `player_js/_track_render.py::updateOfflineFolderCount`.
 */
import { getAllDownloads } from "./offlineDb";
export interface OfflinePill {
  textContent: string | null;
  classList: { toggle(c: string, force?: boolean): unknown };
}
/** Count of ready downloads -> `#offline-folder-count` and the pill. Never rejects. */
export function updateOfflineFolderCount(pill: OfflinePill | null): Promise<void> {
  return getAllDownloads()
    .then((downloads) => {
      const ready = downloads.filter((d) => d.status === "ready").length;
      const el = document.getElementById("offline-folder-count");
      if (el) el.textContent = String(ready);
      if (pill) {
        pill.textContent = "Downloaded (" + ready + ")";
        pill.classList.toggle("has-downloads", ready > 0);
      }
    })
    .catch(() => {});
}