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



