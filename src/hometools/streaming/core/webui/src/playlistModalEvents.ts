/**
 * Add-to-playlist modal DOM events — ported from
 * `player_js/_drag_drop_init.py` ("playlist event wiring"). Installed once;
 * `playlistAddPath` via `htState`, actions via hooks.
 */

import { getState } from "./stateBridge";

export interface PlaylistModalEventHooks {
  /** `PLAYLISTS_ENABLED` */
  enabled: boolean;
  closeModal(): void;
  createAndAdd(name: string, relativePath: string): void;
}

let _installed = false;

export function initPlaylistModalEvents(h: PlaylistModalEventHooks): void {
  if (!h.enabled || _installed) return;
  _installed = true;

  const modalClose = document.getElementById("playlist-modal-close-btn");
  if (modalClose) modalClose.addEventListener("click", h.closeModal);
  const modalBackdrop = document.getElementById("playlist-modal-backdrop");
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) h.closeModal();
    });
  }
  const newBtn = document.getElementById("playlist-modal-new-btn");
  const newInput = document.getElementById("playlist-modal-new-name") as HTMLInputElement | null;
  if (newBtn && newInput) {
    newBtn.addEventListener("click", () => {
      const n = newInput.value.trim();
      if (!n) return;
      const st = getState();
      h.createAndAdd(n, st ? st.playlistAddPath : "");
      newInput.value = "";
    });
    newInput.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Enter") newBtn.click();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const mb = document.getElementById("playlist-modal-backdrop");
    if (mb && !mb.hidden) h.closeModal();
  });
}

