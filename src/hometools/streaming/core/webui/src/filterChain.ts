/**
 * Rating/favorite/genre/search filter chain applied to a playlist before
 * rendering.
 *
 * Ported from `player_js/_search_filter.py`'s `applyFilter()` — the pure
 * filter/annotate chain (both the normal-mode and `DEBUG_FILTER`-mode
 * branches) split out from the DOM reads at the top of that function
 * (`searchInput.value`/`sortField.value`) and the final `renderTracks()`
 * call, which stay in `_search_filter.py`. Explicit-parameter pattern: every
 * value `applyFilter()` used to read from closure/module-scope globals
 * (`showHidden`, `filterRating`, `filterFav`, `filterGenre`,
 * `_effectiveThreshold`, `_justRatedPath`, `_savedFavorites`, `DEBUG_FILTER`)
 * is now one field of `FilterChainOptions`.
 *
 * `_hiddenShown`/`_debugReason` annotations are added via a shallow object
 * spread clone (never mutates an item already in `playlistItems`) — same
 * behavior as the legacy `for...in hasOwnProperty` copy loops.
 */

export interface FilterChainOptions {
  needle: string;
  debugFilter: boolean;
  effectiveThreshold: number;
  showHidden: boolean;
  justRatedPath: string | null;
  filterRating: number;
  filterFav: boolean;
  filterGenre: string;
  savedFavorites: Record<string, boolean>;
}

function matchesNeedle(t: LegacyMediaItem, needle: string): boolean {
  return (
    (t.title || "").toLowerCase().indexOf(needle) >= 0 ||
    (t.artist || "").toLowerCase().indexOf(needle) >= 0 ||
    (t.relative_path || "").toLowerCase().indexOf(needle) >= 0
  );
}

export function applyFilterChain(items: LegacyMediaItem[], opts: FilterChainOptions): LegacyMediaItem[] {
  const {
    needle,
    debugFilter,
    effectiveThreshold,
    showHidden,
    justRatedPath,
    filterRating,
    filterFav,
    filterGenre,
    savedFavorites,
  } = opts;

  if (debugFilter) {
    // ── Debug mode: annotate items with reasons instead of removing ──
    // showHidden=true  → rating-below-threshold items get _hiddenShown (grayed, same UX as normal mode)
    // showHidden=false → rating-below-threshold items get _debugReason (visible with filter-reason overlay)
    items = items.map((t) => {
      const r = t.rating || 0;
      // Rating threshold: when showHidden=true, gray items in-place (don't annotate as debug-filtered).
      // The just-rated item is always grayed regardless of showHidden — never debug-filtered away.
      if (effectiveThreshold > 0 && r > 0 && r < effectiveThreshold) {
        if (showHidden || t.relative_path === justRatedPath) {
          return { ...t, _hiddenShown: true };
        }
        return { ...t, _debugReason: "Rating " + r + "\u2605 < Schwelle " + effectiveThreshold };
      }
      const reasons: string[] = [];
      if (filterRating > 0 && r < filterRating && t.relative_path !== justRatedPath) {
        reasons.push("Quick-Filter: Rating < " + filterRating + "\u2605");
      }
      if (filterFav && !savedFavorites[t.relative_path]) {
        reasons.push("Kein Favorit");
      }
      if (filterGenre && t.genre !== filterGenre) {
        reasons.push("Genre \u2260 " + filterGenre);
      }
      if (reasons.length > 0) {
        // Clone the item so we don't mutate the original in playlistItems
        return { ...t, _debugReason: reasons.join(" | ") };
      }
      return t;
    });
    // Text search always filters even in debug mode
    if (needle) {
      items = items.filter((t) => matchesNeedle(t, needle));
    }
    return items;
  }

  // ── Normal mode ──
  // Effective threshold: tracks with rating < threshold are "ausgeblendet".
  // Unrated tracks (rating 0) are always shown regardless of threshold.
  // showHidden=false  → hidden songs filtered out entirely.
  // showHidden=true   → hidden songs kept at their natural position, grayed
  //                     out so the full list is visible.
  // The just-rated track (justRatedPath) is NEVER removed by this step,
  // even when showHidden=false — it is grayed in-place instead, so the
  // user can see and undo the change that just crossed the threshold.
  if (effectiveThreshold > 0) {
    if (!showHidden) {
      items = items.filter((t) => {
        const r = t.rating || 0;
        return r === 0 || r >= effectiveThreshold || t.relative_path === justRatedPath;
      });
    }
    // Mark hidden items in-place — they stay at their sorted position.
    // Runs in both showHidden branches so the just-rated exception above
    // (kept in the array when showHidden=false) still gets grayed.
    items = items.map((t) => {
      const r = t.rating || 0;
      if (r > 0 && r < effectiveThreshold) {
        return { ...t, _hiddenShown: true };
      }
      return t;
    });
  }
  if (needle) {
    items = items.filter((t) => matchesNeedle(t, needle));
  }
  // Quick-filters (never affect hidden-shown items — they are already grayed,
  // and never remove the just-rated item — it gets marked hidden-shown below
  // instead of being filtered out, mirroring the threshold exception above).
  if (filterRating > 0) {
    items = items.filter((t) => t._hiddenShown || t.relative_path === justRatedPath || (t.rating || 0) >= filterRating);
    items = items.map((t) => {
      if (!t._hiddenShown && t.relative_path === justRatedPath && (t.rating || 0) < filterRating) {
        return { ...t, _hiddenShown: true };
      }
      return t;
    });
  }
  if (filterFav) {
    items = items.filter((t) => t._hiddenShown || !!savedFavorites[t.relative_path]);
  }
  if (filterGenre) {
    items = items.filter((t) => t._hiddenShown || t.genre === filterGenre);
  }
  return items;
}

