/**
 * Lazy per-folder rating refresh. Ported from `player_js/_queue.py`
 * (refreshFolderRatings + `_ratingRefreshPath`, reset in refreshCatalog).
 * Dedupe state private; items/path via htState, side effects via hooks.
 */

import { getState } from "./stateBridge";
import { patchRatingsInPlace, ratingRefreshInfo } from "./catalogRefresh";

export interface RatingRefreshHooks {
  enabled: boolean;
  apiBase: string;
  applyFilter(): void;
}

let _ratingRefreshPath: string | null = null;

/** Forget last refreshed folder (user-triggered catalog refresh). */
export function resetRatingRefresh(): void {
  _ratingRefreshPath = null;
}

export function refreshFolderRatings(folderItems: Array<{ relative_path: string }>, h: RatingRefreshHooks): void {
  const s = getState();
  if (!s || !h.enabled || !folderItems.length) return;
  const refreshPath = s.currentPath;
  if (_ratingRefreshPath === refreshPath) return;
  _ratingRefreshPath = refreshPath;
  const paths = folderItems.map((t) => t.relative_path);
  fetch(h.apiBase + "/refresh-ratings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (!data || !data.ratings) return;
      const ratings = data.ratings as Record<string, unknown>;
      patchRatingsInPlace(s.allItems, ratings);
      patchRatingsInPlace(s.playlistItems, ratings);
      const infoEl = document.getElementById("refresh-info");
      if (infoEl && data.last_refresh) {
        const dt = new Date(data.last_refresh);
        infoEl.textContent = ratingRefreshInfo(Object.keys(ratings).length, data.changed, dt);
        infoEl.title = "Letzte Rating-Aktualisierung: " + dt.toLocaleString();
      }
      if (s.inPlaylist && s.currentPath === refreshPath) h.applyFilter();
    })
    .catch(() => {
      /* silent background refresh */
    });
}

