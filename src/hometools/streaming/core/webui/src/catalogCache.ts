/**
 * Client-side localStorage caches used by the legacy player script:
 * - full catalog snapshot (stale-while-revalidate, 5 min TTL)
 * - last-played position (30 day TTL)
 * - `_locallyDeletedPaths` filtering for background/silent catalog fetches
 *
 * Ported from `player_js/_core.py` — see
 * `.github/instructions/streaming.instructions.md` → "Catalog caching —
 * stale-while-revalidate" for the exact behavioral contract these functions
 * must keep (backed by `tests/test_streaming_player_ui.py::TestCatalogLocalStorageCache`).
 *
 * Pure: cache keys are derived from an explicit `apiPath` parameter — this
 * module never reads `window.API_PATH` (that identifier is a `var` scoped to
 * the still-Python-generated legacy IIFE, not a real global). `main.ts`
 * bridges these functions onto `window` under their original legacy names,
 * closing over the already-parsed `#ht-config` `apiPath`, so every existing
 * call site in `player_js/*.py` (`_saveCatalogCache(items)`,
 * `_loadCatalogCache()`, `_clearCatalogCache()`, `_saveLastPlayedLocal(rp,
 * pos)`, `_loadLastPlayedLocal()`, `_applyLocalMutations(items)`) keeps
 * working unchanged.
 */

const CATALOG_MAX_AGE_MS = 5 * 60 * 1000;
const LAST_PLAYED_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;

function keyFor(prefix: string, apiPath: string): string {
  return prefix + apiPath.replace(/\W+/g, "_");
}

export function saveCatalogCache(items: LegacyMediaItem[], apiPath: string): void {
  if (!items || !items.length) return;
  try {
    localStorage.setItem(
      keyFor("ht-catalog-", apiPath),
      JSON.stringify({ items: items, savedAt: Date.now(), count: items.length })
    );
  } catch {
    /* QuotaExceededError on large libraries or private-mode — ignore */
  }
}

export function loadCatalogCache(apiPath: string): LegacyMediaItem[] | null {
  const key = keyFor("ht-catalog-", apiPath);
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !Array.isArray(data.items) || !data.savedAt) return null;
    if (Date.now() - data.savedAt > CATALOG_MAX_AGE_MS) {
      localStorage.removeItem(key);
      return null; /* expired */
    }
    return data.items;
  } catch {
    return null;
  }
}

export function clearCatalogCache(apiPath: string): void {
  try {
    localStorage.removeItem(keyFor("ht-catalog-", apiPath));
  } catch {
    /* ignore */
  }
}

export interface LastPlayedEntry {
  path: string;
  position_seconds: number;
  folder: string;
  timestamp: number;
}

export function saveLastPlayedLocal(rp: string, pos: number, apiPath: string): void {
  if (!rp) return;
  try {
    localStorage.setItem(
      keyFor("ht-last-", apiPath),
      JSON.stringify({
        path: rp,
        position_seconds: pos,
        folder: rp.lastIndexOf("/") > 0 ? rp.substring(0, rp.lastIndexOf("/")) : "",
        timestamp: Date.now(),
      })
    );
  } catch {
    /* ignore */
  }
}

export function loadLastPlayedLocal(apiPath: string): LastPlayedEntry | null {
  try {
    const raw = localStorage.getItem(keyFor("ht-last-", apiPath));
    if (!raw) return null;
    const data = JSON.parse(raw) as LastPlayedEntry;
    if (!data || !data.path) return null;
    if (Date.now() - (data.timestamp || 0) > LAST_PLAYED_MAX_AGE_MS) return null; /* 30 days */
    return data;
  } catch {
    return null;
  }
}

/**
 * Drop items whose path was deleted client-side this session (see header
 * comment). Mutates `locallyDeletedPaths` in place — prunes any key the
 * server no longer returns (confirmed deletion, safe to stop tracking) —
 * mirroring the original function's direct mutation of the shared
 * `_locallyDeletedPaths` closure variable in `_core.py`. The caller (bridged
 * via `main.ts`) passes `window._locallyDeletedPaths`, now bridged onto
 * `window` by `_core.py` (see `legacy-globals.d.ts`) so this object
 * reference stays the single source of truth shared with the rest of the
 * still-Python-generated script.
 */
export function applyLocalMutations(
  items: LegacyMediaItem[],
  locallyDeletedPaths: Record<string, boolean>
): LegacyMediaItem[] {
  if (!items || !items.length) return items;
  const deletedKeys = Object.keys(locallyDeletedPaths);
  if (!deletedKeys.length) return items;
  let freshSet: Record<string, boolean> | null = null;
  deletedKeys.forEach((rp) => {
    if (!freshSet) {
      freshSet = {};
      items.forEach((it) => {
        (freshSet as Record<string, boolean>)[it.relative_path] = true;
      });
    }
    if (!(freshSet as Record<string, boolean>)[rp]) delete locallyDeletedPaths[rp];
  });
  return items.filter((it) => !locallyDeletedPaths[it.relative_path]);
}

