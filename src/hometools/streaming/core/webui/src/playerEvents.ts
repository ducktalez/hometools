/**
 * Core <video>/<audio> element event handlers: ended, error, pause, play.
 * Ported from `player_js/_library_tools.py`. (timeupdate/loadedmetadata stay
 * legacy for now.)
 */

import { bgAudioIsActive, getBgAudio, stopBgSync } from "./bgAudio";
import { setWasPlaying } from "./bgPlayback";
import { isCrossfading, crossfadeCleanup } from "./crossfade";
import { getProgressPath } from "./progress";

export interface PlayerEventsHooks {
  player: HTMLMediaElement;
  btnPlay: { innerHTML: string };
  icPlay: string;
  icPause: string;
  isVideoMode: boolean;
  showVidControls(): void;
  saveProgressNow(): void;
  clearProgressFor(rp: string): void;
  finishCrossfade(): void;
  playNextItem(): void;
  /** Legacy `currentStreamUrl`. */
  currentStreamUrl(): string;
  removeGoneTrack(rp: string): void;
  showToast(msg: string): void;
}

/** Within 1.5 s of the end (or duration unknown) counts as a real finish. */
export function reachedEnd(duration: number, position: number): boolean {
  return !isFinite(duration) || duration <= 0 || position >= duration - 1.5;
}

export function onEnded(h: PlayerEventsHooks): void {
  /* Spurious 'ended' (stall/network error) must not auto-advance. */
  if (!reachedEnd(h.player.duration, h.player.currentTime)) {
    h.saveProgressNow();
    h.btnPlay.innerHTML = h.icPlay;
    return;
  }
  h.clearProgressFor(getProgressPath());
  if (isCrossfading()) {
    h.finishCrossfade();
    return;
  }
  h.playNextItem();
}

/** Missing file (404 confirmed via HEAD) removes the item; else just a toast. */
export function onError(h: PlayerEventsHooks): void {
  const err = h.player.error;
  if (!err) {
    h.btnPlay.innerHTML = h.icPlay;
    return;
  }
  if (err.code === 1) return; /* ABORTED: user stop */
  const checkUrl = h.currentStreamUrl() || h.player.currentSrc || "";
  const rp = getProgressPath();
  if (err.code === 2 && checkUrl && rp) {
    fetch(checkUrl, { method: "HEAD", cache: "no-store" })
      .then((r) => {
        if (r.status === 404) {
          h.removeGoneTrack(rp);
        } else {
          h.showToast("Wiedergabe fehlgeschlagen");
          h.btnPlay.innerHTML = h.icPlay;
        }
      })
      .catch(() => {
        h.showToast("Verbindungsfehler");
        h.btnPlay.innerHTML = h.icPlay;
      });
  } else {
    h.showToast("Wiedergabe fehlgeschlagen");
    h.btnPlay.innerHTML = h.icPlay;
  }
}

export function onPause(h: PlayerEventsHooks): void {
  /* Ignore browser auto-pause in background / bg-audio takeover. */
  if (document.hidden) return;
  if (bgAudioIsActive()) return;
  setWasPlaying(false);
  if (isCrossfading()) {
    crossfadeCleanup();
    h.player.volume = 1;
  }
  const bg = getBgAudio();
  if (bg) {
    bg.pause();
    bg.muted = true;
  }
  stopBgSync();
  if (!h.player.ended) h.btnPlay.innerHTML = h.icPlay;
  h.saveProgressNow();
  if (h.isVideoMode) h.showVidControls();
}

export function onPlay(h: PlayerEventsHooks): void {
  h.btnPlay.innerHTML = h.icPause;
  if (h.isVideoMode) h.showVidControls();
}

export function initPlayerEvents(h: PlayerEventsHooks): void {
  h.player.addEventListener("ended", () => onEnded(h));
  h.player.addEventListener("error", () => onError(h));
  h.player.addEventListener("pause", () => onPause(h));
  h.player.addEventListener("play", () => onPlay(h));
}

