/**
 * Skip-intro button UI. Ported from `player_js/_core.py`
 * (`_setCurrentIntro`, `_updateSkipIntroBtn`, `_saveIntroMarker`, button
 * click/long-press wiring). Intro state (`_introStart` etc.) is
 * module-private; legacy calls `setCurrentIntro` / `updateSkipIntroBtn`
 * via window bridge. Pure decisions live in `intro.ts`.
 */

import { parseIntro, introButtonMode, patchIntroLocal } from "./intro";
import { getState } from "./stateBridge";

export interface IntroUiHooks {
  player: HTMLMediaElement;
  /** Null when the page has no skip-intro button. */
  button: HTMLElement | null;
  enabled: boolean;
  isVideoMode: boolean;
  apiPath: string;
  getProgressPath(): string;
  fmtTime(sec: number): string;
  toast(msg: string): void;
}

const LONG_PRESS_MS = 650;

let _h: IntroUiHooks | null = null;
let _start = 0;
let _end = 0;
let _isSeries = false;
let _mode: "" | "skip" | "set" = "";
let _timer: ReturnType<typeof setTimeout> | null = null;
let _longPressed = false;

function hide(): void {
  if (_h && _h.button) _h.button.hidden = true;
  _mode = "";
}

/** Reset intro state from an item; hides the button. */
export function setCurrentIntro(t: LegacyMediaItem | null | undefined): void {
  const info = parseIntro(t);
  _start = info.start;
  _end = info.end;
  _isSeries = info.isSeries;
  if (_h && _h.button) hide();
}

/** Show/hide/relabel the button for the current playback position. */
export function updateSkipIntroBtn(): void {
  const h = _h;
  if (!h || !h.enabled || !h.button || !h.isVideoMode) return;
  const cur = h.player.currentTime || 0;
  const dur = isFinite(h.player.duration) ? h.player.duration : 0;
  const mode = introButtonMode(cur, dur, _start, _end, _isSeries);
  if (mode) {
    if (_mode !== mode) {
      _mode = mode;
      const label = h.button.querySelector("span");
      h.button.classList.toggle("set-mode", mode === "set");
      if (label) label.textContent = mode === "skip" ? "Intro überspringen" : "Intro-Ende setzen";
      h.button.hidden = false;
    }
    return;
  }
  if (!h.button.hidden) hide();
}

function saveIntroMarker(start: number, end: number): void {
  const h = _h;
  if (!h) return;
  const relPath = h.getProgressPath() || "";
  if (!relPath) return;
  _start = Math.max(0, start || 0);
  _end = Math.max(0, end || 0);
  const st = getState();
  if (st) patchIntroLocal([st.allItems, st.filteredItems], relPath, _start, _end);
  try {
    fetch(h.apiPath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: relPath, start: _start, end: _end }),
    }).catch(() => {});
  } catch {
    /* ignore */
  }
}

function roundedPos(h: IntroUiHooks): number {
  return Math.round((h.player.currentTime || 0) * 10) / 10;
}

function cancelLongPress(): void {
  if (_timer) {
    clearTimeout(_timer);
    _timer = null;
  }
}

/** Wire button events. No-op when disabled or button missing. */
export function initIntroUi(h: IntroUiHooks): void {
  _h = h;
  _start = 0;
  _end = 0;
  _isSeries = false;
  _mode = "";
  _longPressed = false;
  cancelLongPress();
  const btn = h.button;
  if (!h.enabled || !btn) return;

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (_longPressed) {
      _longPressed = false;
      return;
    }
    if (_mode === "skip") {
      try {
        h.player.currentTime = _end;
      } catch {
        /* ignore */
      }
      h.toast("Intro übersprungen");
    } else if (_mode === "set") {
      const pos = roundedPos(h);
      saveIntroMarker(0, pos);
      hide();
      h.toast("Intro-Ende gesetzt bei " + h.fmtTime(pos));
    }
  });
  /* Long-press in skip mode → recalibrate intro end to current position. */
  btn.addEventListener("pointerdown", () => {
    if (_mode !== "skip") return;
    _longPressed = false;
    _timer = setTimeout(() => {
      _longPressed = true;
      const pos = roundedPos(h);
      saveIntroMarker(_start, pos);
      h.toast("Intro-Ende neu gesetzt bei " + h.fmtTime(pos));
    }, LONG_PRESS_MS);
  });
  btn.addEventListener("pointerup", cancelLongPress);
  btn.addEventListener("pointercancel", cancelLongPress);
  btn.addEventListener("pointerleave", cancelLongPress);
}

