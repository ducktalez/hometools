/**
 * Transport controls: play/pause toggle + smart "previous". Ported from
 * `player_js/_library_tools.py` (togglePlay/handlePreviousTrack).
 */

import { getState } from "./stateBridge";
import { getBgAudio } from "./bgAudio";
import { setWasPlaying } from "./bgPlayback";
import { prevIndex } from "./shuffle";

export interface TransportHooks {
  player: HTMLMediaElement;
  btnPlay: { innerHTML: string };
  icPlay: string;
  icPause: string;
  playTrack(index: number): void;
  startBgMirror(): void;
  stopBgSync(): void;
  /** Catalog duration of the current item (seconds, 0 if unknown). */
  currentItemDuration(): number;
}

const PREV_THRESHOLD_S = 3;
const SHORT_TRACK_S = 10;

export function togglePlay(h: TransportHooks): void {
  const s = getState();
  if (s && s.currentIndex < 0 && s.filteredItems.length) {
    h.playTrack(0);
    return;
  }
  const { player, btnPlay } = h;
  const bg = getBgAudio();
  if (player.paused) {
    /* Bg audio drove playback (back from background): sync video first. */
    if (bg && !bg.muted) {
      player.currentTime = bg.currentTime;
      bg.muted = true;
    }
    player
      .play()
      .then(() => h.startBgMirror())
      .catch(() => {});
    btnPlay.innerHTML = h.icPause;
  } else {
    /* Intentional user pause. */
    setWasPlaying(false);
    player.pause();
    if (bg) {
      bg.pause();
      bg.muted = true;
    }
    h.stopBgSync();
    btnPlay.innerHTML = h.icPlay;
  }
}

/** Restart when >= 3 s in (unless track < 10 s), else go to previous. */
export function handlePreviousTrack(h: TransportHooks): void {
  const s = getState();
  const t = h.player.currentTime || 0;
  const dur = h.currentItemDuration() || 0;
  const isShort = dur > 0 && dur < SHORT_TRACK_S;
  if (t >= PREV_THRESHOLD_S && !isShort) h.playTrack(s ? s.currentIndex : 0);
  else h.playTrack(prevIndex());
}

