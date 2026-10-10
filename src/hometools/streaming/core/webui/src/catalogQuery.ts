/**
 * Catalog filtering by path prefix.
 *
 * Ported from `player_js/_queue.py`'s `itemsUnder(path)`. Legacy version
 * read the mutable `allItems` global straight from its enclosing IIFE
 * scope (not reachable from here — see main.ts header). Explicit-parameter
 * pattern, same as `smartPlaylist.ts`/`catalogCache.ts`: `_queue.py` keeps
 * a thin bare-name wrapper `itemsUnder(path)` that forwards to
 * `window._itemsUnder(path, allItems)`, so all 13 existing call sites
 * across the other `player_js/*.py` fragments stay untouched.
 */

/** Items whose `relative_path` sits under `path` (recursive). Empty/falsy `path` = all items. */
export function itemsUnder(path: string, allItems: LegacyMediaItem[]): LegacyMediaItem[] {
  if (!path) return allItems;
  const prefix = path + "/";
  return allItems.filter((it) => it.relative_path.startsWith(prefix));
}

/**
 * Distinct, sorted genres of `items` (feeds the filter popover's `<select>`).
 *
 * Ported from `_search_filter.py`'s `_collectPlaylistGenres()` — read the
 * mutable `playlistItems` global, now an explicit param (call site passes
 * it through).
 */
export function collectGenres(items: LegacyMediaItem[] | null | undefined): string[] {
  const genres: Record<string, boolean> = {};
  (items || []).forEach((t) => {
    if (t.genre) genres[t.genre] = true;
  });
  return Object.keys(genres).sort();
}

/**
 * Copy-on-write field patch: every entry with `relPath` in each array is
 * REPLACED by `{...old, ...fields}` (never mutated). Each array holds its own
 * reference (filter() copies refs), so all must be patched individually —
 * patching allItems alone left playlistItems stale (rating-filter bug).
 *
 * Ported from `_library_tools.py::_patchAllItemsRating` (arrays now explicit).
 */
export function replaceItemFields(
  arrays: Array<LegacyMediaItem[] | null | undefined>,
  relPath: string,
  fields: Partial<LegacyMediaItem>
): void {
  arrays.forEach((arr) => {
    if (!arr) return;
    for (let i = 0; i < arr.length; i++) {
      if (arr[i] && arr[i].relative_path === relPath) {
        arr[i] = { ...arr[i], ...fields } as LegacyMediaItem;
      }
    }
  });
}

/**
 * Sort the track list by the active `#sort-field` selection. Pure copy
 * (`items.slice().sort(...)`), byte-for-byte port of the comparator inline
 * in `_search_filter.py::applyFilter()`.
 *
 * Explicit-parameter pattern: `sortBy` was `sortField.value` (DOM read) and
 * `hasCustomPlaylist` was the truthiness of the mutable `_currentPlaylistId`
 * global — both now passed in by the caller instead of read from closure.
 */
export function sortTracks(
  items: LegacyMediaItem[],
  sortBy: string,
  hasCustomPlaylist: boolean
): LegacyMediaItem[] {
  return items.slice().sort((a, b) => {
    const sa = (a.season as number) || 0;
    const sb = (b.season as number) || 0;
    const ea = (a.episode as number) || 0;
    const eb = (b.episode as number) || 0;
    if (sortBy === "custom") {
      /* In playlist context: preserve playlist order (no sort).
         In filesystem context: sort by rating desc, title asc as tiebreaker. */
      if (hasCustomPlaylist) return 0;
      const ra = a.rating || 0;
      const rb = b.rating || 0;
      if (ra !== rb) return rb - ra;
      return a.title.localeCompare(b.title);
    }
    if (sortBy === "recent") {
      /* newest first by mtime, title as tiebreaker */
      const ma = (a.mtime as number) || 0;
      const mb = (b.mtime as number) || 0;
      if (ma !== mb) return mb - ma;
      return a.title.localeCompare(b.title);
    }
    if (sortBy === "title") {
      /* Series-aware title sort: prefer season/episode when present */
      if (sa > 0 || sb > 0) {
        if (sa !== sb) return sa - sb;
        if (ea !== eb) return ea - eb;
      }
      return a.title.localeCompare(b.title) || a.relative_path.localeCompare(b.relative_path);
    }
    if (sortBy === "path") return a.relative_path.localeCompare(b.relative_path);
    /* artist sort: group by folder, then season/episode within */
    const ad = (a.artist || "").localeCompare(b.artist || "");
    if (ad !== 0) return ad;
    if (sa !== sb) return sa - sb;
    if (ea !== eb) return ea - eb;
    return a.title.localeCompare(b.title);
  });
}



