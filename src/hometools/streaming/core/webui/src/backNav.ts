/**
 * Back navigation + offline-library close. Ported from
 * `player_js/_folder_browse.py::goBack` and `_track_render.py::closeOfflineLibrary`.
 * State via htState (globalSearchActive, currentPath, inPlaylist); views via hooks.
 */

import { getState } from "./stateBridge";
import { parentPath } from "./pathUtils";

/** Virtual path of the offline ("Downloaded") view. */
export const OFFLINE_PATH = "__offline__";

export interface BackHooks {
  exitGlobalSearch(): void;
  showFolderView(): void;
  /** `contentsAt(path)` — only the folder count matters here. */
  contentsAt(path: string): { folders: unknown[] };
}

/**
 * Back: leave global search -> leave offline view -> leave playlist view when
 * the current folder has subfolders -> else go to parent folder.
 */
export function goBack(h: BackHooks): void {
  const s = getState();
  if (!s) return;
  if (s.globalSearchActive) {
    h.exitGlobalSearch();
    return;
  }
  if (s.currentPath === OFFLINE_PATH) {
    s.currentPath = "";
    h.showFolderView();
    return;
  }
  if (s.inPlaylist && h.contentsAt(s.currentPath).folders.length > 0) {
    h.showFolderView();
    return;
  }
  s.currentPath = parentPath(s.currentPath);
  h.showFolderView();
}

/** Close the offline view (no-op elsewhere). */
export function closeOfflineLibrary(h: Pick<BackHooks, "showFolderView">): void {
  const s = getState();
  if (!s || s.currentPath !== OFFLINE_PATH) return;
  s.currentPath = "";
  h.showFolderView();
}

