/**
 * Background-tab resume (audio + video). Browsers may pause media when a tab
 * gets hidden; remember whether it was running and resume on visible.
 * Ported from `player_js/_core.py`. Flag private.
 */

export interface TabResumeHooks {
  player: HTMLMediaElement;
}

let _wasPlayingBeforeHide = false;

/** Handle one visibility transition (exported for tests). */
export function onTabVisibilityChange(h: TabResumeHooks): void {
  if (document.hidden) {
    _wasPlayingBeforeHide = !h.player.paused;
  } else if (_wasPlayingBeforeHide && h.player.paused) {
    h.player.play().catch(() => {});
  }
}

/** Wire the visibilitychange listener. */
export function initTabResume(h: TabResumeHooks): void {
  _wasPlayingBeforeHide = false;
  document.addEventListener("visibilitychange", () => onTabVisibilityChange(h));
}

