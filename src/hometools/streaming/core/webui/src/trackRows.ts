/**
 * Track-list row HTML. Ported from `_search_filter.py::_appendTrackBatch`
 * (missing / debug-filtered / normal rows) and `renderSearchResults`
 * (folder + result rows). Pure: legacy globals come in via `ctx`.
 */

import { filenameFromPath, needsConversion } from "./pathUtils";

type Esc = (s: unknown) => string;

export interface TrackRowCtx {
  escHtml: Esc;
  fmtTime: (sec: number) => string;
  showOrig: boolean;
  currentIndex: number;
  bpmCalcEnabled: boolean;
  trackViewMode: string;
  isVideoMode: boolean;
  metadataEditEnabled: boolean;
  playlistsEnabled: boolean;
  itemNoun: string;
  bpmMin: number;
  bpmMax: number;
  dupePaths: { has(p: string): boolean } | null;
  dupeSafety: Record<string, boolean> | null;
  filePlaceholder: string;
  ic: {
    folderPlay: string; trash: string; dl: string; pin: string;
    edit: string; playlist: string; queue: string; dots: string;
  };
  /** undefined when metricPill bridge missing (legacy `typeof` guard). */
  renderBpmPill?: (bpm: number | undefined, min: number, max: number, opts: Record<string, unknown>) => string;
  renderInlineRating: (t: LegacyMediaItem, idx: number) => string;
  renderMoveWidget: (t: LegacyMediaItem, idx: number) => string;
}

type RowItem = LegacyMediaItem & { _missing?: boolean; _debugReason?: string; _hiddenShown?: boolean };

const pad2 = (n: unknown) => String(n).padStart(2, "0");
const ratingBarHtml = (r: number | undefined) =>
  r && r > 0 ? '<div class="rating-bar" style="width:' + (r / 5) * 100 + '%"></div>' : "";

/** One `<li>` for item `t` at real index `idx`. */
export function trackRowHtml(t: RowItem, idx: number, c: TrackRowCtx): string {
  const esc = c.escHtml;
  if (t._missing) {
    const seLabel = "S" + pad2(t.season) + "E" + pad2(t.episode);
    return (
      '<li class="track-item missing-episode" aria-disabled="true">' +
      '<span class="track-num"><span class="num-text">' + seLabel + "</span></span>" +
      '<div class="track-info"><div class="track-title">Folge fehlt</div>' +
      '<div class="track-artist">' + seLabel + " \u2014 nicht in der Bibliothek</div></div></li>"
    );
  }
  if (t._debugReason) {
    const dbgTitle = c.showOrig ? filenameFromPath(t.relative_path) : t.title;
    const dbgSub = t.artist || t.relative_path;
    const dbgThumb = t.thumbnail_url || c.filePlaceholder;
    return (
      '<li class="track-item debug-filtered">' +
      '<span class="track-num"><span class="num-text">\u00b7</span></span>' +
      '<div class="thumb-wrap track-thumb-wrap">' +
      '<img class="track-thumb" src="' + esc(dbgThumb) + '" alt="" loading="lazy">' +
      ratingBarHtml(t.rating) + "</div>" +
      '<div class="track-info">' +
      '<div class="track-title">' + esc(dbgTitle) + "</div>" +
      '<div class="track-artist">' + esc(dbgSub) + "</div>" +
      '<div class="debug-reason">' + esc(t._debugReason) + "</div>" +
      "</div></li>"
    );
  }

  const isSeries = (t.season || 0) > 0;
  const numLabel = isSeries ? "S" + pad2(t.season) + "E" + pad2(t.episode) : String(idx + 1);
  const displayTitle = c.showOrig ? filenameFromPath(t.relative_path) : t.title;
  const subtitle = t.artist || t.relative_path;
  const extraCls = (idx === c.currentIndex ? " active" : "") + (t._hiddenShown ? " track-item--hidden-shown" : "");
  const thumbSrc = t.thumbnail_url || c.filePlaceholder;
  const convertBadge = needsConversion(t.relative_path)
    ? '<span class="convert-badge" title="Wird on-the-fly konvertiert">\u26A1</span>'
    : "";
  const isDupe = !!(c.dupePaths && c.dupePaths.has(t.relative_path));
  const dupeSafe = isDupe && !!c.dupeSafety && !!c.dupeSafety[t.relative_path];
  const dupeDeleteCls = isDupe ? (dupeSafe ? " track-delete-btn--safe" : " track-delete-btn--warn") : "";
  const dupeDeleteTitle = isDupe
    ? dupeSafe
      ? "Duplikat l\u00f6schen (Gr\u00f6\u00dfe + L\u00e4nge nahezu identisch)"
      : "Duplikat l\u00f6schen \u2014 Vorsicht: Gr\u00f6\u00dfe oder L\u00e4nge weicht ab!"
    : "";
  const dupeBadge = isDupe
    ? '<span class="dupe-badge" title="Duplikat erkannt">Duplikat' +
      '<button class="track-delete-btn' + dupeDeleteCls + '" data-index="' + idx +
      '" title="' + esc(dupeDeleteTitle) + '">' + c.ic.trash + "</button></span>"
    : "";
  const tableEditable = c.trackViewMode === "table" && !c.isVideoMode && c.metadataEditEnabled && c.showOrig;
  const editAttrs = tableEditable
    ? ' contenteditable="true" spellcheck="false" data-relative-path="' + esc(t.relative_path || "") + '"'
    : "";
  const bpmPillHtml =
    c.isVideoMode || typeof c.renderBpmPill !== "function"
      ? ""
      : '<span class="track-bpm-cell">' +
        c.renderBpmPill(t.bpm, c.bpmMin, c.bpmMax, {
          index: idx, relativePath: t.relative_path, calcEnabled: c.bpmCalcEnabled,
        }) + "</span>";
  const rp = esc(t.relative_path || "");

  return (
    '<li class="track-item' + extraCls + '" data-index="' + idx + '">' +
    '<span class="track-num"><span class="num-text">' + numLabel + "</span></span>" +
    '<div class="thumb-wrap track-thumb-wrap">' +
    '<img class="track-thumb" src="' + esc(thumbSrc) + '" alt="" loading="lazy">' +
    '<button class="track-play-btn" data-index="' + idx + '" title="Abspielen">' + c.ic.folderPlay + "</button>" +
    ratingBarHtml(t.rating) + "</div>" +
    '<div class="track-info">' +
    '<div class="track-title"><span class="track-title-text"' + (tableEditable ? editAttrs + ' data-field="title"' : "") + ">" +
    esc(displayTitle) + "</span>" + convertBadge + dupeBadge + "</div>" +
    '<div class="track-artist"' + (tableEditable ? editAttrs + ' data-field="artist"' : "") + ">" + esc(subtitle) + "</div>" +
    "</div>" +
    bpmPillHtml +
    '<span class="track-duration-cell">' + (t.duration ? c.fmtTime(t.duration) : "") + "</span>" +
    '<span class="track-genre-cell">' + esc(t.genre || "") + "</span>" +
    '<button class="track-dl-btn" data-stream-url="' + esc(t.stream_url) +
    '" data-title="' + esc(t.title) +
    '" data-artist="' + esc(t.artist || "") +
    '" data-relative-path="' + rp +
    '" data-thumbnail-url="' + esc(t.thumbnail_url || "") +
    '" data-media-type="' + esc(t.media_type || c.itemNoun) + '" title="Download">' + c.ic.dl + "</button>" +
    '<button class="track-pin-btn" data-relative-path="' + rp +
    '" data-title="' + esc(t.title) + '" title="Favorit">' + c.ic.pin + "</button>" +
    (c.metadataEditEnabled
      ? '<button class="track-edit-btn" data-index="' + idx + '" title="Bearbeiten">' + c.ic.edit + "</button>"
      : "") +
    (c.playlistsEnabled
      ? '<button class="track-playlist-btn" data-relative-path="' + rp + '" title="Zur Playlist hinzuf\u00fcgen">' + c.ic.playlist + "</button>"
      : "") +
    '<button class="track-queue-btn" data-relative-path="' + rp + '" data-index="' + idx +
    '" title="Zur Warteschlange hinzuf\u00fcgen">' + c.ic.queue + "</button>" +
    '<button class="track-kebab-btn" data-relative-path="' + rp +
    '" data-title="' + esc(t.title) + '" title="Mehr Optionen">' + c.ic.dots + "</button>" +
    '<button class="track-reveal-btn" data-relative-path="' + rp +
    '" data-title="' + esc(t.title) + '" title="Im Explorer anzeigen">' +
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>' +
    "</button>" +
    c.renderInlineRating(t, idx) +
    c.renderMoveWidget(t, idx) +
    "</li>"
  );
}

/** Concatenated rows for `items[from..to)`; `realIdxMap[i]` = real index. */
export function trackRowsHtml(
  items: RowItem[],
  realIdxMap: number[],
  from: number,
  to: number,
  c: TrackRowCtx
): string {
  let html = "";
  for (let i = from; i < to; i++) html += trackRowHtml(items[i], realIdxMap[i], c);
  return html;
}

export interface FolderMatch {
  path: string;
  name: string;
  displayName?: string;
  count: number;
  thumbnail_url?: string;
}

/** Inner HTML of a search "folder" row. */
export function searchFolderRowHtml(fm: FolderMatch, esc: Esc, filePlaceholder: string, icFolderPlay: string): string {
  const thumbSrc = fm.thumbnail_url || filePlaceholder;
  const slash = fm.path.lastIndexOf("/");
  const parentDir = slash > 0 ? fm.path.substring(0, slash) : "";
  return (
    '<div class="track-number">' + icFolderPlay + "</div>" +
    '<div class="track-thumb-wrap"><img class="track-thumb" src="' + esc(thumbSrc) + '" loading="lazy"></div>' +
    '<div class="track-info">' +
    '<div class="track-title">' + esc(fm.displayName || fm.name) +
    ' <span class="search-folder-count">(' + fm.count + ")</span></div>" +
    '<div class="track-artist">Ordner</div>' +
    (parentDir ? '<div class="search-result-folder">' + esc(parentDir) + "</div>" : "") +
    "</div>"
  );
}

/** Inner HTML of a search result row (`i` = 0-based position). */
export function searchResultRowHtml(t: LegacyMediaItem, i: number, esc: Esc, filePlaceholder: string): string {
  const thumbSrc = t.thumbnail_url || filePlaceholder;
  const rp = t.relative_path || "";
  const lastSlash = rp.lastIndexOf("/");
  const folderPath = lastSlash > 0 ? rp.substring(0, lastSlash) : "";
  return (
    '<div class="track-number">' + (i + 1) + "</div>" +
    '<div class="track-thumb-wrap"><img class="track-thumb" src="' + esc(thumbSrc) + '" loading="lazy">' + ratingBarHtml(t.rating) + "</div>" +
    '<div class="track-info">' +
    '<div class="track-title">' + esc(t.title || t.relative_path) + "</div>" +
    '<div class="track-artist">' + esc(t.artist || "") + "</div>" +
    (folderPath ? '<div class="search-result-folder">' + esc(folderPath) + "</div>" : "") +
    "</div>"
  );
}

