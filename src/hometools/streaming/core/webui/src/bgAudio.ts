/**
 * Hidden muted <audio> mirroring the video source so iOS keeps audio alive in
 * the background. Ported from `player_js/_library_tools.py`
 * (ensureBgAudio/bgAudioIsActive/startBgMirror/stopBgSync). Element + sync
 * timer are module-private; legacy reads them via `getBgAudio()`.
 */

export interface BgMirrorHooks {
  player: HTMLMediaElement;
  isVideoPlayer: boolean;
  /** Advance when the background track ends. */
  playNext(): void;
}

let _el: HTMLAudioElement | null = null;
let _timer: ReturnType<typeof setInterval> | null = null;

export function getBgAudio(): HTMLAudioElement | null {
  return _el;
}

/** Bg audio is the active (unmuted, playing) source. */
export function bgAudioIsActive(): boolean {
  return !!_el && !_el.muted && !_el.paused;
}

export function stopBgSync(): void {
  if (_timer) {
    clearInterval(_timer);
    _timer = null;
  }
}

function ensure(hooks: BgMirrorHooks): HTMLAudioElement {
  if (_el) return _el;
  const a = document.createElement("audio");
  a.style.display = "none";
  a.preload = "auto";
  (a as HTMLAudioElement & { playsInline: boolean }).playsInline = true;
  a.muted = true;
  document.body.appendChild(a);
  a.addEventListener("ended", () => hooks.playNext());
  _el = a;
  return a;
}

/** Start the muted mirror and keep it within ~0.5s of the video. */
export function startBgMirror(hooks: BgMirrorHooks): void {
  if (!hooks.isVideoPlayer) return;
  const bg = ensure(hooks);
  const player = hooks.player;
  if (bg.src !== player.src) bg.src = player.src;
  bg.currentTime = player.currentTime;
  bg.muted = true;
  bg.play().catch(() => {});
  stopBgSync();
  _timer = setInterval(() => {
    if (!_el || !_el.muted) return;
    if (!player.paused && Math.abs(_el.currentTime - player.currentTime) > 0.5) {
      _el.currentTime = player.currentTime;
    }
  }, 2000);
}

