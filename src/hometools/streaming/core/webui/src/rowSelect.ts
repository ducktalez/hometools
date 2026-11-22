/**
 * Desktop row click: select/highlight without starting playback.
 * Zustandslos.
 */

export function selectTrackRow(trackList: ParentNode, idx: number): void {
  document.querySelectorAll(".track-item.row-selected").forEach((el) => {
    el.classList.remove("row-selected");
  });
  const row = trackList.querySelector('.track-item[data-index="' + idx + '"]');
  if (row) row.classList.add("row-selected");
}

