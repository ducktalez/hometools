/**
 * Shuffle / repeat buttons: mode cycling, persistence, long-press for
 * weighted shuffle. Ported from `player_js/_library_tools.py`
 * (cycleShuffle/activateWeightedShuffle/updateShuffleBtn/cycleRepeat/
 * updateRepeatBtn + init + button wiring). Long-press state is private.
 */

import { getState } from "./stateBridge";
import { nextShuffleMode, nextRepeatMode, shuffleBtnView, repeatBtnView } from "./playerControls";
import { rebuildShuffleQueue } from "./shuffle";

export interface ModeBtn {
  classList: { toggle(c: string, on: boolean): void };
  title: string;
  innerHTML: string;
  addEventListener(type: string, fn: (e: Event) => void, opts?: { passive: boolean }): void;
}

export interface ModeButtonsHooks {
  btnShuffle: ModeBtn | null;
  btnRepeat: ModeBtn | null;
  shuffleEnabled: boolean;
  repeatEnabled: boolean;
  icRepeat: string;
  icRepeatOne: string;
  showToast(msg: string): void;
}

const LONG_PRESS_MS = 600;
let _longPressed = false;
let _longPressTimer: ReturnType<typeof setTimeout> | null = null;

function ls(): Storage | null {
  try {
    return typeof localStorage !== "undefined" ? localStorage : null;
  } catch {
    return null;
  }
}

function rebuild(): void {
  const s = getState();
  rebuildShuffleQueue(s && s.currentIndex >= 0 ? s.currentIndex : 0);
}

export function updateShuffleBtn(h: ModeButtonsHooks): void {
  const s = getState();
  if (!h.btnShuffle || !s) return;
  const v = shuffleBtnView(s.shuffleMode);
  h.btnShuffle.classList.toggle("shuffle-active", v.active);
  h.btnShuffle.classList.toggle("shuffle-weighted", v.variant);
  h.btnShuffle.title = v.title;
}

export function updateRepeatBtn(h: ModeButtonsHooks): void {
  const s = getState();
  if (!h.btnRepeat || !s) return;
  const v = repeatBtnView(s.repeatMode);
  h.btnRepeat.classList.toggle("repeat-active", v.active);
  h.btnRepeat.classList.toggle("repeat-one", v.variant);
  h.btnRepeat.innerHTML = s.repeatMode === "one" ? h.icRepeatOne : h.icRepeat;
  h.btnRepeat.title = v.title;
}

/** off -> normal -> weighted -> off */
export function cycleShuffle(h: ModeButtonsHooks): void {
  const s = getState();
  if (!s) return;
  s.shuffleMode = nextShuffleMode(s.shuffleMode);
  ls()?.setItem("ht-shuffle-mode", s.shuffleMode || "");
  updateShuffleBtn(h);
  rebuild();
}

/** Long-press: jump straight to weighted shuffle. */
export function activateWeightedShuffle(h: ModeButtonsHooks): void {
  const s = getState();
  if (!s) return;
  s.shuffleMode = "weighted";
  ls()?.setItem("ht-shuffle-mode", "weighted");
  updateShuffleBtn(h);
  rebuild();
  h.showToast("Gewichteter Shuffle aktiv (nach Bewertung)");
}

/** off -> all -> one -> off */
export function cycleRepeat(h: ModeButtonsHooks): void {
  const s = getState();
  if (!s) return;
  s.repeatMode = nextRepeatMode(s.repeatMode);
  ls()?.setItem("ht-repeat-mode", s.repeatMode || "");
  updateRepeatBtn(h);
}

/** Restore persisted modes and wire button events. */
export function initModeButtons(h: ModeButtonsHooks): void {
  const s = getState();
  if (!s) return;
  if (h.shuffleEnabled) {
    const saved = ls()?.getItem("ht-shuffle-mode");
    if (saved === "normal" || saved === "weighted") s.shuffleMode = saved;
    updateShuffleBtn(h);
  }
  if (h.shuffleEnabled && h.btnShuffle) {
    const btn = h.btnShuffle;
    const startLongPress = (): void => {
      _longPressed = false;
      _longPressTimer = setTimeout(() => {
        _longPressed = true;
        activateWeightedShuffle(h);
      }, LONG_PRESS_MS);
    };
    const cancelLongPress = (): void => {
      if (_longPressTimer) clearTimeout(_longPressTimer);
      _longPressTimer = null;
    };
    btn.addEventListener("mousedown", startLongPress);
    btn.addEventListener("mouseup", cancelLongPress);
    btn.addEventListener("mouseleave", cancelLongPress);
    btn.addEventListener(
      "touchstart",
      (e) => {
        e.preventDefault();
        startLongPress();
      },
      { passive: false }
    );
    btn.addEventListener("touchend", cancelLongPress);
    btn.addEventListener("touchcancel", cancelLongPress);
    btn.addEventListener("click", () => {
      if (!_longPressed) cycleShuffle(h);
      _longPressed = false;
    });
  }
  if (h.repeatEnabled) {
    const saved = ls()?.getItem("ht-repeat-mode");
    if (saved === "all" || saved === "one") s.repeatMode = saved;
    updateRepeatBtn(h);
    if (h.btnRepeat) h.btnRepeat.addEventListener("click", () => cycleRepeat(h));
  }
}

