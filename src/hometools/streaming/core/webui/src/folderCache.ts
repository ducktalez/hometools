/**
 * Cached list of top-level library folders (move-widget quick picks).
 *
 * Ported from `player_js/_library_tools.py` (`_allFoldersCache` +
 * `_getAllFolders` + `_invalidateFolderCache`). The cache var was only ever
 * touched through those two functions, so it moved along ("state moved,
 * not bridged" pattern, see `clickGuard.ts`).
 *
 * `allItems` stays an explicit param — it is reassigned all over the legacy
 * script, so mirroring it onto `window` would need every mutation site kept
 * in sync. `_library_tools.py` keeps a thin `_getAllFolders()` wrapper that
 * passes its local `allItems`; the ~11 bare `_invalidateFolderCache()` call
 * sites resolve straight to the bridged function.
 */

let cache: string[] | null = null;

/** Distinct first path segments, locale-sorted. Cached until invalidated. */
export function getAllFolders(allItems: LegacyMediaItem[]): string[] {
  if (cache) return cache;
  const set: Record<string, boolean> = {};
  (allItems || []).forEach((it) => {
    const sl = it.relative_path.indexOf("/");
    if (sl > 0) set[it.relative_path.substring(0, sl)] = true;
  });
  cache = Object.keys(set).sort((a, b) => a.localeCompare(b));
  return cache;
}

/** Drop the cache — call after any move/delete/catalog refresh. */
export function invalidateFolderCache(): void {
  cache = null;
}

