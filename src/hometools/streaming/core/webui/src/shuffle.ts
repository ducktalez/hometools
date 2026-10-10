/**
 * Shuffle engine: queue building + next/prev index resolution.
 *
 * Ported from `player_js/_library_tools.py` (fisherYates,
 * buildWeightedQueue, buildNormalQueue, rebuildShuffleQueue, nextIndex,
 * prevIndex). First consumer of the `htState` bridge (stateBridge.ts):
 * these read AND write shuffleQueue/shufflePos, which legacy code also
 * touches directly (_library_tools.py playTrack sync, _folder_browse.py
 * showPlaylist start pick) — explicit params can't carry writes back, so
 * the live getter/setter bridge is the right boundary here.
 *
 * Pure queue builders stay exported for tests; the three stateful entry
 * points no-op safely when the bridge is missing (bundle loads before the
 * legacy script runs).
 */

import { getState, type HtState } from "./stateBridge";

/** In-place Fisher-Yates. */
export function fisherYates(arr: number[]): number[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = arr[i];
    arr[i] = arr[j];
    arr[j] = tmp;
  }
  return arr;
}

/** Weighted queue: rating 0 = weight 1, rating 5 = weight 6. */
export function buildWeightedQueue(items: LegacyMediaItem[]): number[] {
  const pool: number[] = [];
  items.forEach((t, idx) => {
    const w = Math.max(1, Math.round((t.rating || 0) + 1));
    for (let i = 0; i < w; i++) pool.push(idx);
  });
  return fisherYates(pool);
}

/** Uniform queue over all indices. */
export function buildNormalQueue(items: LegacyMediaItem[]): number[] {
  return fisherYates(items.map((_, i) => i));
}

/** Rebuild queue for current filteredItems/shuffleMode; startIndex leads. */
export function rebuildShuffleQueue(startIndex?: number): void {
  const s = getState();
  if (!s) return;
  if (!s.shuffleMode || !s.filteredItems.length) {
    s.shuffleQueue = [];
    s.shufflePos = -1;
    return;
  }
  const rawQueue = s.shuffleMode === "weighted" ? buildWeightedQueue(s.filteredItems) : buildNormalQueue(s.filteredItems);
  s.shuffleQueue = rawQueue; /* already filteredItems indices */
  if (typeof startIndex === "number" && startIndex >= 0) {
    const pos = s.shuffleQueue.indexOf(startIndex);
    if (pos > 0) {
      s.shuffleQueue.splice(pos, 1);
      s.shuffleQueue.unshift(startIndex);
    }
  }
  s.shufflePos = 0;
}

/** Linear (non-shuffle) next index. -1 = stop. */
function linearNext(s: HtState): number {
  const ni = s.currentIndex + 1;
  if (ni >= s.filteredItems.length) return s.repeatMode === "all" ? 0 : -1;
  return ni;
}

export interface PeekedNext {
  index: number;
  /** Apply the shuffle advance. No-op if shuffleQueue was rebuilt meanwhile. */
  commit(): void;
}

const NOOP = (): void => {};

/**
 * Next index WITHOUT side effects. Crossfade peeks at start and commits
 * only on finish — an aborted crossfade (seek/pause) must not consume a
 * shuffle slot (was: skipped track).
 */
export function peekNextIndex(): PeekedNext {
  const s = getState();
  if (!s) return { index: -1, commit: NOOP };
  if (s.shuffleMode && s.shuffleQueue.length) {
    const q = s.shuffleQueue;
    const pos = (s.shufflePos + 1) % q.length;
    /* Replenish weighted queue when exhausted */
    if (pos === 0 && s.shuffleMode === "weighted") {
      const fresh = buildWeightedQueue(s.filteredItems);
      return {
        index: fresh[0],
        commit: () => {
          const st = getState();
          if (st && st.shuffleQueue === q) {
            st.shuffleQueue = fresh;
            st.shufflePos = 0;
          }
        },
      };
    }
    return {
      index: q[pos],
      commit: () => {
        const st = getState();
        if (st && st.shuffleQueue === q) st.shufflePos = pos;
      },
    };
  }
  return { index: linearNext(s), commit: NOOP };
}

/** Next index respecting shuffle/repeat (advances shuffle state). -1 = stop. */
export function nextIndex(): number {
  const p = peekNextIndex();
  p.commit();
  return p.index;
}

/** Prev index respecting shuffle/repeat. */
export function prevIndex(): number {
  const s = getState();
  if (!s) return 0;
  if (s.shuffleMode && s.shuffleQueue.length) {
    s.shufflePos = (s.shufflePos - 1 + s.shuffleQueue.length) % s.shuffleQueue.length;
    return s.shuffleQueue[s.shufflePos];
  }
  const pi = s.currentIndex - 1;
  if (pi < 0) {
    if (s.repeatMode === "all") return s.filteredItems.length - 1;
    return 0;
  }
  return pi;
}

