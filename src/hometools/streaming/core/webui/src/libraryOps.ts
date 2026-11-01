/**
 * Library mutations in the UI: delete (list / duplicate panel), gone-track
 * removal, move-to-folder. Ported from `player_js/_library_tools.py`
 * (_deleteTrackFromList, _deleteDuplicateFile, _removeGoneTrack,
 * moveFileToFolder). Player state via htState; `_deletePending` is private
 * here (only these functions read it); DOM/render side via hooks.
 * Optimistic marks go to `window._locallyDeletedPaths` (see catalogCache.ts).
 */

import { getState } from "./stateBridge";
import { withoutPath, isBeforeIndex } from "./catalogQuery";
import { currentFolderOf } from "./pathUtils";
import { saveRecentMoveTarget } from "./recentMoveTargets";

export interface LibraryOpsHooks {
  deleteApiPath: string;
  moveApiPath: string;
  toast(msg: string): void;
  /** Dupe map + folder cache invalidation (legacy). */
  invalidateCaches(): void;
  saveCatalogCache(items: unknown[]): void;
  applyFilter(): void;
  showFolderView(): void;
  playTrack(index: number): void;
  itemsUnder(path: string): unknown[];
  progressRelPath(): string;
  /** Play button -> paused icon. */
  showPausedIcon(): void;
  /** Re-render open dupe panel. */
  reopenDupePanel(): void;
}

let deletePending: string | null = null;

function locallyDeleted(): Record<string, boolean> {
  const w = window as unknown as { _locallyDeletedPaths?: Record<string, boolean> };
  return w._locallyDeletedPaths || (w._locallyDeletedPaths = {});
}

/** currentIndex after a delete of `filteredIdx` (before re-render). */
export function indexAfterDelete(currentIndex: number, filteredIdx: number, filteredLen: number): number {
  if (currentIndex >= 0 && filteredIdx < currentIndex) return Math.max(0, currentIndex - 1);
  if (filteredIdx === currentIndex && currentIndex >= filteredLen - 1) return Math.max(0, currentIndex - 1);
  return currentIndex;
}

function postJson(url: string, body: unknown, failMsg: string): Promise<Record<string, unknown>> {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => {
    if (!r.ok) {
      return r.json().then((d: { detail?: string }) => {
        throw new Error(d.detail || failMsg);
      });
    }
    return r.json();
  });
}

function errMsg(err: unknown): string {
  return String((err as Error)?.message || err);
}

function fadeThen(index: number, fn: () => void): void {
  const list = typeof document !== "undefined" ? document.getElementById("track-list") : null;
  const li = list ? list.querySelector('[data-index="' + index + '"]') : null;
  if (li) {
    li.classList.add("track-item--removing");
    li.addEventListener("animationend", fn, { once: true });
  } else {
    fn();
  }
}

export function deleteTrackFromList(filteredIdx: number, h: LibraryOpsHooks): void {
  const s = getState();
  if (!s) return;
  const t = s.filteredItems[filteredIdx];
  if (!t) return;
  const name = t.title || t.relative_path;
  if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
  const wasCurrentlyPlaying = filteredIdx === s.currentIndex;
  locallyDeleted()[t.relative_path] = true;
  deletePending = t.relative_path;
  postJson(h.deleteApiPath, { path: t.relative_path }, "Fehler")
    .then(() => {
      s.allItems = withoutPath(s.allItems, t.relative_path);
      h.invalidateCaches();
      h.saveCatalogCache(s.allItems);
      s.currentIndex = indexAfterDelete(s.currentIndex, filteredIdx, s.filteredItems.length);
      h.toast("Datei gel\u00f6scht: " + name);
      fadeThen(filteredIdx, () => {
        deletePending = null;
        if (s.inPlaylist) {
          const items = h.itemsUnder(s.currentPath) as typeof s.playlistItems;
          if (items.length) {
            s.playlistItems = items;
            h.applyFilter();
          } else h.showFolderView();
        } else h.showFolderView();
        if (wasCurrentlyPlaying && s.filteredItems.length > 0) {
          h.playTrack(Math.min(s.currentIndex, s.filteredItems.length - 1));
        }
      });
    })
    .catch((err) => {
      delete locallyDeleted()[t.relative_path];
      deletePending = null;
      h.toast("L\u00f6schen fehlgeschlagen: " + errMsg(err));
    });
}

export function deleteDuplicateFile(allIndex: number, h: LibraryOpsHooks): void {
  const s = getState();
  if (!s) return;
  const t = s.allItems[allIndex];
  if (!t) return;
  const name = t.title || t.relative_path;
  if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
  const playing =
    s.currentIndex >= 0 &&
    s.currentIndex < s.filteredItems.length &&
    s.filteredItems[s.currentIndex].relative_path === t.relative_path;
  const wasBefore = !playing && isBeforeIndex(s.filteredItems, t.relative_path, s.currentIndex);
  postJson(h.deleteApiPath, { path: t.relative_path }, "Fehler")
    .then(() => {
      s.allItems.splice(allIndex, 1);
      s.playlistItems = withoutPath(s.playlistItems, t.relative_path);
      h.invalidateCaches();
      h.saveCatalogCache(s.allItems);
      if (wasBefore) s.currentIndex = Math.max(0, s.currentIndex - 1);
      h.toast("Datei gel\u00f6scht: " + name);
      if (s.inPlaylist) h.applyFilter();
      h.reopenDupePanel();
      if (playing && s.filteredItems.length > 0) {
        h.playTrack(Math.min(s.currentIndex, s.filteredItems.length - 1));
      }
    })
    .catch((err) => h.toast("L\u00f6schen fehlgeschlagen: " + errMsg(err)));
}

/** Track 404'd in the player: drop from lists, no server call. */
export function removeGoneTrack(relativePath: string, h: LibraryOpsHooks): void {
  const s = getState();
  if (!s) return;
  if (deletePending === relativePath) return;
  h.toast("Datei nicht gefunden \u2014 aus der Liste entfernt");
  const wasPlaying = relativePath === h.progressRelPath();
  const wasBefore = !wasPlaying && isBeforeIndex(s.filteredItems, relativePath, s.currentIndex);
  s.allItems = withoutPath(s.allItems, relativePath);
  h.invalidateCaches();
  h.saveCatalogCache(s.allItems);
  s.playlistItems = withoutPath(s.playlistItems, relativePath);
  if (wasBefore) s.currentIndex = Math.max(0, s.currentIndex - 1);
  h.showPausedIcon();
  if (s.inPlaylist) {
    h.applyFilter();
    if (wasPlaying && s.filteredItems.length > 0) {
      h.playTrack(Math.min(s.currentIndex < 0 ? 0 : s.currentIndex, s.filteredItems.length - 1));
    } else if (s.filteredItems.length === 0) {
      h.showFolderView();
    }
  } else {
    h.showFolderView();
  }
}

export function moveFileToFolder(idx: number, targetFolder: string, h: LibraryOpsHooks): void {
  const s = getState();
  if (!s) return;
  const t = s.filteredItems[idx];
  if (!t) return;
  if (targetFolder === currentFolderOf(t)) {
    h.toast("Datei ist bereits in diesem Ordner");
    return;
  }
  locallyDeleted()[t.relative_path] = true;
  postJson(h.moveApiPath, { path: t.relative_path, target_folder: targetFolder }, "Move failed")
    .then((d) => {
      if (!d || !d.ok) return;
      saveRecentMoveTarget(targetFolder);
      const newPath = String(d.new_path);
      for (let i = 0; i < s.allItems.length; i++) {
        if (s.allItems[i].relative_path === t.relative_path) {
          s.allItems[i] = Object.assign({}, s.allItems[i], {
            relative_path: newPath,
            stream_url: String(s.allItems[i].stream_url).replace(
              encodeURIComponent(t.relative_path),
              encodeURIComponent(newPath)
            ),
            artist: targetFolder,
          });
          break;
        }
      }
      h.invalidateCaches();
      h.saveCatalogCache(s.allItems);
      h.toast("Verschoben nach " + targetFolder);
      fadeThen(idx, () => h.applyFilter());
    })
    .catch((err) => {
      delete locallyDeleted()[t.relative_path];
      h.toast("Fehler: " + ((err as Error)?.message || "Verschieben fehlgeschlagen"));
    });
}




