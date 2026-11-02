/**
 * Background-playback intent flag + visibilitychange handler for the video
 * player. Ported from `player_js/_library_tools.py`. `wasPlaying` is set on
 * the `playing` event and cleared only by intentional user pause (browser
 * auto-pause on mobile does NOT clear it). Legacy reads/writes it through
 * `wasPlaying()` / `setWasPlaying()`.
 */

import { getBgAudio } from "./bgAudio";
import { isPipActive, exitPip } from "./pip";

export interface BgPlaybackHooks {
  player: HTMLVideoElement;
  isVideoPlayer: boolean;
  isIOS: boolean;
}

let _was = false;

export function wasPlaying(): boolean {
  return _was;
}

export function setWasPlaying(v: boolean): void {
  _was = !!v;
}

type WebkitVideo = HTMLVideoElement & { webkitPresentationMode?: string };

/** Handle one visibility transition (exported for tests). */
export function onVisibilityChange(h: BgPlaybackHooks): void {
  if (!h.isVideoPlayer) return;
  const player = h.player as WebkitVideo;
  const bg = getBgAudio();
  if (document.hidden && _was) {
    const inPip =
      document.pictureInPictureElement === player || player.webkitPresentationMode === "picture-in-picture";
    /* Desktop keeps a playing <video> running in hidden tabs; only iOS needs
       the PiP / muted bg-audio hand-off. */
    if (h.isIOS && !inPip && bg && !bg.paused) {
      bg.currentTime = player.currentTime;
      bg.muted = false;
    }
    if ("mediaSession" in navigator) navigator.mediaSession.playbackState = "playing";
  } else if (!document.hidden && _was) {
    if (isPipActive()) exitPip();
    if (bg && !bg.muted) {
      player.currentTime = bg.currentTime;
      player.play().catch(() => {});
      bg.muted = true;
    } else if (player.paused) {
      player.play().catch(() => {});
    }
  }
}

/** Wire the `playing` listener + visibilitychange handler. */
export function initBackgroundPlayback(h: BgPlaybackHooks): void {
  _was = false;
  h.player.addEventListener("playing", () => {
    _was = true;
  });
  document.addEventListener("visibilitychange", () => onVisibilityChange(h));
}

