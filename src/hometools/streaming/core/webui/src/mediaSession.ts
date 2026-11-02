/**
 * Media Session API (lock-screen controls) + active-media selection. Ported
 * from `player_js/_library_tools.py` (updateMediaSession/activeMedia).
 */

import { getBgAudio, bgAudioIsActive } from "./bgAudio";
import { setWasPlaying } from "./bgPlayback";

export interface MediaSessionHooks {
  player: HTMLMediaElement;
  /** `ITEM_NOUN` ("video" | "audio"). */
  itemNoun: string;
  previousTrack(): void;
  nextTrack(): void;
}

/** Element currently driving playback (bg audio when unmuted+playing). */
export function activeMedia(player: HTMLMediaElement): HTMLMediaElement {
  return bgAudioIsActive() ? (getBgAudio() as HTMLMediaElement) : player;
}

export function updateMediaSession(
  t: { title?: string; artist?: string },
  hooks: MediaSessionHooks
): void {
  if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
  const ms = navigator.mediaSession;
  ms.metadata = new MediaMetadata({
    title: t.title,
    artist: t.artist || "",
    album: hooks.itemNoun === "video" ? "hometools video" : "hometools audio",
    artwork: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  });
  ms.setActionHandler("play", () => {
    void activeMedia(hooks.player).play();
    setWasPlaying(true);
  });
  ms.setActionHandler("pause", () => {
    /* Lockscreen pause = intentional user pause */
    setWasPlaying(false);
    activeMedia(hooks.player).pause();
    const bg = getBgAudio();
    if (bg) {
      bg.pause();
      bg.muted = true;
    }
  });
  ms.setActionHandler("previoustrack", () => hooks.previousTrack());
  ms.setActionHandler("nexttrack", () => hooks.nextTrack());
  try {
    ms.setActionHandler("seekto", (d) => {
      if (typeof d.seekTime === "number") activeMedia(hooks.player).currentTime = d.seekTime;
    });
  } catch {
    /* unsupported action */
  }
}

