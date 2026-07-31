"""CSS fragment: track list (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_track_list_css() -> str:
    """Return the track list section of the dark-theme CSS."""
    return """/* ── Inline track rating stars ── */
.track-inline-rating {
  display: none; align-items: center; gap: 0px; flex-shrink: 0; margin-left: 4px;
}
body.tool-inline-ratings .track-inline-rating { display: flex; }
.track-inline-rating-star {
  background: none; border: none; padding: 1px; cursor: pointer; color: #555;
  width: 18px; height: 18px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.1s; -webkit-tap-highlight-color: transparent;
}
.track-inline-rating-star svg { width: 13px; height: 13px; }
.track-inline-rating-star.active { color: #ffd700; }
.track-inline-rating-star:hover { color: #ffd700; }
/* Hide other track buttons when inline ratings active (reduce clutter) */
body.tool-inline-ratings .track-dl-btn,
body.tool-inline-ratings .track-pin-btn,
body.tool-inline-ratings .track-edit-btn,
body.tool-inline-ratings .track-playlist-btn,
body.tool-inline-ratings .track-queue-btn { display: none; }
/* Hide individual button groups via tools toggles */
body.tool-hide-downloads .track-dl-btn { display: none; }
body.tool-hide-playlists .track-playlist-btn { display: none; }
/* ── Duplicate detection badges ── */
.dupe-badge {
  display: none; font-size: 0.6rem; color: #000; background: #f5a623;
  padding: 1px 4px 1px 6px; border-radius: 8px; margin-left: 6px; vertical-align: middle;
  font-weight: 600; letter-spacing: 0.02em; white-space: nowrap;
  align-items: center; gap: 2px;
}
body.tool-show-duplicates .dupe-badge { display: inline-flex; }
/* Inline delete button — lives inside .dupe-badge pill */
.track-delete-btn {
  background: none; border: none; color: #000; cursor: pointer;
  padding: 0; margin-left: 2px; display: inline-flex; align-items: center;
  opacity: 0.55; transition: opacity 0.12s, color 0.12s;
  line-height: 1;
}
.track-delete-btn svg { width: 12px; height: 12px; }
.track-delete-btn:hover { opacity: 1; color: #7f1d1d; }
/* Safety-based colour coding (set when dupe-map is built):
   --safe  = both size AND duration within 2 % → amber, probably identical rips
   --warn  = deviation > 2 % in either metric   → red,   review before deleting */
.track-delete-btn--safe { opacity: 0.9; color: #f59e0b; }
.track-delete-btn--safe:hover { opacity: 1; color: #d97706; }
.track-delete-btn--warn { opacity: 0.9; color: #ef4444; }
.track-delete-btn--warn:hover { opacity: 1; color: #b91c1c; }
/* ── Duplicate list panel ── */
.dupe-panel-backdrop {
  position: fixed; inset: 0; z-index: 310; background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
}
.dupe-panel-backdrop[hidden] { display: none; }
.dupe-panel {
  background: var(--surface); border: 1px solid #333; border-radius: 12px;
  padding: 1.2rem 1.4rem; width: min(480px, 94vw);
  max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.6);
}
.dupe-panel-title { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.5rem; }
.dupe-panel-subtitle { font-size: 0.75rem; color: var(--sub); margin-bottom: 1rem; }
.dupe-group { margin-bottom: 1rem; border-bottom: 1px solid #262626; padding-bottom: 0.75rem; }
.dupe-group:last-child { border-bottom: none; }
.dupe-group-header {
  font-size: 0.78rem; font-weight: 600; color: var(--accent); margin-bottom: 0.4rem;
  display: flex; align-items: center; gap: 6px;
}
.dupe-group-header svg { width: 14px; height: 14px; flex-shrink: 0; }
.dupe-group-count { font-size: 0.65rem; color: var(--sub); font-weight: 400; }
.dupe-group-item {
  display: flex; align-items: center; gap: 0.6rem; padding: 0.3rem 0; cursor: pointer;
  border-radius: 6px; transition: background 0.1s;
}
.dupe-group-item:hover { background: var(--surface2); }
.dupe-group-item img { width: 32px; height: 32px; border-radius: 4px; object-fit: cover; flex-shrink: 0; background: var(--surface2); }
.dupe-group-item-info { flex: 1; min-width: 0; }
.dupe-group-item-title { font-size: 0.82rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dupe-group-item-path { font-size: 0.65rem; color: var(--sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dupe-group-item-meta { font-size: 0.6rem; color: #666; margin-top: 2px; letter-spacing: 0.01em; }
.dupe-trash-btn {
  background: none; border: none; color: var(--sub); cursor: pointer; padding: 0.3rem;
  flex-shrink: 0; border-radius: 4px; transition: color 0.12s, background 0.12s;
  display: flex; align-items: center; justify-content: center;
}
.dupe-trash-btn svg { width: 16px; height: 16px; }
.dupe-trash-btn:hover { color: #ef4444; background: rgba(239,68,68,0.12); }
/* Safety colour coding — same thresholds as .track-delete-btn variants */
.dupe-trash-btn--safe { color: #f59e0b; }
.dupe-trash-btn--safe:hover { color: #d97706; background: rgba(245,158,11,0.12); }
.dupe-trash-btn--warn { color: #ef4444; }
.dupe-trash-btn--warn:hover { color: #b91c1c; background: rgba(239,68,68,0.12); }
.dupe-panel-close {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.4rem 0.9rem; cursor: pointer;
  font-size: 0.85rem; margin-top: 0.5rem; width: 100%;
  transition: border-color 0.12s, color 0.12s;
}
.dupe-panel-close:hover { border-color: var(--text); color: var(--text); }
.dupe-panel-play-all {
  background: var(--accent); border: none; color: #000;
  border-radius: 6px; padding: 0.5rem 0.9rem; cursor: pointer;
  font-size: 0.85rem; font-weight: 600; margin-top: 0.75rem; width: 100%;
  transition: opacity 0.12s;
}
.dupe-panel-play-all:hover { opacity: 0.85; }
.dupe-show-link {
  display: none; font-size: 0.72rem; color: var(--accent); cursor: pointer;
  margin-top: 2px; background: none; border: none; padding: 0;
  text-decoration: underline;
}
.dupe-show-link:hover { color: var(--warn); }
/* ── File-Mover (inline move-to-folder widget) ── */
.track-move-widget {
  display: none; align-items: center; gap: 4px; margin-left: auto; flex-shrink: 0;
  font-size: 0.68rem; padding: 2px 0;
}
body.tool-show-file-mover .track-move-widget { display: flex; }
body.tool-show-file-mover .track-dl-btn,
body.tool-show-file-mover .track-pin-btn,
body.tool-show-file-mover .track-edit-btn,
body.tool-show-file-mover .track-playlist-btn,
body.tool-show-file-mover .track-queue-btn { display: none; }
.move-quick-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 2px; flex-shrink: 1;
  max-width: 160px;
}
.move-quick-btn {
  background: var(--surface2); color: var(--sub); border: 1px solid transparent;
  border-radius: 4px; padding: 1px 6px; cursor: pointer; font-size: 0.62rem;
  white-space: nowrap; max-width: 78px; overflow: hidden; text-overflow: ellipsis;
  line-height: 1.35; transition: background 0.1s, border-color 0.12s, color 0.12s;
  text-align: left;
}
.move-quick-btn:hover { background: var(--accent); color: #000; border-color: var(--accent); }
.move-quick-btn.is-current { border-color: var(--accent); color: var(--accent); pointer-events: none; opacity: 0.5; }
.move-folder-select {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 6px; padding: 2px 6px; font-size: 0.75rem; cursor: pointer;
  max-width: 140px; flex-shrink: 1;
}
.move-folder-select:focus { border-color: var(--accent); outline: none; }
.move-delete-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  border-left: 1px solid #444; padding: 2px 6px 2px 8px;
  font-size: 0.62rem; display: flex; align-items: center; gap: 3px;
  border-radius: 0 4px 4px 0; white-space: nowrap; flex-shrink: 0;
  transition: color 0.12s, background 0.12s;
}
.move-delete-btn svg { width: 11px; height: 11px; flex-shrink: 0; }
.move-delete-btn:hover { color: #e57373; background: rgba(229,115,115,0.08); }
.folder-filter-bar {
  padding: 0 16px 4px; display: flex; align-items: center; gap: 8px;
}
#global-search-input {
  flex: 1; padding: 8px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface2); color: var(--text);
  font-size: 0.95rem; outline: none;
}
#global-search-input:focus { border-color: var(--accent); }
#global-search-input::placeholder { color: var(--sub); }
.global-search-clear {
  background: none; border: none; color: var(--sub); cursor: pointer;
  font-size: 1.2rem; padding: 4px 8px; line-height: 1;
}
.global-search-clear:hover { color: var(--text); }
/* Search results: folder path shown under artist */
.search-result-folder { font-size: 0.7rem; color: var(--sub); opacity: 0.7; margin-top: 1px; }
/* Folder/series matches inside the global-search result list */
.search-folder-item { background: rgba(255,255,255,0.02); }
.search-folder-item .track-number {
  color: var(--accent, #1db954); display: flex; align-items: center; justify-content: center;
}
.search-folder-item .track-number svg { width: 14px; height: 14px; fill: currentColor; }
.search-folder-item .track-artist { color: var(--accent, #1db954); font-weight: 500; }
.search-folder-count { color: var(--sub); font-weight: 400; font-size: 0.85em; }
.offline-folder-card { cursor: pointer; }
.offline-folder-icon {
  display: flex; align-items: center; justify-content: center;
  background: var(--surface2); border-radius: 6px; width: 100%; aspect-ratio: 1;
}
.offline-folder-icon svg { width: 36px; height: 36px; fill: var(--accent); }
.fav-badge {
  position: absolute; top: 0.5rem; right: 0.5rem;
  color: var(--accent); font-size: 1rem; line-height: 1;
  pointer-events: none; z-index: 2;
}
.fav-folder { border: 1px solid var(--accent); border-radius: 8px; }
/* Language flag badges */
.lang-badge {
  display: inline-block; width: 18px; height: 12px; vertical-align: middle;
  margin-left: 4px; border-radius: 2px; overflow: hidden;
  line-height: 0; flex-shrink: 0;
}
.lang-badge svg { width: 18px; height: 12px; display: block; }
/* Fixed-position primary-language flag on video folder cards (top-right corner).
   Always rendered for mono-lingual folders so the default language is visible. */
.folder-lang-corner {
  position: absolute; top: 6px; right: 6px;
  z-index: 3; pointer-events: none;
  background: rgba(0,0,0,0.55); border-radius: 3px;
  padding: 2px; line-height: 0;
}
.folder-lang-corner .composite-flag,
.folder-lang-corner .lang-badge { margin: 0; }
.folder-grid.list-mode .folder-lang-corner { top: 4px; right: 4px; }
/* Composite flag: main flag + optional smaller subtitle flag overlay */
.composite-flag {
  position: relative; display: inline-block; width: 22px; height: 14px;
  vertical-align: middle; flex-shrink: 0;
}
.composite-flag > svg { width: 18px; height: 12px; display: block; border-radius: 2px; }
.composite-flag-sub {
  position: absolute; bottom: -2px; right: -4px;
  width: 11px; height: 8px; line-height: 0;
  border: 1px solid #1a1a1a; border-radius: 1px; overflow: hidden;
  background: #1a1a1a;
}
.composite-flag-sub svg { width: 11px; height: 8px; display: block; }
/* Language select buttons on multi-lang folder cards */
.lang-select-btn {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 4px; border: 1px solid transparent; border-radius: 4px;
  background: none; cursor: pointer; color: var(--sub); font-size: 0.7rem;
  transition: border-color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent; vertical-align: middle;
}
.lang-select-btn:hover { border-color: var(--accent); background: rgba(255,255,255,0.05); }
.lang-select-btn.active-lang { border-color: var(--accent); }
.folder-count .lang-select-btn + .lang-select-btn { margin-left: 2px; }
/* Multi-language folder cards */
.multi-lang-folder { position: relative; }
/* Language picker overlay */
.lang-picker-overlay {
  z-index: 50; min-width: 220px; max-width: 300px;
  background: #2a2a2a; border: 1px solid #444; border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.5); padding: 8px 0;
  animation: langPickerIn .15s ease-out;
}
@keyframes langPickerIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.lang-picker-title {
  padding: 6px 14px 8px; color: #aaa; font-size: 0.78rem; font-weight: 600;
  border-bottom: 1px solid #333; margin-bottom: 4px;
}
.lang-picker-item {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 10px 14px; border: none; background: none; color: #eee;
  font-size: 0.9rem; cursor: pointer; text-align: left;
  transition: background .1s;
}
.lang-picker-item:hover { background: #3a3a3a; }
.lang-picker-flag { display: inline-block; width: 24px; height: 16px; line-height: 0; flex-shrink: 0; }
.lang-picker-flag svg { width: 24px; height: 16px; display: block; }
.lang-picker-label { flex: 1; }
.lang-picker-count { color: #888; font-size: 0.8rem; }
/* Audiobook folder styling */
.audiobook-folder .folder-icon { color: #a0c4ff; }
.audiobook-folder .folder-name { color: #a0c4ff; }
/* Recently played section */
.recent-section { padding: 0.5rem 0.75rem 0; }
.recent-section-title {
  font-size: 0.68rem; text-transform: uppercase; letter-spacing: .08em;
  color: var(--sub); margin-bottom: 0.4rem; padding-left: 0.1rem;
}
.recent-scroll {
  display: flex; gap: 0.65rem; overflow-x: auto; padding-bottom: 0.4rem;
  scrollbar-width: thin; scrollbar-color: #444 transparent;
  -webkit-overflow-scrolling: touch;
}
.recent-scroll::-webkit-scrollbar { height: 3px; }
.recent-scroll::-webkit-scrollbar-thumb { background: #444; border-radius: 2px; }
.recent-card {
  flex-shrink: 0; width: 100px; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.recent-thumb-wrap {
  position: relative; width: 100px; height: 100px;
  border-radius: 6px; overflow: hidden; background: #2a2a2a;
}
.recent-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.recent-progress-bar {
  position: absolute; bottom: 0; left: 0; height: 3px; background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.recent-title {
  font-size: 0.72rem; margin-top: 0.25rem; line-height: 1.2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.recent-sub {
  font-size: 0.62rem; color: var(--sub); margin-top: 0.1rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.recent-card:hover .recent-title { color: var(--accent); }
body.modal-open { overflow: hidden; }
.offline-library {
  position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,0.62);
  display: flex; align-items: flex-end; justify-content: center; padding: 1rem;
}
.offline-library[hidden] { display: none; }
.offline-panel {
  width: min(760px, 100%); max-height: min(82vh, 900px);
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--surface); border: 1px solid #333; border-radius: 16px;
  box-shadow: 0 20px 48px rgba(0,0,0,0.45);
}
.offline-head {
  display: flex; align-items: flex-start; gap: 0.75rem;
  padding: 1rem 1rem 0.75rem; border-bottom: 1px solid #262626;
}
.offline-title-wrap { flex: 1 1 0; min-width: 0; }
.offline-title { font-size: 1rem; font-weight: 700; }
.offline-subtitle, .offline-summary-detail {
  font-size: 0.78rem; color: var(--sub); margin-top: 0.2rem;
}
.offline-summary {
  padding: 0.75rem 1rem 0.25rem; font-size: 0.85rem; color: var(--text);
}
.offline-summary.warn { color: #ffcc00; }
.offline-toolbar {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  padding: 0.5rem 1rem 0.9rem;
}
.offline-toolbar select {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; padding: 0.4rem 0.8rem; font-size: 0.8rem;
}
.offline-download-list {
  list-style: none; margin: 0; padding: 0; overflow: auto; border-top: 1px solid #202020;
}
.offline-download-item {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.8rem 1rem; border-bottom: 1px solid #202020; cursor: pointer;
}
.offline-download-item:hover { background: var(--surface2); }
.offline-download-thumb {
  width: 48px; height: 48px; border-radius: 6px; object-fit: cover; background: var(--surface2);
  flex-shrink: 0;
}
.offline-download-meta { flex: 1 1 0; min-width: 0; }
.offline-download-title {
  font-size: 0.9rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.offline-download-sub, .offline-download-size {
  font-size: 0.77rem; color: var(--sub); margin-top: 0.12rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.offline-download-delete {
  background: none; border: 1px solid #555; color: var(--sub); border-radius: 999px;
  padding: 0.35rem 0.65rem; cursor: pointer; flex-shrink: 0;
}
.offline-download-delete:hover { color: #ff6b6b; border-color: #ff6b6b; }
.empty-downloads {
  text-align: center; color: var(--sub); padding: 2rem 1rem; font-size: 0.85rem;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem max(1rem, var(--sal)) 0.5rem max(1rem, var(--sar));
  background: var(--surface);
  border-bottom: 1px solid #333; flex-shrink: 0;
  overflow: hidden;
  max-height: 100px;
  transition: max-height 0.22s ease, padding-top 0.22s ease, padding-bottom 0.22s ease, border-bottom-width 0.22s ease;
}
.filter-bar.fb-scroll-hidden {
  max-height: 0; padding-top: 0; padding-bottom: 0; border-bottom-width: 0;
}
/* Header global search (right-aligned in the header) */
.header-search {
  margin-left: auto; flex: 0 1 200px; min-width: 80px;
  background: var(--surface2); color: var(--text);
  border: 1px solid #444; border-radius: 20px;
  padding: 0.35rem 0.75rem; font-size: 0.82rem; outline: none;
}
.header-search:focus { border-color: var(--accent); }
.header-search::placeholder { color: var(--sub); }
/* search-wrap: stretchy input with embedded count label on the right */
.search-wrap { position: relative; flex: 1 1 0; min-width: 0; }
.search-wrap #search-input { width: 100%; box-sizing: border-box; padding-right: 4.5rem; }
.track-count {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  font-size: 0.75rem; color: var(--sub); white-space: nowrap; pointer-events: none;
  max-width: 4rem; overflow: hidden; text-overflow: ellipsis;
}
.filter-bar input, .filter-bar select {
  background: var(--surface2); color: var(--text);
  border: 1px solid #444; border-radius: 20px;
  padding: 0.4rem 0.8rem; font-size: 0.85rem; outline: none; min-width: 0;
}
.filter-bar input { flex: 1 1 0; }
.filter-bar input:focus, .filter-bar select:focus { border-color: var(--accent); }
.filter-bar select { color-scheme: dark; }
/* Filter-Chips (Schnellfilter in der Track-Liste) */
.filter-chip {
  background: var(--surface2); color: var(--sub);
  border: 1px solid #444; border-radius: 20px;
  padding: 0.35rem 0.65rem; font-size: 0.78rem; font-weight: 500;
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 0.25rem;
  transition: color 0.12s, border-color 0.12s;
  -webkit-tap-highlight-color: transparent; line-height: 1;
}
.filter-chip:hover { border-color: var(--accent); color: var(--text); }
.filter-chip.active { border-color: var(--accent); color: var(--accent); }
.filter-chip svg { width: 11px; height: 11px; fill: currentColor; flex-shrink: 0; }

/* ── Combined "Filtern" popover (Bewertung + Favorit + Genre) ──
   Mirrors .ht-ctx-menu's fixed-position anchored-card look (see
   css/_table_view.py) but hosts form controls instead of a menu list. */
.filter-popover {
  position: fixed; z-index: 9999; min-width: 220px;
  background: #1e1e1e; border: 1px solid #333; border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.45);
  padding: 0.75rem 0.9rem;
  display: flex; flex-direction: column; gap: 0.65rem;
}
.filter-popover-section { display: flex; flex-direction: column; gap: 0.35rem; }
.filter-popover-label {
  font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--sub);
}
.filter-popover-stars { display: flex; gap: 4px; }
.filter-popover-star {
  background: none; border: none; padding: 2px; cursor: pointer; color: #555;
  width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
  transition: color 0.12s; -webkit-tap-highlight-color: transparent;
}
.filter-popover-star svg { width: 16px; height: 16px; }
.filter-popover-star.active { color: #ffd700; }
.filter-popover-star:hover { color: #ffd700; }
.filter-popover-toggle {
  display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text);
  cursor: pointer; -webkit-tap-highlight-color: transparent;
}
.filter-popover-genre-select {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 6px; padding: 0.35rem 0.5rem; font-size: 0.85rem; outline: none;
  color-scheme: dark;
}
.filter-popover-genre-select:focus { border-color: var(--accent); }
.filter-popover-reset {
  background: none; border: 1px solid #444; color: var(--sub); cursor: pointer;
  border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.8rem;
  transition: border-color 0.12s, color 0.12s;
}
.filter-popover-reset:hover { border-color: var(--text); color: var(--text); }

/* ── Item list ── */
.track-list-wrap { flex: 1 1 0; overflow-y: auto; }
.track-list { list-style: none; }
.track-item {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.65rem max(1rem, var(--sar)) 0.65rem max(1rem, var(--sal));
  cursor: pointer;
  border-bottom: 1px solid #222; transition: background 0.12s;
  -webkit-tap-highlight-color: transparent;
}
.track-item:hover  { background: var(--surface2); }
.track-item.active { background: #183320; }
.track-item.active .track-artist { color: var(--accent); }
/* Desktop click-to-select (no playback) — subtle highlight distinct
   from the .active (currently playing) state. */
.track-item.row-selected:not(.active) { background: rgba(255,255,255,0.06); }
.track-num {
  min-width: 26px; text-align: center; font-size: 0.78rem;
  color: var(--sub); flex-shrink: 0; white-space: nowrap; padding-right: 4px;
}
/* In a series folder (any item has season>0), fix the num column to S01E12 width */
.track-list--series .track-num { width: 4rem; min-width: 4rem; }
.track-item.active .num-text { display: none; }
.track-info { flex: 1 1 0; min-width: 0; }
/* Fixed visual order for trailing action buttons — keeps the reveal button
   just left of the kebab menu while the rest of the optional tools buttons
   can still appear/disappear without shifting the cluster unexpectedly.
   DOM order stays as-is; only the visual flex order changes. */
.track-num { order: 0; }
.thumb-wrap.track-thumb-wrap { order: 1; }
.track-info { order: 2; }
.track-bpm-cell { order: 3; }
.track-dl-btn { order: 4; }
.track-pin-btn { order: 5; }
.track-edit-btn { order: 6; }
.track-playlist-btn { order: 7; }
.track-queue-btn { order: 8; }
.track-inline-rating { order: 9; }
.track-move-widget { order: 10; }
.track-reveal-btn { order: 11; }
.track-kebab-btn { order: 12; }

.track-title {
  font-size: 0.92rem; font-weight: 500;
  display: flex; align-items: center; overflow: hidden; gap: 4px;
}
.track-title-text {
  flex: 1 1 0; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  user-select: text;
}
.track-artist {
  font-size: 0.8rem; color: var(--sub); margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

"""
