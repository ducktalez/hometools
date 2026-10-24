/**
 * Small chrome markup/text helpers: indexing toast, table header, view-toggle.
 * Ported from `_core.py::showIndexingToast` and
 * `_queue.py::_applyTrackViewMode` (markup/text halves).
 */

/** Progress percent from a cache-status object or `{percent}`; null if none. */
export function indexProgressPercent(prog: unknown): number | null {
  if (!prog || typeof prog !== "object") return null;
  const p = prog as { build_percent?: unknown; percent?: unknown };
  if (typeof p.build_percent === "number") return p.build_percent;
  if (typeof p.percent === "number") return p.percent;
  return null;
}

export function indexingToastHtml(msg: string | null | undefined, prog: unknown, esc: (s: unknown) => string): string {
  const pct = indexProgressPercent(prog);
  let barHtml = "";
  if (pct !== null && pct >= 0) {
    const w = Math.max(2, Math.min(100, pct));
    barHtml = '<div class="ht-index-progress"><div class="ht-index-progress-fill" style="width:' + w + '%"></div></div>';
  }
  return '<div class="ht-index-row"><span class="spinner"></span>' + esc(msg || "Indexing\u2026") + "</div>" + barHtml;
}

export const TRACK_TABLE_HEADER_HTML =
  "<span></span><span></span>" +
  "<span>Titel</span><span>Interpret</span>" +
  "<span>Dauer</span><span>Genre</span><span>BPM</span><span>\u2605</span><span></span>";

export interface ViewToggleView {
  useListIcon: boolean;
  title: string;
  locked: boolean;
}

export function viewToggleView(tableMode: boolean, isVideoMode: boolean): ViewToggleView {
  return {
    useListIcon: tableMode,
    title: tableMode
      ? "Detailansicht \u2014 Klick f\u00fcr normale Listenansicht"
      : "Listenansicht \u2014 Klick f\u00fcr Detailansicht (Tabelle)",
    locked: isVideoMode,
  };
}

