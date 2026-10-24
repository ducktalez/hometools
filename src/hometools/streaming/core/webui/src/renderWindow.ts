/**
 * Windowed track-list rendering math + jump-to-track target.
 * Ported from `_search_filter.py` (`_appendTrackBatch`, `_ensureRenderedTo`,
 * `jumpToCurrentTrack`). Pure; DOM + state writes stay legacy.
 */

/** End (exclusive) of the next batch; `<= offset` means nothing left. */
export function batchEnd(offset: number, batchSize: number, total: number): number {
  return Math.min(offset + batchSize, total);
}

/** Display position of real index `idx` in `realIdxMap`, or -1. */
export function displayIndexOf(realIdxMap: number[], idx: number): number {
  for (let k = 0; k < realIdxMap.length; k++) {
    if (realIdxMap[k] === idx) return k;
  }
  return -1;
}

/**
 * Display index that must be rendered for real index `idx`, or -1 when no
 * extra batches are needed (nothing rendered/unknown idx/already in DOM).
 */
export function renderTargetFor(realIdxMap: number[], idx: number, batchOffset: number, total: number): number {
  if (!total || idx < 0) return -1;
  const displayIdx = displayIndexOf(realIdxMap, idx);
  if (displayIdx < 0 || displayIdx < batchOffset) return -1;
  return displayIdx;
}

export interface JumpTarget {
  folder: string;
  /** Already in the right playlist view: just scroll. */
  sameView: boolean;
}

export function jumpTarget(
  t: { relative_path?: string },
  inPlaylist: boolean,
  currentPath: string
): JumpTarget {
  const rp = t.relative_path || "";
  const slash = rp.lastIndexOf("/");
  const folder = slash >= 0 ? rp.substring(0, slash) : "";
  return { folder, sameView: inPlaylist && currentPath === folder };
}

