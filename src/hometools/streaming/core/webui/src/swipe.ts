/**
 * Touch swipe-right = back (mobile nav) — ported from
 * `player_js/_drag_drop_init.py`. Swipe state private; `inPlaylist`/
 * `currentPath` via `htState`; `goBack` via hook. Listeners live for the
 * page lifetime (installed once).
 */

import { getState } from "./stateBridge";

const SWIPE_MIN_DIST = 60; // px horizontal
const SWIPE_MAX_VERT = 80; // px vertical deviation
const SWIPE_MAX_TIME = 400; // ms

const BLOCKING_CLASSES = ["edit-modal-backdrop", "lyrics-panel", "queue-panel", "offline-library", "playlist-modal-backdrop"];

/** False if swipe starts inside range input / canvas / modal-like panel. */
export function swipeTarget(start: Element | null): boolean {
  let el: Element | null = start;
  while (el) {
    const cur: Element = el;
    if (cur.tagName === "INPUT" && (cur as HTMLInputElement).type === "range") return false;
    if (cur.tagName === "CANVAS") return false;
    if (cur.classList && BLOCKING_CLASSES.some((c) => cur.classList.contains(c))) return false;
    el = cur.parentElement;
  }
  return true;
}

/** True when the gesture counts as a swipe to the right. */
export function isBackSwipe(dx: number, dy: number, dt: number): boolean {
  if (dt > SWIPE_MAX_TIME) return false;
  if (Math.abs(dy) > SWIPE_MAX_VERT) return false;
  if (Math.abs(dx) < SWIPE_MIN_DIST) return false;
  return dx > 0;
}

export interface SwipeHooks {
  goBack(): void;
}

let _installed = false;

export function initSwipeGestures(h: SwipeHooks): void {
  if (_installed) return;
  _installed = true;
  let startX = 0;
  let startY = 0;
  let startT = 0;
  let active = false;

  document.addEventListener(
    "touchstart",
    (e: TouchEvent) => {
      if (!swipeTarget(e.target as Element | null)) return;
      if (e.touches.length !== 1) return;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      startT = Date.now();
      active = true;
    },
    { passive: true },
  );

  document.addEventListener(
    "touchend",
    (e: TouchEvent) => {
      if (!active) return;
      active = false;
      if (e.changedTouches.length !== 1) return;
      const dx = e.changedTouches[0].clientX - startX;
      const dy = e.changedTouches[0].clientY - startY;
      if (!isBackSwipe(dx, dy, Date.now() - startT)) return;
      const st = getState();
      if (st && (st.inPlaylist || st.currentPath)) h.goBack();
    },
    { passive: true },
  );
}


