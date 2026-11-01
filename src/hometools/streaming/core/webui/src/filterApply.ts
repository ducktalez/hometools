/**
 * Filter chips + filter/sort/render pipeline — ported from
 * `player_js/_search_filter.py` (updateFilterChips, applyFilter). Pure parts
 * live in `filterChain.ts`, `catalogQuery.ts::sortTracks` and
 * `filterPopover.ts` (chip views). `playlistItems` via `htState`; filter
 * state, DOM elements and render via `FilterApplyHooks`.
 */

import { getState } from "./stateBridge";
import { applyFilterChain } from "./filterChain";
import { sortTracks } from "./catalogQuery";
import { filterCombinedChipView, filterHiddenChipView } from "./filterPopover";
import type { FilterPopoverState } from "./filterPopover";

export interface FilterApplyHooks {
  combinedBtn(): HTMLElement | null;
  hiddenBtn(): HTMLElement | null;
  getFilter(): FilterPopoverState;
  icFilter: string;
  icEye: string;
  /** `_effectiveThreshold` */
  effectiveThreshold(): number;
  showHidden(): boolean;
  /** Re-render the popover body if it is currently open. */
  refreshOpenPopover(): void;
  /** `searchInput.value` / `sortField.value` */
  searchValue(): string;
  sortValue(): string;
  /** `_locallyDeletedPaths` */
  locallyDeleted(): Record<string, boolean>;
  debugFilter: boolean;
  justRatedPath(): string | null;
  /** `_savedFavorites` */
  savedFavorites(): Record<string, boolean>;
  /** truthiness of `_currentPlaylistId` */
  hasCustomPlaylist(): boolean;
  renderTracks(items: LegacyMediaItem[], force?: boolean): void;
}

function applyChip(btn: HTMLElement, v: { html: string; active: boolean; title: string }): void {
  btn.innerHTML = v.html;
  btn.classList.toggle("active", v.active);
  btn.title = v.title;
}

/** Refresh the "Filtern" and "Ausgeblendet" chip buttons. */
export function updateFilterChips(h: FilterApplyHooks): void {
  const st = getState();
  const combined = h.combinedBtn();
  if (combined) applyChip(combined, filterCombinedChipView(h.getFilter(), h.icFilter));
  // Keep an open popover (star state, genre <select>) in sync, e.g. after navigating.
  h.refreshOpenPopover();
  const hiddenBtn = h.hiddenBtn();
  if (hiddenBtn) {
    const hv = filterHiddenChipView(st ? st.playlistItems : [], h.effectiveThreshold(), h.showHidden(), h.icEye);
    if (hv) {
      hiddenBtn.style.display = "";
      applyChip(hiddenBtn, hv);
    } else {
      hiddenBtn.style.display = "none";
    }
  }
}

/** Items to show for the current filter/search/sort settings. */
export function computeFilteredItems(h: FilterApplyHooks): LegacyMediaItem[] {
  const st = getState();
  const base = st ? st.playlistItems : [];
  // Safety net: strip locally-deleted paths however playlistItems was last set.
  const deleted = h.locallyDeleted();
  let items = Object.keys(deleted).length ? base.filter((it) => !deleted[it.relative_path]) : base;
  const f = h.getFilter();
  items = applyFilterChain(items, {
    needle: h.searchValue().trim().toLowerCase(),
    debugFilter: h.debugFilter,
    effectiveThreshold: h.effectiveThreshold(),
    showHidden: h.showHidden(),
    justRatedPath: h.justRatedPath(),
    filterRating: f.rating,
    filterFav: f.fav,
    filterGenre: f.genre,
    savedFavorites: h.savedFavorites(),
  });
  return sortTracks(items, h.sortValue(), h.hasCustomPlaylist());
}

export function applyFilter(force: boolean | undefined, h: FilterApplyHooks): void {
  h.renderTracks(computeFilteredItems(h), force);
}

