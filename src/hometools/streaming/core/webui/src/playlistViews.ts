/**
 * Playlist views + add-to-playlist modal — ported from
 * `player_js/_smart_playlists.py` (showUserPlaylistView, playUserPlaylist,
 * openPlaylistModal, closePlaylistModal, renderPlaylistModalList).
 *
 * State via `htState` (allItems, playlistItems, inPlaylist, currentPath,
 * userPlaylists, currentPlaylistId, playlistAddPath). Everything view-ish
 * (header entry, filter, favorites order, playback) via `PlaylistViewHooks`.
 */

import { getState } from "./stateBridge";
import { playlistModalListHtml } from "./smartEditorModal";
import type { UserPlaylist } from "./smartPlaylist";

export interface PlaylistViewHooks {
  toast(msg: string): void;
  esc(s: unknown): string;
  /** `_enterTrackListView({title})` */
  enterTrackListView(opts: { title: string }): void;
  applyFilter(): void;
  playTrack(index: number): void;
  /** `_savedFavorites` (relative_path -> true) */
  savedFavorites(): Record<string, boolean>;
  sortFavoritesByOrder(items: LegacyMediaItem[]): LegacyMediaItem[];
  loadFavoritesOrder(): string[];
  loadFavoritesOrderAsync(cb: (serverOrder: string[]) => void): void;
  /** `_resolvePlaylistItems(plId)` -> `{pl, resolved}` or null */
  resolvePlaylist(plId: string): { pl: { name?: string }; resolved: LegacyMediaItem[] } | null;
  /** `addToPlaylist(plId, relativePath)` */
  addToPlaylist(plId: string, relativePath: string): void;
}

/** Browse a playlist (user, smart, `__favorites__`, `__alltitles__`) without auto-play. */
export function showUserPlaylistView(plId: string, h: PlaylistViewHooks): void {
  const st = getState();
  if (!st) return;
  const enter = (id: string, items: LegacyMediaItem[], title: string) => {
    st.currentPlaylistId = id;
    st.playlistItems = items;
    st.inPlaylist = true;
    st.currentPath = "";
    h.enterTrackListView({ title });
  };

  if (plId === "__alltitles__") {
    if (st.allItems.length === 0) {
      h.toast("Keine Titel in der Bibliothek vorhanden");
      return;
    }
    enter("__alltitles__", st.allItems.slice(), "Titel");
    return;
  }
  if (plId === "__favorites__") {
    const favs = h.savedFavorites();
    const favItems = st.allItems.filter((t) => !!favs[t.relative_path]);
    if (favItems.length === 0) {
      h.toast("Keine Favoriten vorhanden");
      return;
    }
    enter("__favorites__", h.sortFavoritesByOrder(favItems), "Favoriten");
    // Pre-warm: fetch server-side order, re-sort if it differs
    h.loadFavoritesOrderAsync((serverOrder) => {
      if (!serverOrder.length) return;
      if (st.currentPlaylistId !== "__favorites__") return;
      if (JSON.stringify(h.loadFavoritesOrder()) === JSON.stringify(serverOrder)) return;
      st.playlistItems = h.sortFavoritesByOrder(favItems);
      h.applyFilter();
    });
    return;
  }
  const data = h.resolvePlaylist(plId);
  if (!data) {
    /* Existing manual playlist without (resolvable) items: open the empty view
       so the user can see/rename it instead of a dead-end toast. */
    const pl = ((st.userPlaylists || []) as { id?: string; name?: string; smart?: unknown }[]).find((p) => p.id === plId);
    if (pl && !pl.smart) {
      enter(plId, [], pl.name || "");
      return;
    }
    h.toast("Keine Titel in dieser Playlist gefunden");
    return;
  }
  enter(plId, data.resolved, data.pl.name || "");
}

/** Same entry as the browse view (shared header state), plus auto-play. */
export function playUserPlaylist(plId: string, h: PlaylistViewHooks): void {
  const st = getState();
  if (!st) return;
  const before = st.playlistItems;
  showUserPlaylistView(plId, h);
  if (st.playlistItems !== before && st.playlistItems.length > 0) h.playTrack(0);
}

export function openPlaylistModal(relativePath: string, h: PlaylistViewHooks): void {
  const st = getState();
  if (st) st.playlistAddPath = relativePath;
  const backdrop = document.getElementById("playlist-modal-backdrop");
  if (!backdrop) return;
  backdrop.hidden = false;
  document.body.classList.add("modal-open");
  renderPlaylistModalList(h);
}

export function closePlaylistModal(): void {
  const backdrop = document.getElementById("playlist-modal-backdrop");
  if (backdrop) backdrop.hidden = true;
  document.body.classList.remove("modal-open");
  const st = getState();
  if (st) st.playlistAddPath = "";
}

export function renderPlaylistModalList(h: PlaylistViewHooks): void {
  const st = getState();
  const listEl = document.getElementById("playlist-modal-list");
  if (!st || !listEl) return;
  listEl.innerHTML = playlistModalListHtml(st.userPlaylists as UserPlaylist[], h.esc);
  listEl.querySelectorAll<HTMLElement>(".playlist-modal-item").forEach((el) => {
    el.addEventListener("click", () => h.addToPlaylist(el.dataset.id || "", st.playlistAddPath));
  });
}

