/**
 * Picture-in-Picture for the video player. Ported from
 * `player_js/_library_tools.py` (requestPiP/exitPiP + PiP wiring).
 * `_active` is module-private; legacy reads `isPipActive()` / calls `exitPip()`.
 */

export interface PipHooks {
  player: HTMLVideoElement;
  /** Null when the page has no PiP button. */
  button: HTMLElement | null;
  isVideoPlayer: boolean;
  isIOS: boolean;
  /** Legacy `wasPlaying` flag: resume inline after leaving PiP. */
  wasPlaying(): boolean;
}

type WebkitVideo = HTMLVideoElement & {
  webkitSupportsPresentationMode?: (mode: string) => boolean;
  webkitSetPresentationMode?: (mode: string) => void;
};

let _active = false;
let _supported = false;
let _player: WebkitVideo | null = null;
let _button: HTMLElement | null = null;

export function isPipActive(): boolean {
  return _active;
}

function setActive(v: boolean): void {
  _active = v;
  if (_button) _button.classList.toggle("active", v);
}

export function requestPip(): Promise<void> {
  const p = _player;
  if (!p || !_supported || _active) return Promise.resolve();
  try {
    if (p.requestPictureInPicture) {
      return p
        .requestPictureInPicture()
        .then(() => setActive(true))
        .catch(() => {});
    }
    if (p.webkitSetPresentationMode) {
      p.webkitSetPresentationMode("picture-in-picture");
      setActive(true);
    }
  } catch {
    /* ignore */
  }
  return Promise.resolve();
}

export function exitPip(): void {
  const p = _player;
  if (!p || !_active) return;
  try {
    if (document.exitPictureInPicture && document.pictureInPictureElement) {
      document.exitPictureInPicture().catch(() => {});
    } else if (p.webkitSetPresentationMode) {
      p.webkitSetPresentationMode("inline");
    }
  } catch {
    /* ignore */
  }
  setActive(false);
}

/** Detect support, show button, wire native PiP events + click toggle. */
export function initPip(hooks: PipHooks): void {
  const p = hooks.player as WebkitVideo;
  _player = p;
  _button = hooks.button;
  _active = false;
  _supported =
    hooks.isVideoPlayer &&
    !!(
      document.pictureInPictureEnabled ||
      (typeof p.webkitSupportsPresentationMode === "function" &&
        p.webkitSupportsPresentationMode("picture-in-picture"))
    );
  /* Touch devices: native controls + autopictureinpicture, no custom button. */
  const isTouch =
    hooks.isIOS ||
    (navigator.maxTouchPoints > 0 &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(pointer: coarse)").matches);
  if (_supported && _button && !isTouch) _button.hidden = false;

  if (hooks.isVideoPlayer) {
    p.setAttribute("autopictureinpicture", "");
    p.addEventListener("enterpictureinpicture", () => setActive(true));
    p.addEventListener("leavepictureinpicture", () => {
      setActive(false);
      if (hooks.wasPlaying() && !document.hidden) p.play().catch(() => {});
    });
  }
  if (_button) {
    _button.addEventListener("click", () => {
      if (_active) exitPip();
      else void requestPip();
    });
  }
}

