/**
 * Track-list detail/table view toggle. Ported from `player_js/_queue.py`
 * (_toggleTrackViewMode/_applyTrackViewMode/_isTrackViewVisible).
 * `trackViewMode` stays legacy (read by rendering) -> get/set via hooks.
 */

import { viewToggleView } from "./chromeHtml";

export interface TrackViewModeHooks {
  trackList: HTMLElement;
  trackView: HTMLElement | null;
  viewToggle: HTMLElement | null;
  isVideoMode: boolean;
  tableHeaderHtml: string;
  icList: string;
  icTable: string;
  getMode(): string;
  setMode(m: string): void;
  rerender(): void;
}

export function isTrackViewVisible(trackView: HTMLElement | null): boolean {
  return !!trackView && !trackView.classList.contains("view-hidden");
}

export function applyTrackViewMode(h: TrackViewModeHooks): void {
  const tableMode = h.getMode() === "table" && !h.isVideoMode;
  h.trackList.classList.toggle("table-mode", tableMode);
  let hdr = document.getElementById("track-table-header");
  if (tableMode) {
    if (!hdr) {
      hdr = document.createElement("div");
      hdr.id = "track-table-header";
      hdr.className = "track-table-header";
      hdr.innerHTML = h.tableHeaderHtml;
      h.trackList.parentNode?.insertBefore(hdr, h.trackList);
    }
  } else if (hdr) {
    hdr.remove();
  }
  if (h.viewToggle && isTrackViewVisible(h.trackView)) {
    const v = viewToggleView(tableMode, h.isVideoMode);
    h.viewToggle.innerHTML = v.useListIcon ? h.icList : h.icTable;
    h.viewToggle.title = v.title;
    h.viewToggle.classList.toggle("view-toggle-locked", v.locked);
  }
}

/** rows <-> table; persists, re-applies, forces list rebuild. */
export function toggleTrackViewMode(h: TrackViewModeHooks): void {
  const next = h.getMode() === "table" ? "rows" : "table";
  h.setMode(next);
  try {
    localStorage.setItem("ht-track-view-mode", next);
  } catch {
    /* quota / private mode */
  }
  applyTrackViewMode(h);
  h.rerender();
}

export interface FolderViewModeHooks {
  folderGrid: HTMLElement;
  viewToggle: HTMLElement;
  icList: string;
  icGrid: string;
  toolActive: boolean;
  viewMode: string;
}

/** Folder-grid list/grid mode + toggle button state (tools lock list view). */
export function applyFolderViewMode(h: FolderViewModeHooks): void {
  const g = h.folderGrid.classList;
  const t = h.viewToggle;
  if (h.toolActive) {
    g.add("list-mode");
    g.add("filenames-mode");
    t.innerHTML = h.icList;
    t.title = "Tools aktiv \u2014 Listenansicht mit Dateinamen";
    t.classList.add("view-toggle-locked");
  } else if (h.viewMode === "list") {
    g.add("list-mode");
    g.remove("filenames-mode");
    t.innerHTML = h.icGrid;
    t.title = "Listenansicht \u2014 Klick f\u00fcr Kachelansicht";
    t.classList.remove("view-toggle-locked");
  } else {
    g.remove("list-mode");
    g.remove("filenames-mode");
    t.innerHTML = h.icList;
    t.title = "Kachelansicht \u2014 Klick f\u00fcr Listenansicht";
    t.classList.remove("view-toggle-locked");
  }
}
