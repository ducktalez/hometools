/**
 * Global-search data computation (folder matches + item matches).
 *
 * Ported from `player_js/_search_filter.py`'s `globalSearch(needle)` — split
 * the pure computation (this file) from the DOM/state-mutation half that
 * stays in `_search_filter.py` (sets `playlistItems`/`filteredItems`/
 * `inPlaylist`, calls `_enterTrackListView`/`renderSearchResults`/
 * `rebuildShuffleQueue`). Explicit-parameter pattern: `allItems`/
 * `hiddenActive`/`_effectiveThreshold` were closure reads, now params.
 * `cleanFolderName` (breadcrumb.ts) is imported directly — same bundle,
 * no window-bridge needed for an already-ported module.
 */

import { cleanFolderName } from "./breadcrumb";

export interface FolderMatch {
  path: string;
  name: string;
  displayName: string;
  depth: number;
  thumbnail_url: string;
  thumbnail_lg_url: string;
  count: number;
}

/**
 * Folder/series matches: every unique directory prefix whose *leaf* segment
 * (raw or cleaned) contains `needleLower`, with a descendant-item `count`,
 * sorted shallowest-first then by descendant count then display name.
 */
export function buildFolderMatches(
  allItems: LegacyMediaItem[],
  needleLower: string,
  hiddenActive: boolean,
  effectiveThreshold: number
): FolderMatch[] {
  const folderSeen: Record<string, boolean> = {};
  const folderMatches: FolderMatch[] = [];
  allItems.forEach((t) => {
    if (hiddenActive) {
      const r = t.rating || 0;
      if (r > 0 && r < effectiveThreshold) return;
    }
    const rp = t.relative_path || "";
    if (!rp) return;
    const parts = rp.split("/");
    parts.pop(); // drop the file segment — only directory segments are folders
    let prefix = "";
    for (let i = 0; i < parts.length; i++) {
      const seg = parts[i];
      prefix = prefix ? prefix + "/" + seg : seg;
      if (folderSeen[prefix]) continue;
      const cleaned = cleanFolderName(seg);
      if (seg.toLowerCase().indexOf(needleLower) < 0 && (cleaned || "").toLowerCase().indexOf(needleLower) < 0) {
        continue;
      }
      folderSeen[prefix] = true;
      folderMatches.push({
        path: prefix,
        name: seg,
        displayName: cleaned,
        depth: i,
        thumbnail_url: (t.thumbnail_url as string) || "",
        thumbnail_lg_url: (t.thumbnail_lg_url as string) || "",
        count: 0,
      });
    }
  });
  // Count items beneath each matched folder + favour top-level matches.
  folderMatches.forEach((fm) => {
    const p = fm.path + "/";
    let c = 0;
    for (let j = 0; j < allItems.length; j++) {
      const rp2 = allItems[j].relative_path || "";
      if (rp2.indexOf(p) === 0) c++;
    }
    fm.count = c;
  });
  folderMatches.sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth; // shallow first
    if (b.count !== a.count) return b.count - a.count; // bigger first
    return a.displayName.localeCompare(b.displayName);
  });
  return folderMatches;
}

/** Individual item matches: title/artist/relative_path contains `needleLower`. */
export function searchItems(
  allItems: LegacyMediaItem[],
  needleLower: string,
  hiddenActive: boolean,
  effectiveThreshold: number
): LegacyMediaItem[] {
  return allItems.filter((t) => {
    const r = t.rating || 0;
    if (hiddenActive && r > 0 && r < effectiveThreshold) return false;
    return (
      (t.title || "").toLowerCase().indexOf(needleLower) >= 0 ||
      (t.artist || "").toLowerCase().indexOf(needleLower) >= 0 ||
      (t.relative_path || "").toLowerCase().indexOf(needleLower) >= 0
    );
  });
}

