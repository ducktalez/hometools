/**
 * Shared view-entry points — ported from `player_js/_folder_browse.py`
 * (`_applyHeaderState`, `_enterTrackListView`, `_enterFolderGridView`).
 *
 * `applyHeaderState` is THE single place that touches header controls: every
 * view routes through it via the two entry points, so the header is
 * structurally identical everywhere (same controls, only content/enabled
 * state differ). Do not set header controls anywhere else.
 *
 * State via `htState` (currentPath, allItems, currentIndex); DOM elements and
 * legacy callbacks come in through `ViewHooks` (no closure reads).
 */

import { getState } from "./stateBridge";
import { leafName } from "./pathUtils";

export interface ViewDom {
  headerTitle: HTMLElement;
  backBtn: HTMLElement;
  playAllBtn: HTMLElement;
  folderGrid: HTMLElement;
  trackView: HTMLElement;
  filterBar: HTMLElement;
  playerBar: HTMLElement;
  trackCount: HTMLElement;
  searchInput: HTMLInputElement;
  player: HTMLMediaElement;
}

export interface ViewHooks {
  dom: ViewDom;
  /** Page title captured at startup (`originalTitle`). */
  originalTitle: string;
  renderBreadcrumb(): void;
  applyViewMode(): void;
  initGlobalSearch(): void;
  hideGlobalSearch(): void;
  initFilterBarScrollReveal(): void;
  applyFilter(): void;
  /** `_router.update()` if a router exists. */
  routerUpdate(): void;
}

export interface HeaderOpts {
  title?: string | null;
  backDisabled?: boolean;
  playAllDisabled?: boolean;
  /** Only for states with no catalog at all (loading / load error). */
  disableSearch?: boolean;
}

export interface TrackListOpts extends HeaderOpts {
  hideFilterBar?: boolean;
  collapseFilterBar?: boolean;
  resetIndex?: boolean;
  /** Views that render their own list (global search results). */
  skipFilter?: boolean;
  trackCount?: string | null;
}

export interface FolderGridOpts extends HeaderOpts {
  trackCount?: string | null;
  contentHtml?: string | null;
}

export function applyHeaderState(opts: HeaderOpts | null | undefined, h: ViewHooks): void {
  const o = opts || {};
  const st = getState();
  const d = h.dom;
  const path = st ? st.currentPath : "";
  d.headerTitle.textContent = o.title != null ? o.title : path ? leafName(path) : h.originalTitle;
  d.backBtn.classList.toggle("disabled", !!o.backDisabled);
  d.playAllBtn.classList.toggle("disabled", !!o.playAllDisabled);
  h.renderBreadcrumb();
  // View-toggle icon depends on the current view -> refresh on every change.
  h.applyViewMode();
  // Global search: present in every view once the catalog is loaded.
  if (!o.disableSearch && st && st.allItems.length > 0) h.initGlobalSearch();
  else h.hideGlobalSearch();
}

/** Header/toolbar state for every "flat list of tracks" view. Caller sets
 * playlistItems/currentPath/currentPlaylistId/inPlaylist BEFORE calling. */
export function enterTrackListView(opts: TrackListOpts | null | undefined, h: ViewHooks): void {
  const o = opts || {};
  const st = getState();
  const d = h.dom;
  applyHeaderState({ title: o.title, backDisabled: o.backDisabled, playAllDisabled: o.playAllDisabled }, h);
  d.folderGrid.classList.add("view-hidden");
  d.trackView.classList.remove("view-hidden");
  d.filterBar.classList.toggle("view-hidden", !!o.hideFilterBar);
  d.filterBar.classList.toggle("fb-scroll-hidden", !!o.collapseFilterBar);
  h.initFilterBarScrollReveal();
  d.playerBar.classList.remove("view-hidden");
  // Recently-played strip is a root/folder-grid-only section.
  const rs = document.getElementById("recent-section");
  if (rs) rs.hidden = true;
  // In-list filter box: reset so a previous list's filter doesn't hide items.
  d.searchInput.value = "";
  if (o.resetIndex && st) st.currentIndex = -1;
  if (!o.skipFilter) h.applyFilter();
  if (o.trackCount != null) d.trackCount.textContent = o.trackCount;
  h.routerUpdate();
}

/** Counterpart for every "grid of folders" view (browse, empty, loading, error). */
export function enterFolderGridView(opts: FolderGridOpts | null | undefined, h: ViewHooks): void {
  const o = opts || {};
  const st = getState();
  const d = h.dom;
  applyHeaderState(
    {
      title: o.title,
      backDisabled: o.backDisabled != null ? !!o.backDisabled : !(st && st.currentPath),
      playAllDisabled: o.playAllDisabled,
      disableSearch: o.disableSearch,
    },
    h,
  );
  d.folderGrid.classList.remove("view-hidden");
  d.trackView.classList.add("view-hidden");
  d.filterBar.classList.add("view-hidden");
  if (!d.player.currentSrc) d.playerBar.classList.add("view-hidden");
  if (o.trackCount != null) d.trackCount.textContent = o.trackCount;
  if (o.contentHtml != null) d.folderGrid.innerHTML = o.contentHtml;
  h.routerUpdate();
}

