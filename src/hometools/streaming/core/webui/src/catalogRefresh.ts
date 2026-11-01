/**
 * Catalog refresh decisions — ported from `player_js/_queue.py`
 * (_triggerSilentRefresh, loadInitialCatalog cache-verify, _refreshPoll,
 * refreshFolderRatings). Pure: fetch/cache/render orchestration stays legacy
 * (see streaming.instructions.md "Catalog caching").
 */

interface HasPath {
  relative_path: string;
}

/** True when `fresh` differs from `current` by count OR by any missing path. */
export function catalogChanged(current: HasPath[], fresh: HasPath[]): boolean {
  if (fresh.length !== current.length) return true;
  if (!current.length) return false;
  const freshSet: Record<string, true> = {};
  fresh.forEach((it) => {
    freshSet[it.relative_path] = true;
  });
  return current.some((it) => !freshSet[it.relative_path]);
}

/** Toast after a manual refresh: "N Titel geladen (+x neu | -x entfernt)". */
export function refreshToastMessage(newCount: number, oldCount: number): string {
  const diff = newCount - oldCount;
  let msg = newCount + " Titel geladen";
  if (diff > 0) msg += " (+" + diff + " neu)";
  else if (diff < 0) msg += " (" + diff + " entfernt)";
  return msg;
}

/** `HH:MM` (zero-padded, local time). */
export function hhmm(dt: Date): string {
  return String(dt.getHours()).padStart(2, "0") + ":" + String(dt.getMinutes()).padStart(2, "0");
}

/** Text for `#refresh-info` after a catalog refresh: "N Titel (HH:MM)". */
export function catalogRefreshInfo(count: number, dt: Date): string {
  return count + " Titel (" + hhmm(dt) + ")";
}

/** Text for `#refresh-info` after a rating refresh. */
export function ratingRefreshInfo(ratingsRead: number, changed: number, dt: Date): string {
  let s = ratingsRead + " Ratings gelesen";
  if (changed > 0) s += ", " + changed + " aktualisiert";
  return s + " (" + hhmm(dt) + ")";
}

/**
 * Patch `rating` in place (by index, new object per changed item — items are
 * treated as immutable). Returns the number of items changed.
 */
export function patchRatingsInPlace<T extends HasPath & { rating?: unknown }>(items: T[], ratings: Record<string, unknown>): number {
  let n = 0;
  for (let i = 0; i < items.length; i++) {
    const rp = items[i].relative_path;
    if (Object.prototype.hasOwnProperty.call(ratings, rp) && items[i].rating !== ratings[rp]) {
      items[i] = Object.assign({}, items[i], { rating: ratings[rp] });
      n++;
    }
  }
  return n;
}

