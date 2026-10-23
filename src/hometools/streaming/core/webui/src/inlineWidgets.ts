/**
 * Per-row inline widgets HTML: star rating + move-to-folder widget.
 * Ported from `_track_render.py::renderInlineRating` and
 * `_library_tools.py::renderMoveWidget`. Pure; legacy globals passed in.
 */

type Esc = (s: unknown) => string;

export function inlineRatingHtml(
  rating: number | undefined,
  idx: number,
  enabled: boolean,
  icFilled: string,
  icEmpty: string
): string {
  if (!enabled) return "";
  const rounded = Math.round(rating || 0);
  let html = '<span class="track-inline-rating" data-index="' + idx + '">';
  for (let i = 1; i <= 5; i++) {
    html +=
      '<button class="track-inline-rating-star' + (i <= rounded ? " active" : "") +
      '" data-star="' + i + '" data-index="' + idx + '" title="' + i + (i === 1 ? " Stern" : " Sterne") + '">' +
      (i <= rounded ? icFilled : icEmpty) + "</button>";
  }
  return html + "</span>";
}

/** Up to 4 quick-pick folders: MRU first, topped up from `allFolders`. */
export function moveQuickPicks(recent: string[], allFolders: string[]): string[] {
  const picks = (recent || []).slice(0, 4);
  if (picks.length < 4) {
    const seen: Record<string, boolean> = {};
    picks.forEach((p) => {
      seen[p] = true;
    });
    for (let fi = 0; fi < allFolders.length && picks.length < 4; fi++) {
      if (!seen[allFolders[fi]]) {
        picks.push(allFolders[fi]);
        seen[allFolders[fi]] = true;
      }
    }
  }
  return picks;
}

export function moveWidgetHtml(
  idx: number,
  curFolder: string,
  recent: string[],
  allFolders: string[],
  esc: Esc,
  icTrash: string
): string {
  const picks = moveQuickPicks(recent, allFolders);
  let html = '<span class="track-move-widget" data-index="' + idx + '">';
  html += '<span class="move-quick-grid">';
  for (let i = 0; i < Math.min(4, picks.length); i++) {
    const isCur = picks[i] === curFolder;
    html +=
      '<button class="move-quick-btn' + (isCur ? " is-current" : "") +
      '" data-target="' + esc(picks[i]) +
      '" data-index="' + idx + '" title="Verschieben nach: ' + esc(picks[i]) + '">' +
      esc(picks[i]) + "</button>";
  }
  html += "</span>";
  html += '<select class="move-folder-select" data-index="' + idx + '">';
  html += '<option value="" disabled' + (curFolder ? "" : " selected") + ">Ordner w\u00e4hlen\u2026</option>";
  allFolders.forEach((f) => {
    html += '<option value="' + esc(f) + '"' + (f === curFolder ? " selected" : "") + ">" + esc(f) + "</option>";
  });
  html += "</select>";
  html +=
    '<button class="move-delete-btn" data-index="' + idx + '" title="Datei in den Papierkorb verschieben">' +
    icTrash + "</button>";
  return html + "</span>";
}

