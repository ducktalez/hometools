/**
 * Single canonical toast (bottom-center, auto-hide).
 *
 * Ported from `player_js/_core.py`. State lives on the `#ht-toast` element
 * itself (lazily created, hide timer) — nothing outside read it, so it
 * moved along with the function (same pattern as `clickGuard.ts`).
 *
 * History: this was accidentally duplicated in `_library_tools.py` /
 * `_track_render.py` during the fragment split; the later top-level
 * `function showToast(...)` silently shadowed the real one and callers'
 * custom `durationMs` was ignored. Keeping the implementation here — one
 * module, one export — makes that class of bug impossible.
 * `tests/test_js_syntax.py::test_no_duplicate_top_level_function_declarations`
 * still guards the remaining legacy script.
 */

const DEFAULT_DURATION_MS = 3500;
const FADE_MS = 300;

const TOAST_STYLE =
  "position:fixed;bottom:100px;left:50%;transform:translateX(-50%);" +
  "background:#333;color:#fff;padding:10px 20px;border-radius:8px;" +
  "z-index:9999;font-size:14px;max-width:90%;text-align:center;" +
  "transition:opacity .3s";

let hideTimer = 0;
let removeTimer = 0;

function toastEl(): HTMLElement {
  let t = document.getElementById("ht-toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "ht-toast";
    t.style.cssText = TOAST_STYLE;
    document.body.appendChild(t);
  }
  return t;
}

/** Show `msg` for `durationMs` (default 3500). Re-showing resets the timer. */
export function showToast(msg: string, durationMs?: number): void {
  try {
    const t = toastEl();
    t.textContent = msg;
    t.style.opacity = "1";
    t.style.display = "block";
    clearTimeout(hideTimer);
    clearTimeout(removeTimer);
    hideTimer = window.setTimeout(function () {
      t.style.opacity = "0";
      removeTimer = window.setTimeout(function () {
        t.style.display = "none";
      }, FADE_MS);
    }, durationMs || DEFAULT_DURATION_MS);
  } catch {
    /* never break a caller over a status message */
  }
}

