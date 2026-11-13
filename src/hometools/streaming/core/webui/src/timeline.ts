/**
 * Player timeline: timeupdate/loadedmetadata UI, tap/drag seek on the whole
 * progress track, background-audio UI sync, progress flush on hide/unload.
 * Ported from `player_js/_library_tools.py`. Item duration (catalog fallback)
 * is shared with legacy -> get/set hooks.
 */

import { getBgAudio } from "./bgAudio";
import { drawWaveform } from "./waveform";
import { isCrossfading } from "./crossfade";
import { cancelProgressTimer } from "./progress";
import { getState } from "./stateBridge";

export interface TimelineHooks {
  player: HTMLMediaElement;
  progressBar: HTMLInputElement;
  timeCur: HTMLElement;
  timeDur: HTMLElement;
  track: HTMLElement | null;
  isVideoPlayer: boolean;
  crossfadeDuration: number;
  fmtTime(s: number): string;
  getItemDuration(): number;
  setItemDuration(d: number): void;
  saveProgressNow(): void;
  saveProgressDebounced(): void;
  updateSkipIntroBtn(): void;
  startCrossfade(): void;
}

/** Duration used for seeking: bg audio when hidden, else player, else catalog. */
export function effectiveDuration(h: Pick<TimelineHooks, "player" | "getItemDuration">): number {
  const bg = getBgAudio();
  if (bg && !bg.muted && document.hidden && isFinite(bg.duration)) return bg.duration;
  if (isFinite(h.player.duration)) return h.player.duration;
  return h.getItemDuration() || 0;
}

/** Fraction of track width -> clamped 0..1. */
export function seekFraction(clientX: number, left: number, width: number): number {
  return Math.max(0, Math.min(1, (clientX - left) / width));
}

function onTimeUpdate(h: TimelineHooks): void {
  const p = h.player;
  const itemDur = h.getItemDuration();
  const dur = isFinite(p.duration) ? p.duration : itemDur;
  if (!dur) return;
  h.progressBar.max = String(dur);
  h.progressBar.value = String(p.currentTime);
  h.timeCur.textContent = h.fmtTime(p.currentTime);
  if (isFinite(p.duration)) drawWaveform(p.currentTime / p.duration);
  else if (itemDur) drawWaveform(p.currentTime / itemDur);
  h.saveProgressDebounced();
  h.updateSkipIntroBtn();
  /* Crossfade near end; skip for video and repeat-one. */
  const s = getState();
  if (h.crossfadeDuration > 0 && !isCrossfading() && !h.isVideoPlayer && !(s && s.repeatMode === "one")) {
    const remaining = p.duration - p.currentTime;
    if (remaining > 0 && remaining <= h.crossfadeDuration && p.duration > h.crossfadeDuration + 5) {
      h.startCrossfade();
    }
  }
}

function initTrackSeek(h: TimelineHooks): void {
  const track = h.track;
  if (!track) return;
  let seeking = false;
  function seekToClientX(clientX: number): void {
    const d = effectiveDuration(h);
    if (!d) return;
    const rect = track!.getBoundingClientRect();
    if (!rect.width) return;
    const frac = seekFraction(clientX, rect.left, rect.width);
    const t = frac * d;
    try {
      h.player.currentTime = t;
    } catch {
      /* not seekable yet */
    }
    const bg = getBgAudio();
    if (bg) {
      try {
        bg.currentTime = t;
      } catch {
        /* ignore */
      }
    }
    h.progressBar.max = String(d);
    h.progressBar.value = String(t);
    h.timeCur.textContent = h.fmtTime(t);
    drawWaveform(frac);
  }
  track.addEventListener("pointerdown", (e) => {
    if (e.button != null && e.button !== 0) return;
    seeking = true;
    try {
      track.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    seekToClientX(e.clientX);
    e.preventDefault();
  });
  track.addEventListener("pointermove", (e) => {
    if (!seeking) return;
    seekToClientX(e.clientX);
    e.preventDefault();
  });
  const endSeek = (e: PointerEvent): void => {
    if (!seeking) return;
    seeking = false;
    try {
      track.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    h.saveProgressNow();
  };
  track.addEventListener("pointerup", endSeek);
  track.addEventListener("pointercancel", endSeek);
}

/** Keep bar/time/waveform in sync while bg audio plays in a hidden tab. */
export function syncFromBgAudio(h: Pick<TimelineHooks, "progressBar" | "timeCur" | "fmtTime">): void {
  const bg = getBgAudio();
  if (!bg || bg.muted || !document.hidden || !isFinite(bg.duration)) return;
  h.progressBar.max = String(bg.duration);
  h.progressBar.value = String(bg.currentTime);
  h.timeCur.textContent = h.fmtTime(bg.currentTime);
  drawWaveform(bg.currentTime / bg.duration);
}

export function initTimeline(h: TimelineHooks): void {
  const p = h.player;
  p.addEventListener("timeupdate", () => onTimeUpdate(h));
  p.addEventListener("loadedmetadata", () => {
    if (isFinite(p.duration)) h.setItemDuration(p.duration);
    const d = isFinite(p.duration) ? p.duration : h.getItemDuration();
    h.timeDur.textContent = h.fmtTime(d);
    h.progressBar.max = String(d);
  });
  h.progressBar.addEventListener("input", () => {
    p.currentTime = Number(h.progressBar.value);
  });
  initTrackSeek(h);

  /* Flush progress on hide/unload (5s debounce would be lost on mobile). */
  const flush = (): void => {
    cancelProgressTimer();
    h.saveProgressNow();
  };
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) flush();
  });
  window.addEventListener("pagehide", flush);

  if (h.isVideoPlayer) setInterval(() => syncFromBgAudio(h), 1000);
}

