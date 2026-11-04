/**
 * Lazy duplicate index cache. Ported from `player_js/_library_tools.py`
 * (_buildDuplicateMap/_ensureDupeMap/_getDupeCount/_invalidateDupeMap) and the
 * `_dupeMap/_dupePaths/_dupeSafety` vars in `_track_render.py`. State private.
 */

import { buildDuplicateIndex } from "./dupeUtils";
import type { DuplicateIndex } from "./dupeUtils";

type Items = Parameters<typeof buildDuplicateIndex>[0];

let _index: DuplicateIndex | null = null;

/** Build on first use, then reuse until invalidated. */
export function ensureDupeIndex(items: Items): DuplicateIndex {
  if (!_index) _index = buildDuplicateIndex(items);
  return _index;
}

/** Current index or null if not built yet. */
export function currentDupeIndex(): DuplicateIndex | null {
  return _index;
}

/** Number of duplicate groups. */
export function dupeCount(items: Items): number {
  return Object.keys(ensureDupeIndex(items).map).length;
}

export function invalidateDupeIndex(): void {
  _index = null;
}

