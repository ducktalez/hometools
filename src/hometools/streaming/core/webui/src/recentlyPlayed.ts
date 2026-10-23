/**
 * Recently-played strip helpers.
 * Ported from `_track_render.py::loadRecentlyPlayed` (card HTML + click-folder pick).
 */

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

