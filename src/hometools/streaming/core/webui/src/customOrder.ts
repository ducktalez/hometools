/**
 * Custom item order (favorites + per-folder). Ported from
 * `player_js/_library_tools.py` (`_loadFavoritesOrder`, `_folderOrderKey`,
 * `_loadFolderOrder`, `_sortFavoritesByOrder`, `_sortByFolderOrder`).
 * Pure + localStorage reads (try/catch, [] on failure). Server sync
 * (`_save*`/`_load*Async`, fetch) stays legacy.
 */
export const FAVORITES_ORDER_KEY = "ht-favorites-order";
export function folderOrderKey(folderPath: string | null | undefined): string {
  return "ht-folder-order-" + (folderPath || "__root__");
}
/** Stored order (array of relative paths) under `key`; [] when absent/invalid. */
export function loadOrder(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    const v = raw ? JSON.parse(raw) : [];
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}
/**
 * Copy of `items` sorted by position in `order`; items missing from `order`
 * go last (stable). Returns `items` itself when `order` is empty.
 */
export function sortByOrder<T extends { relative_path: string }>(items: T[], order: string[]): T[] {
  if (!order.length) return items;
  const orderMap: Record<string, number> = {};
  order.forEach((rp, i) => {
    orderMap[rp] = i;
  });
  return items.slice().sort((a, b) => {
    const ia = orderMap[a.relative_path];
    const ib = orderMap[b.relative_path];
    if (ia === undefined && ib === undefined) return 0;
    if (ia === undefined) return 1;
    if (ib === undefined) return -1;
    return ia - ib;
  });
}
