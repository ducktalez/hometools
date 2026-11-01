/**
 * Playlist item reorder (drag & drop target) — ported from
 * `player_js/_smart_playlists.py` (reorderPlaylistItem, _applyPlaylistUpdate).
 * `movePlaylistItem` (up/down) had no callers and was dropped.
 *
 * State via `htState` (allItems, playlistItems, filteredItems, currentIndex,
 * userPlaylists, currentPlaylistId); persistence + re-render come in via
 * `ReorderHooks`.
 */

import { getState } from "./stateBridge";
import { indexOfPath } from "./catalogQuery";
import { snapshotPlaylists, restorePlaylists } from "./playlistSync";
import type { PlaylistLike } from "./playlistActions";

export interface ReorderHooks {
  /** `PLAYLISTS_API_PATH` */
  apiPath: string;
  toast(msg: string): void;
  renderTracks(items: LegacyMediaItem[], force: boolean): void;
  saveFavoritesOrder(paths: string[]): void;
  saveFolderOrder(folderPath: string, paths: string[]): void;
}

/** Move `rp` to `toIndex` (clamped). Returns the new order, or null if absent. */
export function reorderPaths(paths: string[], rp: string, toIndex: number): string[] | null {
  const old = paths.indexOf(rp);
  if (old < 0) return null;
  const out = paths.slice();
  out.splice(old, 1);
  out.splice(Math.max(0, Math.min(toIndex, out.length)), 0, rp);
  return out;
}

/** Show `resolved` as the current list, keeping the playing track's index. */
function showResolved(resolved: LegacyMediaItem[], h: ReorderHooks): void {
  const st = getState();
  if (!st) return;
  const playing = st.currentIndex >= 0 && st.filteredItems[st.currentIndex] ? st.filteredItems[st.currentIndex].relative_path : null;
  st.playlistItems = resolved;
  st.filteredItems = resolved;
  if (playing) {
    const i = indexOfPath(resolved, playing);
    if (i >= 0) st.currentIndex = i;
  }
  h.renderTracks(resolved, true);
}

/** Re-resolve a playlist's items against the catalog and show them. */
export function applyPlaylistUpdate(pl: PlaylistLike, h: ReorderHooks): void {
  const st = getState();
  if (!st) return;
  const resolved: LegacyMediaItem[] = [];
  (pl.items || []).forEach((rp) => {
    const m = st.allItems.find((it) => it.relative_path === rp);
    if (m) resolved.push(m);
  });
  showResolved(resolved, h);
}

export function reorderPlaylistItem(relativePath: string, toIndex: number, h: ReorderHooks): void {
  const st = getState();
  if (!st || !st.currentPlaylistId) return;
  const curId = st.currentPlaylistId;
  if (curId === "__alltitles__") return; // read-only union

  // Favorites / folder: client-side order (localStorage + server sync in legacy hooks)
  if (curId === "__favorites__" || curId === "__folder__") {
    const paths = reorderPaths(st.playlistItems.map((it) => it.relative_path), relativePath, toIndex);
    if (!paths) return;
    if (curId === "__favorites__") h.saveFavoritesOrder(paths);
    else h.saveFolderOrder(st.currentPath, paths);
    const byPath: Record<string, LegacyMediaItem> = {};
    st.playlistItems.forEach((it) => (byPath[it.relative_path] = it));
    showResolved(paths.map((rp) => byPath[rp]).filter(Boolean), h);
    return;
  }

  // Server-backed playlist: optimistic local reorder first
  const snap = snapshotPlaylists() as PlaylistLike[];
  const localPl = (st.userPlaylists as PlaylistLike[]).find((p) => p.id === curId);
  if (localPl) {
    const next = reorderPaths(localPl.items || [], relativePath, toIndex);
    if (next) {
      localPl.items = next;
      applyPlaylistUpdate(localPl, h);
    }
  }
  fetch(h.apiPath + "/items", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playlist_id: curId, relative_path: relativePath, to_index: toIndex }),
  })
    .then((r) => r.json())
    .then((d) => {
      if (!d.playlist) return;
      const l = st.userPlaylists as PlaylistLike[];
      const idx = l.findIndex((p) => p.id === curId);
      if (idx >= 0) l[idx] = d.playlist;
      if (st.currentPlaylistId === curId) applyPlaylistUpdate(d.playlist, h);
    })
    .catch(() => {
      restorePlaylists(snap);
      if (st.currentPlaylistId === curId && localPl) {
        applyPlaylistUpdate(snap.find((p) => p.id === curId) || localPl, h);
      }
      h.toast("Fehler beim Verschieben — rückgängig");
    });
}

