/**
 * Playlist drag & drop reorder — ported from `player_js/_drag_drop_init.py`
 * (initPlaylistDragDrop) + `_smart_playlists.py` (_dndCleanup/destroy).
 *
 * All drag state + listeners are private to `initPlaylistDragDrop`; the
 * cleanup handle is module-private. `filteredItems` via `htState`; the
 * reorder action comes in via `DragDropHooks`.
 */

import { getState } from "./stateBridge";

export interface DragDropHooks {
  /** Legacy `reorderPlaylistItem(relativePath, toIndex)` wrapper. */
  reorder(relativePath: string, toIndex: number): void;
}

const LONG_PRESS_MS = 500;
const MOVE_THRESHOLD = 10;
const NO_DRAG_SELECTOR =
  ".track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn,.track-queue-btn,.track-inline-rating-star,.track-title-text,.track-artist";

let _dndCleanup: (() => void) | null = null;

export function destroyPlaylistDragDrop(): void {
  if (_dndCleanup) {
    _dndCleanup();
    _dndCleanup = null;
  }
}

/** Target index after removing the dragged item (`from`) and inserting at above/below `targetIdx`. */
export function dropIndex(from: number, targetIdx: number, above: boolean): number {
  let to = above ? targetIdx : targetIdx + 1;
  if (from < to) to--;
  return to;
}

export function initPlaylistDragDrop(h: DragDropHooks): void {
  destroyPlaylistDragDrop();

  const trackList = document.getElementById("track-list");
  if (!trackList) return;
  const items = trackList.querySelectorAll(".track-item:not(.missing-episode)");
  if (items.length < 2) return;

  let dragItem: HTMLElement | null = null;
  let dragPath = "";
  let dragFromIdx = -1;
  let ghost: HTMLElement | null = null;
  let dropTarget: HTMLElement | null = null;
  let dropAbove = true;
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let touchStartY = 0;
  let touchStartX = 0;
  let dragActive = false;
  let pendingDrag: { item: HTMLElement; x: number; y: number } | null = null;

  function getTrackItem(el: Element | null): HTMLElement | null {
    while (el && el !== trackList) {
      if (el.classList && el.classList.contains("track-item")) return el as HTMLElement;
      el = el.parentElement;
    }
    return null;
  }

  function createGhost(item: HTMLElement, x: number, y: number): HTMLElement {
    const g = document.createElement("div");
    g.className = "playlist-drag-ghost";
    const img = item.querySelector(".track-thumb") as HTMLImageElement | null;
    const titleEl = item.querySelector(".track-title-text") || item.querySelector(".track-title");
    if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
    g.innerHTML += "<span>" + (titleEl ? titleEl.textContent : "") + "</span>";
    g.style.left = x - 20 + "px";
    g.style.top = y - 20 + "px";
    document.body.appendChild(g);
    return g;
  }

  function moveGhost(x: number, y: number): void {
    if (!ghost) return;
    ghost.style.left = x - 20 + "px";
    ghost.style.top = y - 20 + "px";
  }

  function clearDragClasses(): void {
    trackList!.querySelectorAll(".drag-over-above,.drag-over-below,.dragging").forEach((el) => {
      el.classList.remove("drag-over-above", "drag-over-below", "dragging");
    });
  }

  function clearDropIndicator(): void {
    if (dropTarget) {
      dropTarget.classList.remove("drag-over-above", "drag-over-below");
      dropTarget = null;
    }
  }

  function updateDropTarget(x: number, y: number): void {
    if (ghost) ghost.style.display = "none";
    const el = document.elementFromPoint(x, y);
    if (ghost) ghost.style.display = "";
    let target = el ? getTrackItem(el) : null;

    if (!target) {
      if (dragItem) {
        const dragRect = dragItem.getBoundingClientRect();
        if (dragRect.height > 0 && x >= dragRect.left && x <= dragRect.right && y >= dragRect.top && y <= dragRect.bottom) {
          clearDropIndicator();
          return;
        }
      }
      const tlRect = trackList!.getBoundingClientRect();
      if (x >= tlRect.left && x <= tlRect.right && y >= tlRect.top && y <= tlRect.bottom) {
        const visibleItems = trackList!.querySelectorAll(".track-item:not(.missing-episode):not(.dragging)");
        if (visibleItems.length > 0) {
          const lastItem = visibleItems[visibleItems.length - 1] as HTMLElement;
          if (dropTarget !== lastItem) clearDropIndicator();
          dropTarget = lastItem;
          dropAbove = false;
          lastItem.classList.remove("drag-over-above");
          lastItem.classList.add("drag-over-below");
          return;
        }
      }
      clearDropIndicator();
      return;
    }

    if (target === dragItem) {
      clearDropIndicator();
      return;
    }

    const rect = target.getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    let above = y < mid;

    if (!above) {
      let nextSib = target.nextElementSibling as HTMLElement | null;
      while (
        nextSib &&
        (!nextSib.classList.contains("track-item") || nextSib.classList.contains("missing-episode") || nextSib === dragItem)
      ) {
        nextSib = nextSib.nextElementSibling as HTMLElement | null;
      }
      if (nextSib && nextSib.classList.contains("track-item")) {
        target = nextSib;
        above = true;
      }
    }

    dropAbove = above;

    if (dropIndex(dragFromIdx, Number(target.dataset.index), above) === dragFromIdx) {
      clearDropIndicator();
      return;
    }

    if (dropTarget !== target) clearDropIndicator();
    dropTarget = target;
    target.classList.toggle("drag-over-above", above);
    target.classList.toggle("drag-over-below", !above);
  }

  function startDrag(item: HTMLElement, x: number, y: number): void {
    dragActive = true;
    dragItem = item;
    dragPath = "";
    const idx = Number(item.dataset.index);
    const st = getState();
    if (st && st.filteredItems[idx]) {
      dragPath = st.filteredItems[idx].relative_path;
      dragFromIdx = idx;
    }
    item.classList.add("dragging");
    document.body.classList.add("playlist-dragging");
    ghost = createGhost(item, x, y);
  }

  function endDrag(): void {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    if (!dragActive) return;
    dragActive = false;
    if (ghost) {
      ghost.remove();
      ghost = null;
    }
    document.body.classList.remove("playlist-dragging");

    if (dropTarget && dragPath) {
      const toIndex = dropIndex(dragFromIdx, Number(dropTarget.dataset.index), dropAbove);
      if (toIndex !== dragFromIdx && toIndex >= 0) h.reorder(dragPath, toIndex);
    }
    clearDragClasses();
    dragItem = null;
    dropTarget = null;
  }

  /* --- Named handlers for proper cleanup --- */
  function onMouseDown(e: MouseEvent): void {
    if (e.button !== 0) return;
    if ((e.target as Element).closest(NO_DRAG_SELECTOR)) return;
    const item = getTrackItem(e.target as Element);
    if (!item) return;
    pendingDrag = { item, x: e.clientX, y: e.clientY };
  }
  function onMouseMove(e: MouseEvent): void {
    if (pendingDrag && !dragActive) {
      const pdx = Math.abs(e.clientX - pendingDrag.x);
      const pdy = Math.abs(e.clientY - pendingDrag.y);
      if (pdx > MOVE_THRESHOLD || pdy > MOVE_THRESHOLD) {
        startDrag(pendingDrag.item, e.clientX, e.clientY);
        pendingDrag = null;
      } else {
        return;
      }
    }
    if (!dragActive) return;
    e.preventDefault();
    moveGhost(e.clientX, e.clientY);
    updateDropTarget(e.clientX, e.clientY);
    const rect = trackList!.getBoundingClientRect();
    const scrollZone = 50;
    if (e.clientY < rect.top + scrollZone) trackList!.scrollTop -= 8;
    if (e.clientY > rect.bottom - scrollZone) trackList!.scrollTop += 8;
  }
  function onMouseUp(): void {
    pendingDrag = null;
    endDrag();
  }

  function onTouchStart(e: TouchEvent): void {
    if (e.touches.length !== 1) return;
    if ((e.target as Element).closest(NO_DRAG_SELECTOR)) return;
    const item = getTrackItem(e.target as Element);
    if (!item) return;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    longPressTimer = setTimeout(() => {
      longPressTimer = null;
      startDrag(item, touchStartX, touchStartY);
      if (navigator.vibrate) navigator.vibrate(30);
    }, LONG_PRESS_MS);
  }
  function onTouchMove(e: TouchEvent): void {
    if (longPressTimer) {
      const dx = Math.abs(e.touches[0].clientX - touchStartX);
      const dy = Math.abs(e.touches[0].clientY - touchStartY);
      if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
    }
    if (!dragActive) return;
    e.preventDefault();
    const tx = e.touches[0].clientX;
    const ty = e.touches[0].clientY;
    moveGhost(tx, ty);
    updateDropTarget(tx, ty);
    const rect = trackList!.getBoundingClientRect();
    const scrollZone = 50;
    if (ty < rect.top + scrollZone) trackList!.scrollTop -= 6;
    if (ty > rect.bottom - scrollZone) trackList!.scrollTop += 6;
  }
  function onTouchEnd(): void {
    endDrag();
  }
  function onTouchCancel(): void {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    endDrag();
  }

  /* --- Attach listeners --- */
  trackList.addEventListener("mousedown", onMouseDown);
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
  trackList.addEventListener("touchstart", onTouchStart, { passive: true });
  trackList.addEventListener("touchmove", onTouchMove, { passive: false });
  trackList.addEventListener("touchend", onTouchEnd, { passive: true });
  trackList.addEventListener("touchcancel", onTouchCancel, { passive: true });

  /* --- Cleanup --- */
  _dndCleanup = () => {
    trackList.removeEventListener("mousedown", onMouseDown);
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    trackList.removeEventListener("touchstart", onTouchStart);
    trackList.removeEventListener("touchmove", onTouchMove);
    trackList.removeEventListener("touchend", onTouchEnd);
    trackList.removeEventListener("touchcancel", onTouchCancel);
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    if (dragActive) {
      dragActive = false;
      if (ghost) {
        ghost.remove();
        ghost = null;
      }
      document.body.classList.remove("playlist-dragging");
    }
    clearDragClasses();
  };
}

