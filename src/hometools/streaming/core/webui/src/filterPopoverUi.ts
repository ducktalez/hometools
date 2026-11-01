/**
 * Combined "Filtern" popover (rating + favorite + genre) wiring/lifecycle —
 * ported from `player_js/_search_filter.py` (_wireFilterPopoverBody,
 * _renderFilterPopoverBody, _closeFilterPopover, _toggleFilterPopover).
 * Markup lives in `filterPopover.ts`. The cleanup handle (was
 * `_filterPopoverCleanup` in `_core.py`) is module-private; filter state is
 * shared with the legacy script, so it is read/written through hooks.
 */

import { filterPopoverBodyHtml } from "./filterPopover";
import type { FilterPopoverState, FilterPopoverIcons } from "./filterPopover";

export interface FilterPopoverHooks {
  /** `_collectGenres(playlistItems)` */
  genres(): string[];
  getFilter(): FilterPopoverState;
  /** Assign legacy `filterRating/filterFav/filterGenre` (only given keys). */
  setFilter(p: Partial<FilterPopoverState>): void;
  icons: FilterPopoverIcons;
  esc(s: unknown): string;
  /** updateFilterChips(); applyFilter(); router update */
  onChange(): void;
}

const POPOVER_ID = "ht-filter-popover";

let _cleanup: (() => void) | null = null;

function store(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* quota / private mode */
  }
}

function bodyHtml(h: FilterPopoverHooks): string {
  return filterPopoverBodyHtml(h.genres(), h.getFilter(), h.icons, h.esc);
}

function wireBody(pop: HTMLElement, h: FilterPopoverHooks): void {
  pop.querySelectorAll<HTMLElement>(".filter-popover-star").forEach((starBtn) => {
    starBtn.addEventListener("click", () => {
      const val = Number(starBtn.dataset.star);
      const rating = h.getFilter().rating === val ? 0 : val;
      h.setFilter({ rating });
      store("ht-filter-rating", String(rating));
      h.onChange();
    });
  });
  const favCb = pop.querySelector<HTMLInputElement>("#filter-popover-fav");
  if (favCb) {
    favCb.addEventListener("change", () => {
      h.setFilter({ fav: favCb.checked });
      store("ht-filter-fav", favCb.checked ? "1" : "0");
      h.onChange();
    });
  }
  const genreSel = pop.querySelector<HTMLSelectElement>("#filter-popover-genre-select");
  if (genreSel) {
    genreSel.addEventListener("change", () => {
      h.setFilter({ genre: genreSel.value });
      store("ht-filter-genre", genreSel.value);
      h.onChange();
    });
  }
  const resetBtn = pop.querySelector("#filter-popover-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      h.setFilter({ rating: 0, fav: false, genre: "" });
      store("ht-filter-rating", "0");
      store("ht-filter-fav", "0");
      store("ht-filter-genre", "");
      h.onChange();
    });
  }
}

/** Re-render an already-open popover's contents (no-op when closed). */
export function renderFilterPopoverBody(h: FilterPopoverHooks): void {
  const pop = document.getElementById(POPOVER_ID);
  if (!pop) return;
  pop.innerHTML = bodyHtml(h);
  wireBody(pop, h);
}

export function closeFilterPopover(): void {
  if (_cleanup) {
    _cleanup();
    _cleanup = null;
  }
  const old = document.getElementById(POPOVER_ID);
  if (old) old.remove();
}

export function isFilterPopoverOpen(): boolean {
  return !!document.getElementById(POPOVER_ID);
}

/** Open anchored to `btn`, or close if already open. */
export function toggleFilterPopover(btn: HTMLElement, h: FilterPopoverHooks): void {
  if (document.getElementById(POPOVER_ID)) {
    closeFilterPopover();
    return;
  }
  const pop = document.createElement("div");
  pop.id = POPOVER_ID;
  pop.className = "filter-popover";
  pop.innerHTML = bodyHtml(h);
  document.body.appendChild(pop);
  const rect = btn.getBoundingClientRect();
  pop.style.right = Math.max(4, window.innerWidth - rect.right) + "px";
  const spaceBelow = window.innerHeight - rect.bottom;
  if (spaceBelow >= pop.offsetHeight + 8) {
    pop.style.top = rect.bottom + 6 + "px";
  } else {
    pop.style.top = Math.max(4, rect.top - pop.offsetHeight - 6) + "px";
  }
  wireBody(pop, h);
  const onOutside = (e: Event): void => {
    const t = e.target as Node;
    if (!pop.contains(t) && t !== btn && !btn.contains(t)) closeFilterPopover();
  };
  const onEsc = (e: KeyboardEvent): void => {
    if (e.key === "Escape") closeFilterPopover();
  };
  setTimeout(() => {
    document.addEventListener("click", onOutside);
    document.addEventListener("keydown", onEsc);
  }, 0);
  _cleanup = () => {
    document.removeEventListener("click", onOutside);
    document.removeEventListener("keydown", onEsc);
  };
}

