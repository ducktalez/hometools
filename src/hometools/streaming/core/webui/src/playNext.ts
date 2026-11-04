/**
 * Auto-advance decision chain. Ported from `player_js/_queue.py`
 * (dequeueNext/playNextItem). State via htState; side effects via hooks.
 */

import { getState } from "./stateBridge";
import { nextIndex } from "./shuffle";

export interface PlayNextHooks {
  player: { currentTime: number; play(): Promise<unknown> | void };
  playFromQueue(index: number): void;
  playTrack(index: number): void;
  setWasPlaying(v: boolean): void;
  showStopped(): void;
}

/** Play the head of the user queue; true if one was started. */
export function dequeueNext(h: Pick<PlayNextHooks, "playFromQueue">): boolean {
  const s = getState();
  if (!s || s.userQueue.length === 0) return false;
  h.playFromQueue(0);
  return true;
}

/** repeat-one -> restart; else queue -> else next index; stop at end. */
export function playNextItem(h: PlayNextHooks): void {
  const s = getState();
  if (!s) return;
  if (s.repeatMode === "one") {
    h.player.currentTime = 0;
    try {
      const p = h.player.play();
      if (p && typeof (p as Promise<unknown>).catch === "function") (p as Promise<unknown>).catch(() => {});
    } catch {
      /* ignore */
    }
    return;
  }
  if (dequeueNext(h)) return;
  if (!s.filteredItems.length) return;
  const ni = nextIndex();
  if (ni < 0) {
    h.setWasPlaying(false);
    h.showStopped();
    return;
  }
  h.playTrack(ni);
}

