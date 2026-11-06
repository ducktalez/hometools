/**
 * `playItem` orchestration. Ported from `player_js/_library_tools.py::playItem`.
 * Sequencing only: TS helpers (shuffle sync, bg audio, crossfade, progress,
 * offline URL) are called directly; legacy-owned state (currentIndex,
 * currentStreamUrl, duration, intro) and UI side effects come in via hooks.
 */

import { syncShufflePosition } from "./playbackStart";
import type { Playback } from "./playbackStart";
import { getBgAudio, stopBgSync } from "./bgAudio";
import { crossfadeCleanup } from "./crossfade";
import { setWasPlaying } from "./bgPlayback";
import { revokeOfflineUrl } from "./offlineUrl";
import { cancelProgressTimer, setProgressPath, getProgressPath } from "./progress";

export interface PlayItemTrack {
  relative_path?: string;
  stream_url?: string;
  title?: string;
  duration?: number;
  rating?: number;
}

export interface PlayItemHooks {
  player: { volume: number };
  /** Legacy-owned state. */
  setCurrentIndex(i: number): void;
  setCurrentStreamUrl(url: string): void;
  setCurrentDuration(sec: number): void;
  setCurrentIntro(t: PlayItemTrack): void;
  /** Start playback (offline blob or stream) — `_beginPlayback` with legacy hooks bound. */
  beginPlayback(p: Playback): void;
  playOfflineOrStream(url: string): Promise<Playback>;
  showNowPlaying(t: PlayItemTrack): void;
  markActive(): void;
  updateMediaSession(t: PlayItemTrack): void;
  renderPlayerRating(stars: number): void;
  updatePlayerBarActions(): void;
  refreshMetadata(t: PlayItemTrack): void;
  /** Re-open lyrics panel for `t` when enabled and currently open. */
  refreshLyricsIfOpen(t: PlayItemTrack): void;
  saveProgressNow(): void;
  saveLastPlayedLocal(relPath: string, pos: number): void;
  autoResume: boolean;
  loadAndSeekProgress(relPath: string): void;
  loadSpriteData(relPath: string): void;
  routerUpdate(): void;
}

/** Index < 0 / non-number = item not in filteredItems (e.g. from queue). */
export function playItem(t: PlayItemTrack, index: number | undefined, h: PlayItemHooks): void {
  h.setCurrentIndex(typeof index === "number" ? index : -1);
  h.setCurrentStreamUrl(t.stream_url || "");
  h.setCurrentDuration(t.duration || 0); // catalog duration: fallback until the browser knows it
  h.setCurrentIntro(t);

  syncShufflePosition();

  // Reset bg audio for the new track
  stopBgSync();
  const bg = getBgAudio();
  if (bg) {
    bg.pause();
    bg.muted = true;
    bg.removeAttribute("src");
  }
  crossfadeCleanup();
  h.player.volume = 1;
  setWasPlaying(false);
  revokeOfflineUrl();

  h.showNowPlaying(t);
  h.markActive();
  h.updateMediaSession(t);
  h.renderPlayerRating(t.rating || 0);
  h.updatePlayerBarActions();
  h.refreshMetadata(t);
  h.refreshLyricsIfOpen(t);

  // Progress: flush outgoing track, then track the new one and try to resume.
  h.saveProgressNow();
  cancelProgressTimer();
  const rp = t.relative_path || "";
  setProgressPath(rp);
  // Also persist locally so the episode restores after reload even if < 5 s played.
  h.saveLastPlayedLocal(getProgressPath(), 0);
  if (h.autoResume) h.loadAndSeekProgress(getProgressPath());

  h.loadSpriteData(rp);

  let p: Promise<Playback>;
  try {
    p = h.playOfflineOrStream(t.stream_url || "");
  } catch {
    p = Promise.reject(new Error("playOfflineOrStream failed"));
  }
  p.then(h.beginPlayback).catch(() => {
    h.beginPlayback({ url: t.stream_url || "", offline: false, fallbackUrl: t.stream_url || "" });
  });
  h.routerUpdate();
}

