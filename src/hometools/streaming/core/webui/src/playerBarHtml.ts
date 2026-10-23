/**
 * Player-bar actions + BPM-adjust menu markup.
 * Ported from `_search_filter.py::updatePlayerBarActions` and
 * `_track_render.py::_openBpmAdjustMenu` (markup halves). Wiring stays legacy.
 */

type Esc = (s: unknown) => string;

export function playerBarActionsHtml(
  t: LegacyMediaItem,
  allFolders: string[],
  curFolder: string,
  inMoverMode: boolean,
  esc: Esc,
  icDots: string,
  icTrash: string
): string {
  const kebabHtml =
    '<button class="player-bar-kebab-btn" id="player-bar-kebab" ' +
    'data-relative-path="' + esc(t.relative_path || "") + '" ' +
    'data-title="' + esc(t.title || "") + '" ' +
    'title="Mehr Optionen">' + icDots + "</button>";
  if (!inMoverMode) return kebabHtml;

  let moveHtml = "";
  if (allFolders.length) {
    moveHtml =
      '<select class="player-bar-move-select" id="player-bar-move-select">' +
      '<option value="" disabled selected>Verschieben\u2026</option>';
    allFolders.forEach((f) => {
      moveHtml += '<option value="' + esc(f) + '"' + (f === curFolder ? " disabled" : "") + ">" + esc(f) + "</option>";
    });
    moveHtml += "</select>";
  }
  const trashHtml =
    '<button class="player-bar-trash-btn" id="player-bar-trash" title="Datei l\u00f6schen">' + icTrash + "</button>";
  return (
    (moveHtml ? '<div class="player-bar-actions-row">' + moveHtml + "</div>" : "") +
    '<div class="player-bar-actions-row">' + trashHtml + kebabHtml + "</div>"
  );
}

export interface BpmMenuIcons {
  chevronsDown: string;
  refresh: string;
  chevronsUp: string;
}

export function bpmAdjustMenuHtml(curBpm: number, ic: BpmMenuIcons): string {
  const has = curBpm > 0;
  const dis = has ? "" : " disabled";
  return (
    '<div class="bpm-adjust-current">' + (has ? Math.round(curBpm) + " BPM" : "BPM unbekannt") + "</div>" +
    '<div class="bpm-adjust-actions">' +
    '<button type="button" class="bpm-adjust-btn" data-action="slower"' + dis +
    ' title="Wert halbieren \u2014 falls doppelt so schnell erkannt wurde">' + ic.chevronsDown + "<span>Langsamer</span></button>" +
    '<button type="button" class="bpm-adjust-btn" data-action="reload" title="BPM neu berechnen">' +
    ic.refresh + "<span>Neu berechnen</span></button>" +
    '<button type="button" class="bpm-adjust-btn" data-action="faster"' + dis +
    ' title="Wert verdoppeln \u2014 falls halb so schnell erkannt wurde">' + ic.chevronsUp + "<span>Schneller</span></button>" +
    "</div>" +
    '<div class="bpm-adjust-manual">' +
    '<input type="number" class="bpm-adjust-input" min="0" max="400" step="1" inputmode="numeric" ' +
    'value="' + (has ? Math.round(curBpm) : "") + '" placeholder="BPM manuell">' +
    '<button type="button" class="bpm-adjust-apply">\u00dcbernehmen</button>' +
    "</div>"
  );
}

