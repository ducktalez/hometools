/**
 * Panel-body HTML: duplicate groups + queue list.
 * Ported from `_library_tools.py::openDupePanel` (markup half) and
 * `_core.py::renderQueuePanel` (markup half). DOM wiring stays legacy.
 */

import { _fmtDuration, _fmtFileSize, _fmtDate } from "./dupeUtils";

type Esc = (s: unknown) => string;

export interface DupePanelOpts {
  escHtml: Esc;
  filePlaceholder: string;
  icDuplicate: string;
  icTrash: string;
}

export function dupePanelBodyHtml(
  allItems: LegacyMediaItem[],
  dupeMap: Record<string, number[]>,
  dupeSafety: Record<string, boolean> | null,
  o: DupePanelOpts
): string {
  const esc = o.escHtml;
  const keys = Object.keys(dupeMap || {});
  if (keys.length === 0) {
    return '<div style="text-align:center;color:var(--sub);padding:2rem 0">Keine Duplikate gefunden.</div>';
  }
  let html = "";
  keys.forEach((key) => {
    const indices = dupeMap[key];
    const first = allItems[indices[0]];
    const firstTitle = first ? first.title || key : key;
    html += '<div class="dupe-group">';
    html +=
      '<div class="dupe-group-header">' + o.icDuplicate +
      "<span>" + esc(firstTitle) + "</span>" +
      '<span class="dupe-group-count">(' + indices.length + "x)</span></div>";
    indices.forEach((idx) => {
      const t = allItems[idx];
      if (!t) return;
      const thumbSrc = t.thumbnail_url || o.filePlaceholder;
      const rp = t.relative_path || "";
      const sl = rp.lastIndexOf("/");
      const folder = sl > 0 ? rp.substring(0, sl) : "";
      const metaParts: string[] = [];
      if (t.duration) metaParts.push(_fmtDuration(t.duration));
      if (t.bitrate) metaParts.push(t.bitrate + "\u00a0kbps");
      if (t.file_size) metaParts.push(_fmtFileSize(t.file_size));
      if (t.mtime) metaParts.push(_fmtDate(t.mtime));
      const metaHtml = metaParts.length
        ? '<div class="dupe-group-item-meta">' + metaParts.join(" \u00b7 ") + "</div>"
        : "";
      const isSafe = !!(dupeSafety && dupeSafety[t.relative_path]);
      const trashCls = isSafe ? " dupe-trash-btn--safe" : " dupe-trash-btn--warn";
      const trashTitle = isSafe
        ? "In den Papierkorb verschieben (Gr\u00f6\u00dfe + L\u00e4nge nahezu identisch)"
        : "In den Papierkorb verschieben \u2014 Vorsicht: Gr\u00f6\u00dfe oder L\u00e4nge weicht ab!";
      html +=
        '<div class="dupe-group-item" data-all-index="' + idx + '">' +
        '<img src="' + esc(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="dupe-group-item-info">' +
        '<div class="dupe-group-item-title">' + esc(t.title || t.relative_path) + "</div>" +
        '<div class="dupe-group-item-path">' + esc(folder || t.relative_path) + "</div>" +
        metaHtml +
        "</div>" +
        '<button class="dupe-trash-btn' + trashCls + '" data-all-index="' + idx +
        '" title="' + esc(trashTitle) + '">' + o.icTrash + "</button>" +
        "</div>";
    });
    html += "</div>";
  });
  return html;
}

/** Queue panel body. Empty queue -> empty-state div (caller hides clear btn). */
export function queuePanelHtml(
  queue: LegacyMediaItem[],
  esc: Esc,
  filePlaceholder: string,
  icRemove: string
): string {
  if (!queue.length) return '<div class="queue-empty">Die Warteschlange ist leer.</div>';
  let html = '<ul class="queue-list" id="queue-list">';
  queue.forEach((item, idx) => {
    const thumbSrc = item.thumbnail_url || filePlaceholder;
    html +=
      '<li class="queue-item" data-queue-index="' + idx + '">' +
      '<img class="queue-item-thumb" src="' + esc(thumbSrc) + '" alt="" loading="lazy">' +
      '<div class="queue-item-info">' +
      '<div class="queue-item-title">' + esc(item.title) + "</div>" +
      '<div class="queue-item-artist">' + esc(item.artist || item.relative_path) + "</div>" +
      "</div>" +
      '<button class="queue-item-remove" data-queue-index="' + idx + '" title="Entfernen">' + icRemove + "</button>" +
      "</li>";
  });
  return html + "</ul>";
}

export interface CtxMenuEntry {
  label: string;
  icon?: string;
  danger?: boolean;
}
/** Buttons of the generic context menu. Ported from `_library_tools.py::_openCtxMenu`. */
export function ctxMenuHtml(items: CtxMenuEntry[], esc: Esc): string {
  return items
    .map(
      (it, i) =>
        '<button class="ht-ctx-item' + (it.danger ? " ht-ctx-item--danger" : "") + '" data-idx="' + i + '">' +
        (it.icon || "") + " " + esc(it.label) +
        "</button>"
    )
    .join("");
}