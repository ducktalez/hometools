/**
 * renderTracks — ported from `player_js/_track_render.py`. Sets
 * `htState.filteredItems`, updates the count label, applies the render guard
 * (skips the DOM rebuild when nothing visible changed) and hands over to the
 * windowed renderer. Render-guard key private here; reset via
 * `resetRenderGuard()` whenever `allItems` changes.
 */

import { getState } from "./stateBridge";
import { ensureDupeIndex } from "./dupeState";
import { toolFlags } from "./toolsPanel";
import { rebuildShuffleQueue } from "./shuffle";
import { emptyManualPlaylistId, emptyPlaylistHtml, ADD_BTN_ID } from "./trackPicker";

export interface FilterSnapshot {
  rating: number;
  fav: boolean;
  genre: string;
}

export interface RenderTracksHooks {
  itemNoun: string;
  debugFilter: boolean;
  trackList: HTMLElement;
  trackCount: HTMLElement | null;
  searchInput: HTMLInputElement | null;
  sortField: HTMLSelectElement | null;
  getFilter(): FilterSnapshot;
  effectiveThreshold(): number;
  showHidden(): boolean;
  stopRenderObserver(): void;
  startWindowedRender(realTracks: LegacyMediaItem[]): void;
  markActive(): void;
  openTrackPicker(playlistId: string): void;
}

type Track = LegacyMediaItem & { _debugReason?: string; _hiddenShown?: boolean };

let _rgKey = "";

/** Force the next renderTracks() to rebuild the DOM. */
export function resetRenderGuard(): void {
  _rgKey = "";
}

/** Fingerprint of every input that can change the rendered list. */
export function renderGuardKey(
  playlistId: string,
  currentPath: string,
  search: string,
  sort: string,
  trackCount: number,
  f: FilterSnapshot,
  threshold: number,
  showHidden: boolean,
  justRated: string | null
): string {
  return [
    playlistId || "",
    currentPath,
    search,
    sort,
    String(trackCount),
    String(f.rating),
    f.fav ? "1" : "0",
    f.genre || "",
    String(threshold),
    showHidden ? "1" : "0",
    justRated || "",
  ].join("\x00");
}

export function renderTracks(tracks: Track[], force: boolean | undefined, h: RenderTracksHooks): void {
  const st = getState();
  if (!st) return;
  /* Ensure dupe data is available when the dupe tool is active */
  if (toolFlags().duplicates) ensureDupeIndex(st.allItems);
  /* Debug-dimmed items stay out of filteredItems / shuffle */
  const realTracks = h.debugFilter ? tracks.filter((t) => !t._debugReason) : tracks;
  st.filteredItems = realTracks;
  if (st.shuffleMode) rebuildShuffleQueue(st.currentIndex >= 0 ? st.currentIndex : 0);

  const hiddenShown = realTracks.filter((t) => !!t._hiddenShown).length;
  const visible = realTracks.length - hiddenShown;
  if (h.trackCount) h.trackCount.textContent = visible + " " + (visible !== 1 ? h.itemNoun + "s" : h.itemNoun);

  const key = renderGuardKey(
    st.currentPlaylistId,
    st.currentPath,
    h.searchInput ? h.searchInput.value.trim() : "",
    h.sortField ? h.sortField.value : "",
    tracks.length,
    h.getFilter(),
    h.effectiveThreshold(),
    h.showHidden(),
    st.justRatedPath
  );
  if (!force && key === _rgKey && h.trackList.children.length > 0) {
    h.markActive(); /* nothing visually changed — refresh highlight only */
    return;
  }
  _rgKey = key;

  h.stopRenderObserver();
  h.trackList.innerHTML = "";
  /* Series lists get a fixed-width .track-num that fits "S01E12" */
  h.trackList.classList.toggle("track-list--series", tracks.some((t) => (t.season || 0) > 0));

  if (!tracks.length) {
    const emptyPlId = emptyManualPlaylistId();
    if (emptyPlId) {
      h.trackList.innerHTML = emptyPlaylistHtml();
      const addBtn = document.getElementById(ADD_BTN_ID);
      if (addBtn) addBtn.addEventListener("click", () => h.openTrackPicker(emptyPlId));
      return;
    }
    h.trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
    return;
  }
  /* Episode-gap placeholders, sentinel, first batch, lazy observer: trackRenderWindow.ts */
  h.startWindowedRender(realTracks);
}

