/**
 * Playback start helpers for `playItem`. Ported from
 * `player_js/_library_tools.py` (shuffle sync + beginPlayback/retry chain).
 */

import { getState } from "./stateBridge";

/** Resolved source from `playOfflineOrStream`. */
export interface Playback {
  url: string;
  offline: boolean;
  fallbackUrl: string;
}

export interface BeginPlaybackHooks {
  player: HTMLMediaElement;
  btnPlay: { innerHTML: string };
  icPause: string;
  icPlay: string;
  /** Release the offline blob URL (before falling back to the stream). */
  revokeOfflineUrl(): void;
  /** Called once play() succeeded (starts bg mirror). */
  onStarted(): void;
  generateWaveform(url: string, relPath: string): void;
}

/** Keep the shuffle queue pointing at `currentIndex` (chosen by the user). */
export function syncShufflePosition(): void {
  const s = getState();
  if (!s || !s.shuffleMode || !s.shuffleQueue.length || s.currentIndex < 0) return;
  const qpos = s.shuffleQueue.indexOf(s.currentIndex);
  if (qpos >= 0) {
    s.shufflePos = qpos;
  } else {
    s.shuffleQueue.unshift(s.currentIndex);
    s.shufflePos = 0;
  }
}

/** Load + play; offline failure falls back to stream; last resort waits for canplay. */
export function beginPlayback(playback: Playback, relPath: string, h: BeginPlaybackHooks): void {
  const { player, btnPlay } = h;
  const onSuccess = (): void => {
    btnPlay.innerHTML = h.icPause;
    h.onStarted();
  };
  const retryAfterCanPlay = (): void => {
    player.addEventListener(
      "canplay",
      () => {
        player
          .play()
          .then(onSuccess)
          .catch((e: unknown) => {
            console.error("playTrack retry also failed:", e);
            btnPlay.innerHTML = h.icPlay;
          });
      },
      { once: true }
    );
  };
  player.src = playback.url;
  player.load();
  player
    .play()
    .then(onSuccess)
    .catch((err: unknown) => {
      if (playback.offline) {
        console.warn("Offline playback failed, falling back to stream:", err);
        h.revokeOfflineUrl();
        player.src = playback.fallbackUrl;
        player.load();
        player
          .play()
          .then(onSuccess)
          .catch((fallbackErr: unknown) => {
            console.warn("Stream fallback play() failed, waiting for canplay:", fallbackErr);
            retryAfterCanPlay();
          });
        return;
      }
      console.warn("playTrack play() failed, waiting for canplay:", err);
      retryAfterCanPlay();
    });
  h.generateWaveform(playback.url, relPath);
}

