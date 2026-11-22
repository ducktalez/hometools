/**
 * User queue ("Warteschlange") data operations.
 *
 * (data half of addToQueue/removeFromQueue/
 * (pattern 4). Badge/buttons/panel rendering, toasts and playItem stay in
 */

import { getState } from "./stateBridge";
import { peekNextIndex } from "./shuffle";

export interface NextTarget {
  item: CatalogItem;
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
 *
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
export function queueIndexOf(queue: CatalogItem[] | null | undefined, relPath: string): number {
  if (!queue) return -1;
  for (let i = 0; i < queue.length; i++) {
    if (queue[i].relative_path === relPath) return i;
  }
  return -1;
}

/** Slim copy stored in the queue — only fields the queue panel/playback need. */
export function queueEntry(item: CatalogItem, defaultMediaType: string): CatalogItem {
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
export function queueAdd(item: CatalogItem | null | undefined, defaultMediaType: string): QueueAddResult {
  const s = getState();
  if (!s || !item || !item.relative_path) return "invalid";
  if (queueIndexOf(s.userQueue, item.relative_path) >= 0) return "duplicate";
  s.userQueue.push(queueEntry(item, defaultMediaType));
  return "added";
}

/** Remove entry at `index`; returns it, or null when out of range. */
export function queueRemoveAt(index: number): CatalogItem | null {
  const s = getState();
  if (!s || index < 0 || index >= s.userQueue.length) return null;
  return s.userQueue.splice(index, 1)[0];
}

/** Empty the queue (reassigns, like the app `_userQueue = []`). */
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

export interface QueueActionHooks {
  onChanged(): void;
  playItem(item: CatalogItem, index: number): void;
}

/** Remove entry, refresh UI via hook. */
export function removeFromQueue(index: number, h: Pick<QueueActionHooks, "onChanged">): void {
  if (!queueRemoveAt(index)) return;
  h.onChanged();
}

/** Empty queue, refresh UI via hook. */
export function clearQueueAction(h: Pick<QueueActionHooks, "onChanged">): void {
  queueClear();
  h.onChanged();
}

/** Dequeue entry and play it (index in filteredItems if present, else -1). */
export function playFromQueue(index: number, h: QueueActionHooks): void {
  const item = queueRemoveAt(index);
  if (!item) return;
  h.onChanged();
  const s = getState();
  const fi = s ? s.filteredItems : [];
  const idx = fi.findIndex((x) => x.relative_path === item.relative_path);
  if (idx >= 0) h.playItem(fi[idx], idx);
  else h.playItem(item, -1);
}
export interface AddToQueueHooks {
  ensureDom(): void;
  onChanged(): void;
  toast(msg: string): void;
  esc(s: unknown): string;
  itemNoun: string;
}
/** Add to queue with toasts: duplicate -> notice, added -> refresh + confirmation. */
export function addToQueue(item: CatalogItem | null | undefined, h: AddToQueueHooks): void {
  h.ensureDom();
  const res = queueAdd(item, h.itemNoun);
  if (res === "invalid" || !item) return;
  if (res === "duplicate") {
    h.toast("Bereits in der Warteschlange");
    return;
  }
  h.onChanged();
  h.toast("\u201e" + h.esc(item.title || "Titel") + "\u201c zur Warteschlange hinzugef\u00fcgt");
}
