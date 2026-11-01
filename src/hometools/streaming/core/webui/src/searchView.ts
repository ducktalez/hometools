/**
 * Global-search view — ported from `player_js/_search_filter.py`
 * (globalSearch, renderSearchResults, navigateToSearchFolder,
 * navigateToSearchResult, exitGlobalSearch). Data computation lives in
 * `search.ts`, row markup in `trackRows.ts`. Shared state (`allItems`,
 * `playlistItems`, `filteredItems`, `inPlaylist`, `currentPath`,
 * `globalSearchActive`, `shuffleMode`, `currentIndex`) via `htState`;
 * everything view-ish via `SearchViewHooks`.
 */

import { getState } from "./stateBridge";
import { buildFolderMatches, searchItems } from "./search";
import type { FolderMatch } from "./search";
import { searchFolderRowHtml, searchResultRowHtml } from "./trackRows";
import { rebuildShuffleQueue } from "./shuffle";

export interface SearchViewHooks {
  /** `_effectiveThreshold` */
  effectiveThreshold(): number;
  /** `showHidden` */
  showHidden(): boolean;
  itemNoun: string;
  esc(s: unknown): string;
  filePlaceholder: string;
  icFolderPlay: string;
  trackList(): HTMLElement | null;
  /** `_enterTrackListView(opts)` */
  enterTrackListView(opts: Record<string, unknown>): void;
  showFolderView(): void;
  playItem(item: LegacyMediaItem, idx: number): void;
  markActive(): void;
}

/** Header title for N search hits ("1 Ergebnis" / "N Ergebnisse"). */
export function searchTitle(total: number): string {
  return total + " Ergebnis" + (total !== 1 ? "se" : "");
}

/** Track-count label: "N Ordner · M items". */
export function searchTrackCountLabel(resultCount: number, folderCount: number, itemNoun: string): string {
  let label = resultCount + " " + (resultCount !== 1 ? itemNoun + "s" : itemNoun);
  if (folderCount) label = folderCount + " Ordner · " + label;
  return label;
}

function clearSearchInput(): void {
  const inp = document.getElementById("global-search-input") as HTMLInputElement | null;
  if (inp) inp.value = "";
}

export function navigateToSearchFolder(folderPath: string, h: SearchViewHooks): void {
  const st = getState();
  if (st) {
    st.globalSearchActive = false;
    st.currentPath = folderPath || "";
  }
  clearSearchInput();
  h.showFolderView();
}

export function exitGlobalSearch(h: SearchViewHooks): void {
  const st = getState();
  if (st) st.globalSearchActive = false;
  clearSearchInput();
  h.showFolderView();
}

export function renderSearchResults(results: LegacyMediaItem[], folderMatches: FolderMatch[] | null, h: SearchViewHooks): void {
  const trackList = h.trackList();
  if (!trackList) return;
  const folders = folderMatches || [];
  trackList.innerHTML = "";
  if (results.length === 0 && folders.length === 0) {
    trackList.innerHTML =
      '<li class="track-item" style="opacity:0.5;pointer-events:none"><div class="track-info"><div class="track-title">Keine Ergebnisse</div></div></li>';
    return;
  }
  folders.forEach((fm) => {
    const li = document.createElement("li");
    li.className = "track-item search-folder-item";
    li.innerHTML = searchFolderRowHtml(fm, h.esc, h.filePlaceholder, h.icFolderPlay);
    li.addEventListener("click", () => navigateToSearchFolder(fm.path, h));
    trackList.appendChild(li);
  });
  results.forEach((t, i) => {
    const li = document.createElement("li");
    li.className = "track-item";
    li.setAttribute("data-index", String(i));
    li.innerHTML = searchResultRowHtml(t, i, h.esc, h.filePlaceholder);
    // Play within search results — search stays open.
    li.addEventListener("click", () => {
      h.playItem(t, i);
      h.markActive();
    });
    trackList.appendChild(li);
  });
}

export function globalSearch(needle: string, h: SearchViewHooks): void {
  const st = getState();
  if (!st) return;
  const needleLower = needle.toLowerCase();
  const threshold = h.effectiveThreshold();
  const hiddenActive = threshold > 0 && !h.showHidden();
  const folderMatches = buildFolderMatches(st.allItems, needleLower, hiddenActive, threshold);
  const results = searchItems(st.allItems, needleLower, hiddenActive, threshold);
  st.globalSearchActive = true;
  // Search results double as current playlist (next/prev works) — must be
  // set BEFORE enterTrackListView (contract: caller sets these first).
  st.playlistItems = results;
  st.filteredItems = results;
  st.inPlaylist = true;
  const totalCount = folderMatches.length + results.length;
  // skipFilter: renderSearchResults below owns the list; hideFilterBar: chips
  // don't apply to search results.
  h.enterTrackListView({
    title: searchTitle(totalCount),
    backDisabled: false,
    playAllDisabled: true,
    hideFilterBar: true,
    skipFilter: true,
    trackCount: searchTrackCountLabel(results.length, folderMatches.length, h.itemNoun),
  });
  if (st.shuffleMode) rebuildShuffleQueue(st.currentIndex >= 0 ? st.currentIndex : 0);
  renderSearchResults(results, folderMatches, h);
}

