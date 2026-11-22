/**
 * modules can call `getDom()` instead of taking elements via hooks.
 * Missing element -> `null` (never throws).
 */

const BY_ID = {
  player: "player",
  btnPlay: "btn-play",
  btnPrev: "btn-prev",
  btnNext: "btn-next",
  btnShuffle: "btn-shuffle",
  btnRepeat: "btn-repeat",
  trackList: "track-list",
  trackCount: "track-count",
  playerTitle: "player-title",
  playerArtist: "player-artist",
  playerThumb: "player-thumb",
  playerBarActions: "player-bar-actions",
  progressBar: "progress-bar",
  timeCur: "time-cur",
  timeDur: "time-dur",
  searchInput: "search-input",
  sortField: "sort-field",
  filterCombinedBtn: "filter-combined",
  filterHiddenBtn: "filter-hidden",
  folderGrid: "folder-grid",
  trackView: "track-view",
  backBtn: "back-btn",
  logoHomeBtn: "header-logo",
  headerTitle: "header-title",
  videoOverlay: "video-overlay",
  videoMiniBar: "video-mini-bar",
  miniTitle: "mini-title",
  miniArtist: "mini-artist",
  miniThumb: "mini-thumb",
  miniPlayBtn: "mini-play-btn",
  miniExpandBtn: "mini-expand-btn",
  videoCloseBtn: "video-close-btn",
  videoFsBtn: "video-fs-btn",
  videoCastBtn: "video-cast-btn",
  videoSkipIntroBtn: "video-skip-intro-btn",
  videoOverlayTitleText: "video-overlay-title-text",
  videoFloatContainer: "video-float-container",
  videoFloatWrap: "video-float-wrap",
  floatExpandBtn: "float-expand-btn",
  floatCloseBtn: "float-close-btn",
  playAllBtn: "play-all-btn",
  downloadedPill: "downloaded-pill",
  breadcrumb: "breadcrumb",
  viewToggle: "view-toggle",
} as const;

const BY_SELECTOR = {
  filterBar: ".filter-bar",
  playerBar: ".player-bar",
  videoWrap: ".video-wrap",
} as const;

export type DomRefs = { [K in keyof typeof BY_ID | keyof typeof BY_SELECTOR]: HTMLElement | null };

/** Look up every player element once. */
export function collectDom(doc: Pick<Document, "getElementById" | "querySelector"> = document): DomRefs {
  const out: Record<string, HTMLElement | null> = {};
  for (const [k, id] of Object.entries(BY_ID)) out[k] = doc.getElementById(id);
  for (const [k, sel] of Object.entries(BY_SELECTOR)) out[k] = doc.querySelector<HTMLElement>(sel);
  return out as DomRefs;
}

let _cache: DomRefs | null = null;

/** Cached refs (first call collects). */
export function getDom(): DomRefs {
  if (!_cache) _cache = collectDom();
  return _cache;
}

/** Test hook. */
export function resetDom(): void {
  _cache = null;
}
