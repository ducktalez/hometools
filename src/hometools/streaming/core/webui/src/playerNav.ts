/**
 * Player-bar navigation helpers — ported from `player_js/_search_filter.py`
 * (jumpToCurrentTrack, updatePlayerBarActions wiring). Markup/targets live in
 * `playerBarHtml.ts` / `renderWindow.ts`. Shared state (`currentIndex`,
 * `filteredItems`, `playlistItems`, `inPlaylist`, `currentPath`) via
 * `htState`; everything else via hooks.
 *
 * Behaviour fix vs. legacy: the player-bar trash button called the undefined
 * `_deleteItem(...)` (ReferenceError) after its own confirm(). It now calls
 * `deleteTrackFromList`, which asks for confirmation itself.
 */

import { getState } from "./stateBridge";
import { jumpTarget } from "./renderWindow";
import { playerBarActionsHtml } from "./playerBarHtml";
import { currentFolderOf } from "./pathUtils";

export interface JumpHooks {
  ensureRenderedTo(idx: number): void;
  markActive(): void;
  itemsUnder(path: string): LegacyMediaItem[];
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean): void;
}

/** Current track from filtered list, falling back to the playlist list. */
function currentTrack(): LegacyMediaItem | null {
  const st = getState();
  if (!st || st.currentIndex < 0) return null;
  return st.filteredItems[st.currentIndex] || st.playlistItems[st.currentIndex] || null;
}

/** Scroll to (navigating to its folder first if needed) the playing track. */
export function jumpToCurrentTrack(h: JumpHooks): void {
  const st = getState();
  const t = currentTrack();
  if (!st || !t) return;
  const savedRp = t.relative_path || "";
  const jt = jumpTarget(t, st.inPlaylist, st.currentPath);
  if (jt.sameView) {
    h.ensureRenderedTo(st.currentIndex);
    h.markActive();
    return;
  }
  st.currentPath = jt.folder;
  const items = h.itemsUnder(st.currentPath);
  if (!items.length) return;
  h.showPlaylist(items, false);
  // filteredItems was replaced by showPlaylist -> re-find the playing track.
  const newIdx = st.filteredItems.findIndex((fi) => fi.relative_path === savedRp);
  if (newIdx >= 0) {
    st.currentIndex = newIdx;
    h.ensureRenderedTo(newIdx);
    h.markActive();
  }
}

export interface PlayerBarActionsHooks {
  container(): HTMLElement | null;
  /** `_getAllFolders()` */
  allFolders(): string[];
  esc(s: unknown): string;
  icDots: string;
  icTrash: string;
  moveFileToFolder(idx: number, target: string): void;
  /** Asks for confirmation itself. */
  deleteTrackFromList(idx: number): void;
  openTrackCtxMenu(btn: HTMLElement, relativePath: string | undefined, title: string | undefined): void;
}

/** Re-render + wire the right-hand player-bar actions for the current track. */
export function updatePlayerBarActions(h: PlayerBarActionsHooks): void {
  const box = h.container();
  if (!box) return;
  const t = currentTrack();
  if (!t) {
    box.innerHTML = "";
    return;
  }
  const inMoverMode = document.body.classList.contains("tool-show-file-mover");
  box.innerHTML = playerBarActionsHtml(t, h.allFolders(), currentFolderOf(t), inMoverMode, h.esc, h.icDots, h.icTrash);
  if (inMoverMode) {
    const mvSel = box.querySelector<HTMLSelectElement>("#player-bar-move-select");
    if (mvSel) {
      mvSel.addEventListener("change", () => {
        const st = getState();
        const target = mvSel.value;
        if (!target || !st || st.currentIndex < 0) return;
        h.moveFileToFolder(st.currentIndex, target);
        mvSel.value = "";
      });
    }
    const trashBtn = box.querySelector("#player-bar-trash");
    if (trashBtn) {
      trashBtn.addEventListener("click", () => {
        const st = getState();
        if (!st || st.currentIndex < 0) return;
        h.deleteTrackFromList(st.currentIndex);
      });
    }
  }
  const kbBtn = box.querySelector<HTMLElement>("#player-bar-kebab");
  if (kbBtn) {
    kbBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      h.openTrackCtxMenu(kbBtn, kbBtn.dataset.relativePath, kbBtn.dataset.title);
    });
  }
}

