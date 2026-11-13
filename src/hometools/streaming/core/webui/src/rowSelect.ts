/**
 * Desktop row click: select/highlight without starting playback.
 * Ported from `player_js/_search_filter.py`. Zustandslos.
 */

export function selectTrackRow(trackList: ParentNode, idx: number): void {
  document.querySelectorAll(".track-item.row-selected").forEach((el) => {
    el.classList.remove("row-selected");
  });
  const row = trackList.querySelector('.track-item[data-index="' + idx + '"]');
  if (row) row.classList.add("row-selected");
}

