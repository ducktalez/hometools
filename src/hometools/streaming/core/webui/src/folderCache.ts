/**
 * Cached list of top-level library folders (move-widget quick picks).
 *
 * (`_allFoldersCache` +
 * `_getAllFolders` + `_invalidateFolderCache`). The cache var was only ever
 * touched through those two functions, so it moved along ("state moved,
 *
 * script, so mirroring it onto `window` would need every mutation site kept
 * passes its local `allItems`; the ~11 bare `_invalidateFolderCache()` call
 */

let cache: string[] | null = null;

/** Distinct first path segments, locale-sorted. Cached until invalidated. */
export function getAllFolders(allItems: CatalogItem[]): string[] {
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

