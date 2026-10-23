/**
 * Root folder-grid extras: tools row, favorites card, playlist cards.
 * Ported from `_folder_browse.py::showFolderView` (markup only).
 */

type Esc = (s: unknown) => string;

export interface ToolsRowOpts {
  isRoot: boolean;
  playlistsEnabled: boolean;
  offlineEnabled: boolean;
  isVideo: boolean;
  allItemsCount: number;
  icSmartPlaylist: string;
  icPlaylist: string;
  icDl: string;
  icRefresh: string;
}

/** `<div class="playlist-tools-row">…</div>` or "" when no buttons apply. */
export function toolsRowHtml(o: ToolsRowOpts): string {
  const parts: string[] = [];
  if (o.isRoot && o.playlistsEnabled && !o.isVideo) {
    parts.push(
      '<button type="button" class="tools-row-item playlist-new-card" id="playlist-new-card">' +
        '<span class="tools-row-icon">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="width:18px;height:18px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
        "</span>" +
        '<span class="tools-row-label">Neue Playlist\u2026</span>' +
        '<span class="tools-row-count"></span>' +
        "</button>"
    );
    parts.push(
      '<button type="button" class="tools-row-item playlist-new-card smart-new-card" id="smart-playlist-new-card"' +
        ' title="Intelligente Playlist erstellen">' +
        '<span class="tools-row-icon">' + o.icSmartPlaylist + "</span>" +
        '<span class="tools-row-label">Intelligente Playlist\u2026</span>' +
        '<span class="tools-row-count"></span>' +
        "</button>"
    );
    parts.push(
      '<button type="button" class="tools-row-item playlist-folder-card" id="all-titles-card"' +
        ' data-playlist-id="__alltitles__" title="Zeigt alle Titel der Ordner als Liste an">' +
        '<span class="tools-row-icon">' + o.icPlaylist + "</span>" +
        '<span class="tools-row-label">Titel</span>' +
        (o.allItemsCount > 0 ? '<span class="tools-row-count">' + o.allItemsCount + "</span>" : "") +
        "</button>"
    );
  }
  if (o.isRoot && o.offlineEnabled) {
    parts.push(
      '<button type="button" class="tools-row-item offline-folder-card" id="offline-folder-card">' +
        '<span class="tools-row-icon">' + o.icDl + "</span>" +
        '<span class="tools-row-label">Downloaded</span>' +
        '<span class="tools-row-count" id="offline-folder-count">0</span>' +
        "</button>"
    );
  }
  if (o.isRoot) {
    parts.push(
      '<button type="button" class="tools-row-item refresh-catalog-card" id="refresh-catalog-card" title="Neu laden">' +
        '<span class="tools-row-icon">' + o.icRefresh + "</span>" +
        "</button>"
    );
  }
  return parts.length ? '<div class="playlist-tools-row">' + parts.join("") + "</div>" : "";
}

/** Auto-favorites card; "" when `count` is 0. */
export function favoritesCardHtml(count: number, icStar: string, icFolderPlay: string): string {
  if (count <= 0) return "";
  return (
    '<div class="folder-card playlist-folder-card" data-playlist-id="__favorites__">' +
    '<div class="thumb-wrap playlist-thumb-wrap">' +
    '<div class="folder-thumb playlist-folder-icon">' + icStar + "</div>" +
    '<button class="playlist-cover-play-btn" title="Abspielen">' + icFolderPlay + "</button>" +
    "</div>" +
    '<div class="folder-name">Favoriten</div>' +
    '<div class="folder-count">' + count + " Titel</div>" +
    "</div>"
  );
}

export interface PlaylistCardOpts {
  escHtml: Esc;
  icPlaylist: string;
  icSmartPlaylist: string;
  icFolderPlay: string;
  icDots: string;
}

export function playlistCardHtml(
  pl: { id: string; name: string; smart?: { rules?: unknown } | null },
  count: number,
  o: PlaylistCardOpts
): string {
  const esc = o.escHtml;
  const isSmart = !!(pl.smart && pl.smart.rules);
  const iconHtml =
    o.icPlaylist +
    (isSmart ? '<span class="smart-pl-badge" title="Intelligente Playlist">' + o.icSmartPlaylist + "</span>" : "");
  return (
    '<div class="folder-card playlist-folder-card' + (isSmart ? " smart-playlist-card" : "") +
    '" data-playlist-id="' + esc(pl.id) + '">' +
    '<div class="thumb-wrap playlist-thumb-wrap">' +
    '<div class="folder-thumb playlist-folder-icon">' + iconHtml + "</div>" +
    '<button class="playlist-cover-play-btn" title="Abspielen">' + o.icFolderPlay + "</button>" +
    "</div>" +
    '<div class="folder-name">' + esc(pl.name) + "</div>" +
    '<div class="folder-count">' + count + " Titel</div>" +
    '<button class="playlist-folder-kebab" title="Mehr Optionen">' + o.icDots + "</button>" +
    "</div>"
  );
}

