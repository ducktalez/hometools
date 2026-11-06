/**
 * Custom item order (favorites + per-folder). Ported from
 * `player_js/_library_tools.py` (`_loadFavoritesOrder`, `_folderOrderKey`,
 * `_loadFolderOrder`, `_sortFavoritesByOrder`, `_sortByFolderOrder`).
 * Pure + localStorage reads (try/catch, [] on failure). Server sync (`saveOrder`/`loadOrderAsync`, fetch) included.
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
/**
 * Persist order: localStorage (quota errors ignored) + fire-and-forget PUT.
 * `serverKey` = `__favorites__` | folder path | `__root__`.
 */
export function saveOrder(apiPath: string, storageKey: string, serverKey: string, paths: string[]): void {
  try {
    localStorage.setItem(storageKey, JSON.stringify(paths));
  } catch {
    /* quota exceeded - ignore */
  }
  try {
    fetch(apiPath, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: serverKey, items: paths }),
    }).catch(() => {});
  } catch {
    /* ignore */
  }
}
/**
 * Server order first (cached to localStorage when non-empty); else/failure
 * -> localStorage via `loadOrder`. `cb` is called exactly once.
 */
export function loadOrderAsync(apiPath: string, storageKey: string, serverKey: string, cb: (items: string[]) => void): void {
  const fallback = () => cb(loadOrder(storageKey));
  let p: Promise<Response>;
  try {
    p = fetch(apiPath + "?path=" + encodeURIComponent(serverKey));
  } catch {
    fallback();
    return;
  }
  p.then((r) => r.json())
    .then(
      (d: { items?: string[] }) => d.items || [],
      () => [] as string[],
    )
    .then((items) => {
      if (!items.length) {
        fallback();
        return;
      }
      try {
        localStorage.setItem(storageKey, JSON.stringify(items));
      } catch {
        /* ignore */
      }
      try {
        cb(items);
      } catch (e) {
        console.error("loadOrderAsync callback failed", e); // never re-run fallback
      }
    });
}