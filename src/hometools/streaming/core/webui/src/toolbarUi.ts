/**
 * Toolbar + edit-modal event wiring (view toggle, debounced search, sort,
 * filter popover/hidden chips, edit-modal buttons/keys). Ported from
 * `player_js/_library_tools.py`. Folder viewMode + showHidden stay legacy
 * state -> get/set hooks; inPlaylist via htState.
 */

import { getState } from "./stateBridge";

export const SEARCH_DEBOUNCE_MS = 150;

export interface ToolbarHooks {
  viewToggle: HTMLElement | null;
  searchInput: HTMLInputElement | null;
  sortField: HTMLElement | null;
  filterCombinedBtn: HTMLElement | null;
  filterHiddenBtn: HTMLElement | null;
  isVideoMode: boolean;
  isTrackViewVisible(): boolean;
  toggleTrackViewMode(): void;
  anyToolActive(): boolean;
  getViewMode(): string;
  setViewMode(m: string): void;
  getShowHidden(): boolean;
  setShowHidden(v: boolean): void;
  applyViewMode(): void;
  applyFilter(): void;
  showFolderView(): void;
  toggleFilterPopover(btn: HTMLElement): void;
  updateFilterChips(): void;
  routerUpdate(): void;
}

function lsSet(k: string, v: string): void {
  try {
    localStorage.setItem(k, v);
  } catch {
    /* quota / private mode */
  }
}

/** Folder-grid <-> list toggle (or table toggle inside track view). */
export function onViewToggle(h: ToolbarHooks): void {
  if (h.isTrackViewVisible()) {
    if (h.isVideoMode) return; // detail/table view is audio-only
    h.toggleTrackViewMode();
    return;
  }
  if (h.anyToolActive()) return; // locked while tools active
  const next = h.getViewMode() === "list" ? "grid" : "list";
  h.setViewMode(next);
  lsSet("ht-view-mode", next);
  const s = getState();
  if (s && s.inPlaylist) {
    h.applyViewMode();
    h.applyFilter();
  } else {
    h.showFolderView();
  }
  h.routerUpdate();
}

export function initToolbar(h: ToolbarHooks): void {
  h.viewToggle?.addEventListener("click", () => onViewToggle(h));

  /* Debounce: keeps typing snappy at 6000 items. */
  let timer: ReturnType<typeof setTimeout> | null = null;
  h.searchInput?.addEventListener("input", () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      h.applyFilter();
      h.routerUpdate();
    }, SEARCH_DEBOUNCE_MS);
  });

  h.sortField?.addEventListener("change", () => {
    h.applyFilter();
    h.routerUpdate();
  });

  const combined = h.filterCombinedBtn;
  combined?.addEventListener("click", (e) => {
    e.stopPropagation();
    h.toggleFilterPopover(combined);
  });

  h.filterHiddenBtn?.addEventListener("click", () => {
    const v = !h.getShowHidden();
    h.setShowHidden(v);
    lsSet("ht-show-hidden", v ? "1" : "0");
    h.updateFilterChips();
    h.applyFilter();
    h.routerUpdate();
  });
  h.updateFilterChips();
}

export interface EditModalEventsHooks {
  enabled: boolean;
  close(): void;
  submit(): void;
}

/** Cancel/save buttons, backdrop click, Enter submits, Escape closes. */
export function initEditModalEvents(h: EditModalEventsHooks): void {
  if (!h.enabled) return;
  const backdropEl = document.getElementById("edit-modal-backdrop");
  document.getElementById("edit-modal-cancel-btn")?.addEventListener("click", h.close);
  document.getElementById("edit-modal-save-btn")?.addEventListener("click", h.submit);
  backdropEl?.addEventListener("click", (e) => {
    if (e.target === backdropEl) h.close();
  });
  document.addEventListener("keydown", (e) => {
    const backdrop = document.getElementById("edit-modal-backdrop");
    if (!backdrop || backdrop.hasAttribute("hidden")) return;
    if (e.key === "Escape") {
      e.preventDefault();
      h.close();
    }
    if (e.key === "Enter" && (e.target as HTMLElement | null)?.tagName === "INPUT") {
      e.preventDefault();
      h.submit();
    }
  });
}

