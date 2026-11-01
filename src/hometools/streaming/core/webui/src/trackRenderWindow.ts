/**
 * Windowed track-list rendering — ported from `player_js/_search_filter.py`
 * (_stopRenderObserver, _appendTrackBatch, _ensureRenderedTo, markActive) and
 * the windowing setup of `_track_render.py::renderTracks`. The window state
 * (display items, real-index map, batch offset, sentinel, observer; formerly
 * `_render*` vars in `_core.py`) is module-private. The render guard
 * (`_rgKey`), filter vars and row-context building stay legacy and come in
 * via `RenderWindowHooks`. `currentIndex` via `htState`.
 */

import { getState } from "./stateBridge";
import { batchEnd, renderTargetFor } from "./renderWindow";
import { trackRowsHtml } from "./trackRows";
import type { TrackRowCtx } from "./trackRows";
import { withMissingEpisodes } from "./episodeGaps";

export interface RenderWindowHooks {
  /** `trackList` element */
  trackList(): HTMLElement;
  /** `_RENDER_BATCH_SIZE` */
  batchSize: number;
  /** Build the per-batch row context (legacy globals, tool state, icons). */
  rowCtx(): TrackRowCtx;
  /** updateFavoriteButtons / updateAllDownloadButtons / updateQueueButtons */
  decorateRows(): void;
  /** After first/last batch: wire playlist DnD if the view warrants it. */
  maybeInitPlaylistDragDrop(): void;
  /** `_wireTrackListDelegation()` */
  wireDelegation(): void;
}

type DisplayItem = LegacyMediaItem & { _missing?: boolean; _debugReason?: string };

let _displayItems: DisplayItem[] = [];
let _realIdxMap: number[] = [];
let _batchOffset = 0;
let _sentinel: HTMLElement | null = null;
let _observer: IntersectionObserver | null = null;

/** Real-index map: display index -> filtered index (-1 for placeholder/debug rows). */
export function buildRealIdxMap(display: Array<{ _missing?: boolean; _debugReason?: string }>): number[] {
  const map: number[] = [];
  let rc = 0;
  for (const it of display) map.push(it._missing || it._debugReason ? -1 : rc++);
  return map;
}

export function stopRenderObserver(h: RenderWindowHooks): void {
  if (_observer) {
    _observer.disconnect();
    _observer = null;
  }
  const tl = h.trackList();
  if (_sentinel && _sentinel.parentNode === tl) tl.removeChild(_sentinel);
  _sentinel = null;
}

/** Append the next batch of rows to the DOM. */
export function appendTrackBatch(h: RenderWindowHooks): void {
  const end = batchEnd(_batchOffset, h.batchSize, _displayItems.length);
  if (end <= _batchOffset) {
    stopRenderObserver(h);
    return;
  }
  const html = trackRowsHtml(_displayItems, _realIdxMap, _batchOffset, end, h.rowCtx());
  const isFirstBatch = _batchOffset === 0;
  _batchOffset = end;
  const tl = h.trackList();
  if (_sentinel && _sentinel.parentNode === tl) _sentinel.insertAdjacentHTML("beforebegin", html);
  else tl.insertAdjacentHTML("beforeend", html);
  h.decorateRows();
  const done = _batchOffset >= _displayItems.length;
  if (done) stopRenderObserver(h);
  // Container-level DnD: needs to be wired on the first batch (covers later items too) or at the end.
  if (done || isFirstBatch) h.maybeInitPlaylistDragDrop();
}

/** Synchronously render batches until real index `idx` is in the DOM. */
export function ensureRenderedTo(idx: number, h: RenderWindowHooks): void {
  const displayIdx = renderTargetFor(_realIdxMap, idx, _batchOffset, _displayItems.length);
  if (displayIdx < 0) return;
  while (_batchOffset <= displayIdx && _batchOffset < _displayItems.length) {
    const prev = _batchOffset;
    appendTrackBatch(h);
    if (_batchOffset === prev) break; // safety: no progress
  }
}

/** Highlight the playing row (rendering up to it first). */
export function markActive(h: RenderWindowHooks): void {
  const st = getState();
  const cur = st ? st.currentIndex : -1;
  if (cur >= 0) ensureRenderedTo(cur, h);
  document.querySelectorAll<HTMLElement>(".track-item:not(.missing-episode):not(.debug-filtered)").forEach((el) => {
    const idx = Number(el.dataset.index);
    el.classList.toggle("active", idx === cur);
    if (idx === cur) el.scrollIntoView({ block: "nearest" });
  });
}

/**
 * Reset the window for `realTracks` (episode-gap placeholders added), insert
 * the sentinel, render the first batch and set up lazy loading.
 */
export function startWindowedRender(realTracks: LegacyMediaItem[], h: RenderWindowHooks): void {
  const tl = h.trackList();
  _displayItems = withMissingEpisodes(realTracks as Array<LegacyMediaItem & { season?: number; episode?: number }>) as DisplayItem[];
  _realIdxMap = buildRealIdxMap(_displayItems);
  _batchOffset = 0;

  // Sentinel <li> at bottom — IntersectionObserver fires appendTrackBatch.
  const s = document.createElement("li");
  s.className = "track-list-sentinel";
  s.setAttribute("aria-hidden", "true");
  s.style.cssText = "height:1px;pointer-events:none;visibility:hidden;";
  tl.appendChild(s);
  _sentinel = s;

  h.wireDelegation();
  appendTrackBatch(h);

  if (_batchOffset < _displayItems.length) {
    if (typeof IntersectionObserver !== "undefined") {
      _observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) appendTrackBatch(h);
        },
        { rootMargin: "400px" }
      );
      _observer.observe(s);
    } else {
      // Old browsers: render everything synchronously.
      while (_batchOffset < _displayItems.length) appendTrackBatch(h);
    }
  }
}

