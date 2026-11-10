/**
 * Video header buttons: fullscreen + cast. Ported from `player_js/_core.py`.
 * Fullscreen targets the overlay div (iOS falls back to the video element).
 * Cast uses the standard Remote Playback API (Chromium) or the WebKit
 * AirPlay picker (iOS Safari); the button stays hidden without support.
 */

type FsEl = HTMLElement & { webkitRequestFullscreen?: () => void };
type FsVideo = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void;
  webkitShowPlaybackTargetPicker?: () => void;
  remote?: {
    watchAvailability?: (cb: (available: boolean) => void) => Promise<number>;
    prompt?: () => Promise<void>;
    addEventListener: (ev: string, cb: () => void) => void;
  };
};

export interface FullscreenHooks {
  button: HTMLElement | null;
  overlay: HTMLElement | null;
  player: HTMLVideoElement | HTMLAudioElement;
}

export function initFullscreenButton(h: FullscreenHooks): void {
  const btn = h.button;
  if (!btn) return;
  const player = h.player as FsVideo;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const target = (h.overlay || player) as FsEl;
    if (document.fullscreenEnabled && target.requestFullscreen) {
      target.requestFullscreen().catch(() => {
        /* fallback: iOS webkitEnterFullscreen on video element */
        if (player.webkitEnterFullscreen) player.webkitEnterFullscreen();
      });
    } else if (target.webkitRequestFullscreen) {
      target.webkitRequestFullscreen();
    } else if (player.webkitEnterFullscreen) {
      player.webkitEnterFullscreen(); /* iOS Safari */
    }
  });
}

export interface CastHooks {
  button: HTMLElement | null;
  player: HTMLVideoElement | HTMLAudioElement;
}

export function initCastButton(h: CastHooks): void {
  const btn = h.button;
  const player = h.player as FsVideo;
  if (!btn || !player || player.tagName !== "VIDEO") return;
  let initialised = false;

  /* Chromium: Remote Playback API */
  const remote = player.remote;
  if (remote && typeof remote.watchAvailability === "function") {
    initialised = true;
    try {
      remote
        .watchAvailability((available) => {
          btn.hidden = !available;
        })
        .catch(() => {
          /* unsupported / disabled in iframe */
        });
    } catch {
      /* ignore */
    }
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (remote && typeof remote.prompt === "function") {
        remote.prompt().catch((err) => console.warn("Cast prompt cancelled or failed:", err));
      }
    });
    try {
      remote.addEventListener("connect", () => btn.classList.add("active"));
      remote.addEventListener("disconnect", () => btn.classList.remove("active"));
    } catch {
      /* ignore */
    }
  }

  /* iOS Safari fallback: AirPlay picker */
  if (!initialised && (window as unknown as { WebKitPlaybackTargetAvailabilityEvent?: unknown }).WebKitPlaybackTargetAvailabilityEvent) {
    player.addEventListener("webkitplaybacktargetavailabilitychanged", (ev) => {
      btn.hidden = (ev as Event & { availability?: string }).availability !== "available";
    });
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (typeof player.webkitShowPlaybackTargetPicker === "function") player.webkitShowPlaybackTargetPicker();
    });
  }
  /* Neither API: button stays hidden. */
}

