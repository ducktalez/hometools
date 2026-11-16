/**
 * Recently-played strip helpers.
 * Ported from `_track_render.py::loadRecentlyPlayed` (card HTML + click-folder pick).
 */

import { getState } from "./stateBridge";

export interface RecentItem {
  relative_path?: string;
  position_seconds?: number;
  progress_pct?: number;
  thumbnail_url?: string;
  title?: string;
  artist?: string;
  [key: string]: unknown;
}

/** Card HTML for the recent strip. `escHtml` + `placeholder` explicit (legacy globals). */
export function recentCardsHtml(
  items: RecentItem[],
  escHtml: (s: unknown) => string,
  placeholder: string
): string {
  return (items || [])
    .map((it) => {
      const pct = Math.min(100, Math.max(0, it.progress_pct || 0));
      const thumb = it.thumbnail_url || placeholder;
      const imgStyle = it.thumbnail_url ? "" : ' style="object-fit:contain;padding:14px;opacity:.4"';
      return (
        '<div class="recent-card" data-path="' + escHtml(it.relative_path || "") + '"' +
        ' data-pos="' + (it.position_seconds || 0) + '" title="' + escHtml(it.title || "") + '">' +
        '<div class="recent-thumb-wrap">' +
        '<img class="recent-thumb" src="' + escHtml(thumb) + '" loading="lazy"' + imgStyle + ">" +
        (pct > 2 ? '<div class="recent-progress-bar" style="width:' + pct + '%"></div>' : "") +
        "</div>" +
        '<div class="recent-title">' + escHtml(it.title || it.relative_path || "") + "</div>" +
        '<div class="recent-sub">' + escHtml(it.artist || "") + "</div>" +
        "</div>"
      );
    })
    .join("");
}

export interface RecentPlayContext {
  folder: string;
  /** Direct children of `folder`; `[found]` fallback when empty. */
  folderItems: LegacyMediaItem[];
}

/** Folder + sibling items for a recent card click. `null` when path not in `allItems`. */
export function recentPlayContext(path: string, allItems: LegacyMediaItem[]): RecentPlayContext | null {
  const found = allItems.find((it) => it.relative_path === path);
  if (!found) return null;
  const slash = path.lastIndexOf("/");
  const folder = slash >= 0 ? path.substring(0, slash) : "";
  let folderItems = folder
    ? allItems.filter(
        (it) => it.relative_path.startsWith(folder + "/") && it.relative_path.indexOf("/", folder.length + 1) < 0
      )
    : allItems.filter((it) => it.relative_path.indexOf("/") < 0);
  if (!folderItems.length) folderItems = [found];
  return { folder, folderItems };
}

export interface RecentHooks {
  /** `RECENT_API_PATH` */
  apiPath: string;
  esc(s: unknown): string;
  placeholder: string;
  player: HTMLMediaElement;
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean): void;
  playItem(item: LegacyMediaItem, idx: number): void;
}

/** Open the folder of a recent card, play it, seek to the saved position. */
export function playRecentCard(path: string, seekPos: number, h: RecentHooks): void {
  const s = getState();
  if (!s) return;
  const ctx = recentPlayContext(path, s.allItems);
  if (!ctx) return;
  const found = s.allItems.find((it) => it.relative_path === path);
  if (!found) return;
  s.currentPath = ctx.folder;
  s.inPlaylist = true;
  h.showPlaylist(ctx.folderItems, false);
  // Index AFTER showPlaylist sorted/filtered; pre-sort index would play the wrong next episode.
  let idx = s.filteredItems.findIndex((it) => it.relative_path === path);
  if (idx < 0) idx = 0;
  h.playItem(found, idx);
  if (seekPos > 2) {
    h.player.addEventListener(
      "canplay",
      () => {
        h.player.currentTime = seekPos;
      },
      { once: true },
    );
  }
}

/** Fetch + render the recent strip; hides the section when empty/failed. Never throws. */
export function loadRecentlyPlayed(h: RecentHooks): void {
  const section = document.getElementById("recent-section");
  if (!section) return;
  fetch(h.apiPath + "?limit=10")
    .then((r) => (r.ok ? r.json() : null))
    .then((d: { items?: RecentItem[] } | null) => {
      if (!d || !d.items || d.items.length === 0) {
        section.hidden = true;
        return;
      }
      const scroll = section.querySelector(".recent-scroll");
      if (!scroll) return;
      scroll.innerHTML = recentCardsHtml(d.items, h.esc, h.placeholder);
      section.hidden = false;
      scroll.querySelectorAll<HTMLElement>(".recent-card").forEach((card) => {
        card.addEventListener("click", () => {
          playRecentCard(card.dataset.path || "", parseFloat(card.dataset.pos || "") || 0, h);
        });
      });
    })
    .catch(() => {
      section.hidden = true;
    });
}
