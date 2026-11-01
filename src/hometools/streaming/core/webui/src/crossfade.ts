/**
 * Audio crossfade: second hidden <audio>, sine-eased volume ramp, then hand
 * over to the main player. Ported from `player_js/_library_tools.py`
 * (_xfadeCleanup/_startCrossfade/_finishCrossfade). All `_xfade*` state is
 * module-private; legacy reads only `isCrossfading()`.
 */

import { getState } from "./stateBridge";
import { resolveNext } from "./queue";
import { nextIndex } from "./shuffle";

export interface CrossfadeHooks {
  player: HTMLMediaElement;
  /** CFG.crossfadeDuration seconds. */
  durationSec: number;
  /** Persist + clear progress of the outgoing track. */
  flushOutgoingProgress(): void;
  playTrack(index: number): void;
  playFromQueue(index: number): void;
}

let _audio: HTMLAudioElement | null = null;
let _active = false;
let _timer: ReturnType<typeof setInterval> | null = null;
let _nextItem: LegacyMediaItem | null = null;
let _nextIndex = -1;
let _commit: (() => void) | null = null;

export function isCrossfading(): boolean {
  return _active;
}

/** Abort/reset; shuffle position stays untouched (commit dropped). */
export function crossfadeCleanup(): void {
  if (_timer) {
    clearInterval(_timer);
    _timer = null;
  }
  if (_audio) {
    _audio.pause();
    _audio.removeAttribute("src");
  }
  _active = false;
  _nextItem = null;
  _nextIndex = -1;
  _commit = null;
}

export function startCrossfade(h: CrossfadeHooks): void {
  if (_active) return;
  const next = resolveNext();
  if (!next || !next.item || !next.item.stream_url) return;
  _active = true;
  _nextItem = next.item;
  _nextIndex = next.index;
  _commit = next.commit;

  if (!_audio) {
    _audio = document.createElement("audio");
    _audio.style.display = "none";
    _audio.preload = "auto";
    document.body.appendChild(_audio);
  }
  const xf = _audio;
  xf.volume = 0;
  xf.src = next.item.stream_url;
  xf.load();
  xf.play().catch(() => crossfadeCleanup());

  const steps = 20;
  const interval = (h.durationSec * 1000) / steps;
  let step = 0;
  _timer = setInterval(() => {
    step++;
    const progress = Math.min(step / steps, 1);
    const ease = 0.5 - 0.5 * Math.cos(Math.PI * progress);
    h.player.volume = Math.max(0, 1 - ease);
    xf.volume = Math.min(1, ease);
    if (step >= steps) {
      if (_timer) clearInterval(_timer);
      _timer = null;
      finishCrossfade(h);
    }
  }, interval);
}

export function finishCrossfade(h: CrossfadeHooks): void {
  const s = getState();
  if (!s || !_nextItem || !_audio) {
    crossfadeCleanup();
    return;
  }
  h.flushOutgoingProgress();
  const fromQueue = _nextIndex === -1 && s.userQueue.length > 0;
  const idx = _nextIndex;
  const commit = _commit;
  _audio.pause();
  _active = false;
  _nextItem = null;

  if (fromQueue) {
    h.playFromQueue(0);
  } else {
    if (idx >= 0 && commit) commit();
    h.playTrack(idx >= 0 ? idx : nextIndex());
  }
  _nextIndex = -1;
  _commit = null;
  h.player.volume = 1;
}

