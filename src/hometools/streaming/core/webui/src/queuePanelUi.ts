/**
 * Queue panel layout + resize + peek handle — ported from `player_js/_queue.py`
 * (_syncQueueBottom, _initQueueResize, _initQueuePeekHandle). Drag state is
 * private; DOM nodes, `_queueOpen`, `_queueUserHeight` and open/toggle
 * actions come in as args/hooks (state is shared with `_core.py`).
 */

/** Panel max-height from window/header/player-bar heights and optional user height. */
export function queuePanelMaxHeight(winH: number, hdrH: number, barH: number, userHeight: number | null, minH: number): number {
  let available = winH - hdrH - barH - 8; // 8px breathing room
  if (available < minH) available = minH;
  let h = userHeight ? Math.min(userHeight, available) : available;
  if (h < minH) h = minH;
  return h;
}

/** Clamp a drag-resized height into [minH, available]. */
export function clampQueueHeight(startH: number, delta: number, available: number, minH: number): number {
  const avail = available < minH ? minH : available;
  return Math.max(minH, Math.min(startH + delta, avail));
}

function barAndHeaderHeights(): { barH: number; hdrH: number } {
  const bar = document.querySelector(".player-bar") as HTMLElement | null;
  const hdr = document.querySelector("header") as HTMLElement | null;
  return { barH: bar ? bar.offsetHeight : 80, hdrH: hdr ? hdr.offsetHeight : 56 };
}

/** Position the panel above the player bar and cap its height. */
export function syncQueueBottom(panel: HTMLElement | null, userHeight: number | null, minH: number): void {
  if (!panel) return;
  const { barH, hdrH } = barAndHeaderHeights();
  panel.style.bottom = barH + "px";
  panel.style.maxHeight = queuePanelMaxHeight(window.innerHeight, hdrH, barH, userHeight, minH) + "px";
}

export interface QueueResizeOptions {
  handle: HTMLElement | null;
  panel: HTMLElement | null;
  minH: number;
  heightKey: string;
  isOpen(): boolean;
  /** Persisted height -> legacy `_queueUserHeight`. */
  setUserHeight(h: number): void;
}

function clientY(e: MouseEvent | TouchEvent): number {
  return "touches" in e && e.touches ? e.touches[0].clientY : (e as MouseEvent).clientY;
}

export function initQueueResize(o: QueueResizeOptions): void {
  const { handle, panel } = o;
  if (!handle || !panel) return;
  let dragging = false;
  let startY = 0;
  let startH = 0;

  function onPointerDown(e: MouseEvent | TouchEvent): void {
    if (!o.isOpen()) return;
    e.preventDefault();
    dragging = true;
    startY = clientY(e);
    startH = panel!.offsetHeight;
    panel!.classList.add("dragging");
    document.addEventListener("mousemove", onPointerMove, { passive: false });
    document.addEventListener("touchmove", onPointerMove, { passive: false });
    document.addEventListener("mouseup", onPointerUp);
    document.addEventListener("touchend", onPointerUp);
  }
  function onPointerMove(e: MouseEvent | TouchEvent): void {
    if (!dragging) return;
    e.preventDefault();
    const { barH, hdrH } = barAndHeaderHeights();
    const available = window.innerHeight - hdrH - barH - 8;
    panel!.style.maxHeight = clampQueueHeight(startH, startY - clientY(e), available, o.minH) + "px";
  }
  function onPointerUp(): void {
    if (!dragging) return;
    dragging = false;
    panel!.classList.remove("dragging");
    const finalH = panel!.offsetHeight;
    if (finalH >= o.minH) {
      o.setUserHeight(finalH);
      try {
        localStorage.setItem(o.heightKey, String(finalH));
      } catch {
        /* quota / private mode */
      }
    }
    document.removeEventListener("mousemove", onPointerMove);
    document.removeEventListener("touchmove", onPointerMove);
    document.removeEventListener("mouseup", onPointerUp);
    document.removeEventListener("touchend", onPointerUp);
  }

  handle.addEventListener("mousedown", onPointerDown);
  handle.addEventListener("touchstart", onPointerDown, { passive: false });
}

export interface QueuePanelHooks {
  ensureDom(): void;
  getPanel(): HTMLElement | null;
  getPeekHandle(): HTMLElement | null;
  isOpen(): boolean;
  setOpen(v: boolean): void;
  lyricsOpen(): boolean;
  closeLyrics(): void;
  sync(): void;
  render(): void;
  destroyDnd(): void;
}

export function openQueuePanel(h: QueuePanelHooks): void {
  h.ensureDom();
  const panel = h.getPanel();
  if (!panel) return;
  h.setOpen(true);
  if (h.lyricsOpen()) h.closeLyrics();
  h.sync();
  h.render();
  panel.classList.add("visible");
  h.getPeekHandle()?.classList.add("queue-active");
}

export function closeQueuePanel(h: QueuePanelHooks): void {
  h.ensureDom();
  h.setOpen(false);
  h.destroyDnd();
  h.getPanel()?.classList.remove("visible");
  h.getPeekHandle()?.classList.remove("queue-active");
}

export function toggleQueuePanel(h: QueuePanelHooks): void {
  h.ensureDom();
  if (h.isOpen()) closeQueuePanel(h);
  else openQueuePanel(h);
}

export interface QueuePeekOptions {
  handle: HTMLElement | null;
  isOpen(): boolean;
  open(): void;
  toggle(): void;
}

const PEEK_OPEN_THRESHOLD = 12; // px dragged upward before opening

/** Click toggles the queue; dragging up past the threshold opens it. */
export function initQueuePeekHandle(o: QueuePeekOptions): void {
  const handle = o.handle;
  if (!handle) return;
  let peekDragging = false;
  let peekStartY = 0;
  let openedByDrag = false;

  function onDown(e: MouseEvent | TouchEvent): void {
    peekDragging = true;
    openedByDrag = false;
    peekStartY = clientY(e);
    document.addEventListener("mousemove", onMove, { passive: false });
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("mouseup", onUp);
    document.addEventListener("touchend", onUp);
  }
  function onMove(e: MouseEvent | TouchEvent): void {
    if (!peekDragging || o.isOpen()) return;
    if (peekStartY - clientY(e) > PEEK_OPEN_THRESHOLD) {
      openedByDrag = true;
      o.open();
    }
  }
  function onUp(): void {
    peekDragging = false;
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("touchmove", onMove);
    document.removeEventListener("mouseup", onUp);
    document.removeEventListener("touchend", onUp);
  }

  handle.addEventListener("mousedown", onDown);
  handle.addEventListener("touchstart", onDown, { passive: false });
  handle.addEventListener("click", () => {
    // Drag-triggered open already happened — don't re-toggle (close) it.
    if (openedByDrag) {
      openedByDrag = false;
      return;
    }
    o.toggle();
  });
}

