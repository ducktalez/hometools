/**
 * Queue panel drag & drop reorder — ported from `player_js/_queue.py`
 * (initQueueDragDrop/destroyQueueDragDrop) + `_queueDndCleanup` var from
 * `_core.py`. Drag state + cleanup handle private; move + re-render via hooks.
 */

export interface QueueDragDropHooks {
  /** `_queueMove(from, to)` */
  move(fromIdx: number, toIdx: number): void;
  /** `renderQueuePanel()` */
  render(): void;
}

const LONG_PRESS_MS = 400;
const MOVE_THRESHOLD = 8;

let _queueDndCleanup: (() => void) | null = null;

export function destroyQueueDragDrop(): void {
  if (_queueDndCleanup) {
    _queueDndCleanup();
    _queueDndCleanup = null;
  }
}

/** Target index for moving `from` to above/below item `target`. */
export function queueDropIndex(from: number, target: number, above: boolean): number {
  let to = above ? target : target + 1;
  if (from < to) to -= 1;
  return to;
}

export function initQueueDragDrop(h: QueueDragDropHooks): void {
  destroyQueueDragDrop();
  const qList = document.getElementById("queue-list");
  if (!qList) return;
  if (qList.querySelectorAll(".queue-item").length < 2) return;

  let dragItem: HTMLElement | null = null;
  let ghost: HTMLElement | null = null;
  let dropTarget: HTMLElement | null = null;
  let dropAbove = true;
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let touchStartY = 0;
  let touchStartX = 0;
  let dragActive = false;
  let mouseItem: HTMLElement | null = null;
  let mouseStartX = 0;
  let mouseStartY = 0;

  function getQueueItem(el: Element | null): HTMLElement | null {
    while (el && el !== qList) {
      if (el.classList && el.classList.contains("queue-item")) return el as HTMLElement;
      el = el.parentElement;
    }
    return null;
  }

  function createGhost(item: HTMLElement, x: number, y: number): HTMLElement {
    const g = document.createElement("div");
    g.className = "playlist-drag-ghost";
    const img = item.querySelector(".queue-item-thumb") as HTMLImageElement | null;
    const title = item.querySelector(".queue-item-title");
    if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
    g.innerHTML += "<span>" + (title ? title.textContent : "") + "</span>";
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

  function clearDropIndicator(): void {
    qList!.querySelectorAll(".drag-over-above,.drag-over-below").forEach((el) => {
      el.classList.remove("drag-over-above", "drag-over-below");
    });
    dropTarget = null;
  }

  function updateDropTarget(x: number, y: number): void {
    if (ghost) ghost.style.display = "none";
    const el = document.elementFromPoint(x, y);
    if (ghost) ghost.style.display = "";
    const target = el ? getQueueItem(el) : null;
    if (!target || target === dragItem) {
      clearDropIndicator();
      return;
    }
    const rect = target.getBoundingClientRect();
    const above = y - rect.top < rect.height / 2;
    clearDropIndicator();
    dropTarget = target;
    dropAbove = above;
    target.classList.add(above ? "drag-over-above" : "drag-over-below");
  }

  function cancelDrag(): void {
    dragActive = false;
    if (ghost) {
      ghost.remove();
      ghost = null;
    }
    clearDropIndicator();
    if (dragItem) dragItem.style.opacity = "";
    dragItem = null;
    document.body.classList.remove("playlist-dragging");
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
  }

  function finishDrag(): void {
    if (!dragActive || !dragItem || !dropTarget) {
      cancelDrag();
      return;
    }
    const fromIdx = Number(dragItem.dataset.queueIndex);
    const toIdx = queueDropIndex(fromIdx, Number(dropTarget.dataset.queueIndex), dropAbove);
    h.move(fromIdx, toIdx);
    cancelDrag();
    h.render();
  }

  function startDrag(item: HTMLElement, x: number, y: number): void {
    dragActive = true;
    dragItem = item;
    ghost = createGhost(item, x, y);
    item.style.opacity = "0.3";
    document.body.classList.add("playlist-dragging");
  }

  function onTouchStart(e: TouchEvent): void {
    const item = getQueueItem(e.target as Element);
    if (!item || (e.target as Element).closest(".queue-item-remove")) return;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    longPressTimer = setTimeout(() => {
      longPressTimer = null;
      if (navigator.vibrate) navigator.vibrate(30);
      startDrag(item, touchStartX, touchStartY);
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
    if (dragActive) {
      e.preventDefault();
      const tx = e.touches[0].clientX;
      const ty = e.touches[0].clientY;
      moveGhost(tx, ty);
      updateDropTarget(tx, ty);
    }
  }
  function onTouchEnd(): void {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    if (dragActive) finishDrag();
  }

  function onMouseDown(e: MouseEvent): void {
    if (e.button !== 0) return;
    const item = getQueueItem(e.target as Element);
    if (!item || (e.target as Element).closest(".queue-item-remove")) return;
    mouseItem = item;
    mouseStartX = e.clientX;
    mouseStartY = e.clientY;
  }
  function onMouseMove(e: MouseEvent): void {
    if (mouseItem && !dragActive) {
      const dx = Math.abs(e.clientX - mouseStartX);
      const dy = Math.abs(e.clientY - mouseStartY);
      if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
        startDrag(mouseItem, e.clientX, e.clientY);
        mouseItem = null;
      }
    }
    if (dragActive) {
      e.preventDefault();
      moveGhost(e.clientX, e.clientY);
      updateDropTarget(e.clientX, e.clientY);
    }
  }
  function onMouseUp(): void {
    mouseItem = null;
    if (dragActive) finishDrag();
  }

  qList.addEventListener("touchstart", onTouchStart, { passive: true });
  qList.addEventListener("touchmove", onTouchMove, { passive: false });
  qList.addEventListener("touchend", onTouchEnd);
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
  qList.addEventListener("mousedown", onMouseDown);

  _queueDndCleanup = () => {
    qList.removeEventListener("touchstart", onTouchStart);
    qList.removeEventListener("touchmove", onTouchMove);
    qList.removeEventListener("touchend", onTouchEnd);
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    qList.removeEventListener("mousedown", onMouseDown);
    cancelDrag();
  };
}

