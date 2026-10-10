/**
 * User queue ("Warteschlange") data operations.
 *
 * Ported from `player_js/_core.py` (data half of addToQueue/removeFromQueue/
 * clearQueue/playFromQueue). `_userQueue` is read in several fragments and
 * reassigned by clearQueue, so access goes through the htState bridge
 * (pattern 4). Badge/buttons/panel rendering, toasts and playItem stay in
 * the legacy script — these functions only mutate the queue and report back.
 */

import { getState } from "./stateBridge";
import { peekNextIndex } from "./shuffle";

export interface NextTarget {
  item: LegacyMediaItem;
  /** filteredItems index; -1 when the item comes from the user queue. */
  index: number;
  fromQueue: boolean;
  /** Apply deferred shuffle advance — call only once the transition happens. */
  commit(): void;
}

/**
 * What plays next: head of the user queue first (not consumed), else
 * filteredItems[peekNextIndex()]. null = nothing. Side-effect free —
 * caller commits (crossfade: in _finishCrossfade, so an aborted crossfade
 * doesn't skip a shuffle track).
 *
 * Ported from `_library_tools.py::_resolveNextForCrossfade`.
 */
export function resolveNext(): NextTarget | null {
  const s = getState();
  if (!s) return null;
  if (s.userQueue.length > 0) {
    return { item: s.userQueue[0], index: -1, fromQueue: true, commit: () => {} };
  }
  if (!s.filteredItems.length) return null;
  const p = peekNextIndex();
  if (p.index < 0 || p.index >= s.filteredItems.length) return null;
  return { item: s.filteredItems[p.index], index: p.index, fromQueue: false, commit: p.commit };
}

export type QueueAddResult = "added" | "duplicate" | "invalid";

/** Index of `relPath` in `queue`, -1 if absent. */
export function queueIndexOf(queue: LegacyMediaItem[] | null | undefined, relPath: string): number {
  if (!queue) return -1;
  for (let i = 0; i < queue.length; i++) {
    if (queue[i].relative_path === relPath) return i;
  }
  return -1;
}

/** Slim copy stored in the queue — only fields the queue panel/playback need. */
export function queueEntry(item: LegacyMediaItem, defaultMediaType: string): LegacyMediaItem {
  return {
    title: item.title || "",
    artist: item.artist || "",
    stream_url: item.stream_url || "",
    relative_path: item.relative_path || "",
    thumbnail_url: item.thumbnail_url || "",
    thumbnail_lg_url: item.thumbnail_lg_url || "",
    rating: item.rating || 0,
    media_type: item.media_type || defaultMediaType,
  };
}

/** Append `item` unless invalid or already queued. */
export function queueAdd(item: LegacyMediaItem | null | undefined, defaultMediaType: string): QueueAddResult {
  const s = getState();
  if (!s || !item || !item.relative_path) return "invalid";
  if (queueIndexOf(s.userQueue, item.relative_path) >= 0) return "duplicate";
  s.userQueue.push(queueEntry(item, defaultMediaType));
  return "added";
}

/** Remove entry at `index`; returns it, or null when out of range. */
export function queueRemoveAt(index: number): LegacyMediaItem | null {
  const s = getState();
  if (!s || index < 0 || index >= s.userQueue.length) return null;
  return s.userQueue.splice(index, 1)[0];
}

/** Empty the queue (reassigns, like the legacy `_userQueue = []`). */
export function queueClear(): void {
  const s = getState();
  if (s) s.userQueue = [];
}

/**
 * Move entry `fromIdx` to `toIdx` (final position, already adjusted by the
 * drag-drop caller). No-op on same index / out of range. In place.
 */
export function queueMove(fromIdx: number, toIdx: number): void {
  const s = getState();
  if (!s) return;
  const q = s.userQueue;
  if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0 || fromIdx >= q.length) return;
  const moved = q.splice(fromIdx, 1)[0];
  q.splice(Math.min(toIdx, q.length), 0, moved);
}




