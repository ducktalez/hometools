/**
 * Click-distance guard: suppress click handlers when pointer moved (drag).
 *
 * (`_mdX`/`_mdY`/`CLICK_MOVE_THRESHOLD` +
 * the two capture-phase listeners + `wasDrag`). Whole unit moved, not just
 *
 * still long before any user input, no behavior change.
 */

const CLICK_MOVE_THRESHOLD = 6; /* px */

let mdX = 0;
let mdY = 0;
let cleanup: (() => void) | null = null;

function onMouseDown(e: MouseEvent): void {
  mdX = e.clientX;
  mdY = e.clientY;
}

function onTouchStart(e: TouchEvent): void {
  if (e.touches.length === 1) {
    mdX = e.touches[0].clientX;
    mdY = e.touches[0].clientY;
  }
}

/** Register the capture-phase pointer listeners. Idempotent. */
export function installClickGuard(): void {
  uninstallClickGuard();
  document.addEventListener("mousedown", onMouseDown, true);
  document.addEventListener("touchstart", onTouchStart, { passive: true, capture: true });
  cleanup = function () {
    document.removeEventListener("mousedown", onMouseDown, true);
    document.removeEventListener("touchstart", onTouchStart, { capture: true });
  };
}

/** Remove the listeners (see copilot-instructions rule 14 — named handlers, explicit destroy). */
export function uninstallClickGuard(): void {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
}

/** True when the pointer moved more than the threshold since press = drag, not click. */
export function wasDrag(e: { clientX: number; clientY: number }): boolean {
  const dx = Math.abs(e.clientX - mdX);
  const dy = Math.abs(e.clientY - mdY);
  return dx > CLICK_MOVE_THRESHOLD || dy > CLICK_MOVE_THRESHOLD;
}

