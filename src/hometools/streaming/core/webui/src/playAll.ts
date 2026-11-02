/**
 * "Play all" for the current folder. Ported from `player_js/_search_filter.py`
 * (`playAllCurrent`). State via `htState`, view effects via hooks.
 */

import { getState } from "./stateBridge";
import { itemsUnder } from "./catalogQuery";

export interface PlayAllHooks {
  /** Direct files of a folder (legacy `contentsAt(path).files`). */
  filesAt(path: string): LegacyMediaItem[];
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean): void;
}

export function playAllCurrent(hooks: PlayAllHooks): void {
  const s = getState();
  if (!s) return;
  let items = itemsUnder(s.currentPath, s.allItems);
  if (!items.length) items = hooks.filesAt(s.currentPath);
  if (items.length) hooks.showPlaylist(items, true);
}

