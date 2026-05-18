"""CSS generation for the streaming player UI."""

from __future__ import annotations


def render_base_css() -> str:
    """Return the shared dark-theme CSS used by both audio and video UIs."""
    return """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #121212; --surface: #1e1e1e; --surface2: #282828;
  --accent: #1db954; --text: #fff; --sub: #b3b3b3;
  --header-h: 56px; --filter-h: 52px; --player-h: 80px;
  --sat: env(safe-area-inset-top, 0px);
  --sab: env(safe-area-inset-bottom, 0px);
  --sal: env(safe-area-inset-left, 0px);
  --sar: env(safe-area-inset-right, 0px);
}
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Header ── */
header {
  height: calc(var(--header-h) + var(--sat));
  padding-top: var(--sat);
  background: var(--surface);
  display: flex; align-items: center; padding-left: max(1rem, var(--sal)); padding-right: max(1rem, var(--sar)); gap: 0.75rem;
  flex-shrink: 0; border-bottom: 1px solid #333;
}
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); user-select: none; }
.logo-home-btn {
  background: none; border: none; font-size: 1.4rem; line-height: 1;
  cursor: pointer; padding: 0 2px; color: inherit; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.logo-home-btn:hover { opacity: 0.75; }
.logo-title {
  font-size: 1.1rem; font-weight: 700; color: var(--accent);
  user-select: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1 1 0; min-width: 0;
}
.offline-close, .offline-action-btn {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; cursor: pointer; padding: 0.4rem 0.8rem;
  font-size: 0.8rem; -webkit-tap-highlight-color: transparent;
}
.offline-close:hover, .offline-action-btn:hover {
  color: var(--accent); border-color: var(--accent);
}
.downloaded-pill {
  font-size: 0.72rem; color: var(--sub); border: 1px solid #3a3a3a;
  border-radius: 999px; padding: 0.28rem 0.55rem; margin-left: 0.45rem;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: color 0.15s, border-color 0.15s;
}
.downloaded-pill:hover, .downloaded-pill.has-downloads { color: var(--accent); border-color: var(--accent); }
.downloaded-pill.is-offline { color: #ffcc00; border-color: #ffcc00; }
/* ── Tools pill + panel ── */
.tools-pill-wrap {
  display: inline-flex; align-items: stretch;
  border: 1px solid #3a3a3a; border-radius: 999px;
  margin-left: 0.35rem; overflow: hidden;
  transition: border-color 0.15s;
}
.tools-pill-wrap:hover, .tools-pill-wrap.has-active { border-color: var(--accent); }
.tools-pill-wrap.has-active .tools-pill { color: var(--accent); }
.tools-pill {
  font-size: 0.72rem; color: var(--sub);
  padding: 0.28rem 0.45rem 0.28rem 0.55rem;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: color 0.15s;
}
.tools-pill:hover { color: var(--accent); }
.tools-pill-toggle {
  background: none; border: none; border-left: 1px solid #3a3a3a;
  padding: 0.28rem 0.5rem; cursor: pointer; color: var(--sub);
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.tools-pill-toggle::before {
  content: ''; display: block; width: 8px; height: 8px;
  border-radius: 50%; border: 1.5px solid currentColor;
  transition: background 0.15s, border-color 0.15s;
}
.tools-pill-toggle:hover { color: var(--accent); background: rgba(79,172,255,0.08); }
.tools-pill-toggle.active::before { background: var(--accent); border-color: var(--accent); }
.tools-pill-toggle.active { color: var(--accent); }
/* Buttongroup (segmented selector) — inline, flex-shrink, no forced width */
.tools-buttongroup {
  display: flex; border: 1px solid #3a3a3a;
  border-radius: 6px; overflow: hidden; flex-shrink: 0; margin-left: 0.5rem;
}
.tools-buttongroup-btn {
  background: none; border: none; color: var(--sub);
  padding: 0.32rem 0; font-size: 0.72rem; cursor: pointer;
  border-right: 1px solid #3a3a3a;
  flex: 1; text-align: center;
  transition: background 0.12s, color 0.12s;
}
.tools-buttongroup-btn:last-child { border-right: none; }
.tools-buttongroup-btn:hover { background: rgba(255,255,255,0.05); color: var(--text); }
.tools-buttongroup-btn.is-active {
  background: var(--accent); color: #000; font-weight: 600;
}
.tools-panel-backdrop {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center;
}
.tools-panel-backdrop[hidden] { display: none; }
.tools-panel {
  background: var(--surface); border: 1px solid #333; border-radius: 12px;
  padding: 1.2rem 1.4rem; width: min(360px, 92vw);
  max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.6);
}
.tools-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem;
}
.tools-panel-header .audit-btn { flex-shrink: 0; }
.tools-panel-title { font-size: 1rem; font-weight: 600; color: var(--text); }
.tools-section-heading {
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--sub); margin: 0.9rem 0 0.25rem; opacity: 0.7;
}
.tools-section-heading:first-of-type { margin-top: 0.2rem; }
.tools-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.6rem 0; border-bottom: 1px solid #222;
}
/* Full-width tools-item: no toggle on right, block layout with buttongroup below */
.tools-item--full {
  display: block; align-items: unset; justify-content: unset;
  padding: 0.6rem 0; border-bottom: 1px solid #222;
}
.tools-item:last-child, .tools-item--full:last-child { border-bottom: none; }
.tools-item-label { font-size: 0.85rem; color: var(--text); }
.tools-item-desc { font-size: 0.7rem; color: var(--sub); margin-top: 2px; }
.tools-toggle {
  position: relative; width: 40px; height: 22px; flex-shrink: 0; margin-left: 0.5rem;
}
.tools-toggle input { opacity: 0; width: 0; height: 0; }
.tools-toggle-track {
  position: absolute; inset: 0; background: #444; border-radius: 11px;
  cursor: pointer; transition: background 0.2s;
}
.tools-toggle-track::after {
  content: ''; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px;
  background: #ccc; border-radius: 50%; transition: transform 0.2s;
}
.tools-toggle input:checked + .tools-toggle-track { background: var(--accent); }
.tools-toggle input:checked + .tools-toggle-track::after { transform: translateX(18px); background: #fff; }
.tools-panel-close {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.4rem 0.9rem; cursor: pointer;
  font-size: 0.85rem; margin-top: 1rem; width: 100%;
  transition: border-color 0.12s, color 0.12s;
}
.tools-panel-close:hover { border-color: var(--text); color: var(--text); }
.tools-activate-all {
  background: var(--accent); border: none; color: #fff;
  border-radius: 6px; padding: 0.4rem 0.9rem; cursor: pointer;
  font-size: 0.85rem; margin-bottom: 1rem; width: 100%;
  transition: opacity 0.12s; font-weight: 600;
}
.tools-activate-all:hover { opacity: 0.85; }
/* When tool mode is ON, button turns to a muted "deactivate" style */
.tools-activate-all--active {
  background: rgba(180,60,60,0.75);
}
/* ── Inline track rating stars ── */
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
  display: grid; grid-template-columns: 1fr 1fr; gap: 2px; flex-shrink: 0;
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
.track-num {
  min-width: 26px; text-align: center; font-size: 0.78rem;
  color: var(--sub); flex-shrink: 0; white-space: nowrap; padding-right: 4px;
}
.track-item.active .num-text { display: none; }
.track-info { flex: 1 1 0; min-width: 0; }
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
.track-meta {
  font-size: 0.68rem; color: #666;
  white-space: nowrap; flex-shrink: 0;
}
/* missing episode placeholder */
.track-item.missing-episode {
  opacity: 0.35; pointer-events: none; min-height: 32px;
  border-bottom: 1px solid #1a1a1a;
}
.track-item.missing-episode .track-title { font-style: italic; }
/* debug-filtered items (shown dimmed with filter reason) */
.track-item.debug-filtered {
  opacity: 0.35; pointer-events: none;
}
.track-item.debug-filtered .track-info { position: relative; }
.debug-reason {
  font-size: 0.7rem; color: #e57373; font-style: italic; margin-top: 2px;
}
/* hidden-shown: normally filtered by MIN_RATING, visible via toggle */
.track-item--hidden-shown {
  opacity: 0.4; background: rgba(110,110,110,0.05);
  filter: saturate(0.2);
}
.track-item--hidden-shown:hover { opacity: 0.58; filter: saturate(0.35); }
.track-item--hidden-shown .track-title-text { color: var(--sub); }
.track-item--hidden-shown .track-artist { color: #555; }
/* Keep the "ausgeblendet" indicator even in active/playing state */
.track-item--hidden-shown.active { background: rgba(24,51,32,0.55); opacity: 0.5; }
/* filter-hidden chip: stable width so click target doesn't shift */
#filter-hidden { min-width: 8.5rem; justify-content: flex-start; }
/* moved ghost: file was moved this session — shown dimmed with target hint */
.track-item--moved { opacity: 0.32; cursor: default; pointer-events: none; }
.track-item--moved:hover { opacity: 0.42; }
.moved-hint {
  display: inline-flex; align-items: center; font-size: 0.6rem;
  color: #fff; background: rgba(60,120,220,0.55);
  padding: 1px 6px; border-radius: 8px; margin-left: 6px;
  vertical-align: middle; font-weight: 500; white-space: nowrap; letter-spacing: 0.01em;
}
/* deleted ghost: file was soft-deleted this session — shown dimmed with strikethrough */
.track-item--deleted { opacity: 0.35; cursor: default; pointer-events: none; }
.track-item--deleted .track-title-text { text-decoration: line-through; color: var(--sub); }
.deleted-badge {
  display: inline-flex; align-items: center; font-size: 0.6rem;
  color: #fff; background: rgba(180,60,60,0.65);
  padding: 1px 5px; border-radius: 8px; margin-left: 5px;
  vertical-align: middle; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap;
  flex-shrink: 0;
}
/* Deleted item in dupe panel */
.dupe-group-item--deleted { opacity: 0.35; cursor: default; pointer-events: none; }
.dupe-group-item--deleted .dupe-group-item-title { text-decoration: line-through; }
.hidden-badge {
  display: inline-flex; align-items: center; font-size: 0.6rem;
  color: #fff; background: rgba(120,120,120,0.7);
  padding: 1px 5px; border-radius: 8px; margin-left: 5px;
  vertical-align: middle; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap;
  flex-shrink: 0;
}
/* refresh-info label in the header */
.refresh-info {
  font-size: 0.68rem; color: var(--sub); margin-left: 0.5rem; white-space: nowrap;
}
/* conversion badge for non-native formats */
.convert-badge {
  display: inline-block; font-size: 0.65rem; color: #f5a623;
  margin-left: 5px; vertical-align: middle; opacity: 0.8;
  title: attr(data-tip);
}
.track-dl-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 30px; height: 30px;
  cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1; font-size: 0.7rem;
}
.track-dl-btn svg { width: 16px; height: 16px; fill: currentColor; pointer-events: none; }
.track-dl-btn:hover { color: var(--accent); border-color: var(--accent); }
.track-dl-btn.cached {
  color: var(--accent); border-color: var(--accent);
  background: rgba(29, 185, 84, 0.12);
}
.track-dl-btn.downloading {
  color: #ffcc00; border-color: #ffcc00; font-size: 0.65rem;
  cursor: pointer;
}
@keyframes dl-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.track-dl-btn.downloading { animation: dl-pulse 1.2s ease-in-out infinite; }
.track-pin-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-pin-btn svg { width: 14px; height: 14px; fill: currentColor; pointer-events: none; }
.track-pin-btn:hover { color: var(--accent); border-color: var(--accent); }
.track-pin-btn.pinned {
  color: var(--accent); border-color: var(--accent);
  background: rgba(29, 185, 84, 0.12);
}
.track-edit-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-edit-btn svg { width: 14px; height: 14px; fill: currentColor; pointer-events: none; }
.track-edit-btn:hover { color: var(--accent); border-color: var(--accent); }
/* ── Edit metadata modal ── */
.edit-modal-backdrop {
  position: fixed; inset: 0; z-index: 60; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.edit-modal-backdrop[hidden] { display: none; }
.edit-modal {
  width: min(480px, 100%); background: var(--surface);
  border: 1px solid #444; border-radius: 14px;
  padding: 1.25rem 1.25rem 1rem;
  box-shadow: 0 20px 48px rgba(0,0,0,0.55);
}
.edit-modal-heading { font-size: 1rem; font-weight: 700; margin-bottom: 1rem; }
.edit-field { margin-bottom: 0.75rem; }
.edit-field label { display: block; font-size: 0.78rem; color: var(--sub); margin-bottom: 0.25rem; }
.edit-field input {
  width: 100%; box-sizing: border-box;
  background: var(--surface2); border: 1px solid #444; border-radius: 6px;
  color: var(--text); font-size: 0.9rem; padding: 0.45rem 0.6rem;
  outline: none; transition: border-color 0.15s;
}
.edit-field input:focus { border-color: var(--accent); }
.edit-modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; }
.edit-modal-cancel {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.4rem 0.9rem;
  cursor: pointer; font-size: 0.85rem; transition: border-color 0.12s, color 0.12s;
}
.edit-modal-cancel:hover { border-color: var(--text); color: var(--text); }
.edit-modal-save {
  background: var(--accent); color: #000; border: none; border-radius: 6px;
  padding: 0.4rem 0.9rem; cursor: pointer; font-size: 0.85rem; font-weight: 600;
  transition: background 0.12s;
}
.edit-modal-save:hover { background: #1ed760; }
.edit-modal-save:disabled { opacity: 0.6; cursor: not-allowed; }
/* rating inside edit modal */
.edit-modal-rating { display: flex; gap: 4px; padding: 4px 0; }
.edit-modal-rating-star {
  background: none; border: none; color: #555; cursor: pointer;
  padding: 2px; font-size: 0; line-height: 0; transition: color 0.1s;
}
.edit-modal-rating-star svg { width: 22px; height: 22px; }
.edit-modal-rating-star.active { color: #ffd700; }
.edit-modal-rating-star.hover { color: #ffd700; }
/* ── Playlist add button (per track) ── */
.track-playlist-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-playlist-btn svg { width: 14px; height: 14px; fill: none; stroke: currentColor; pointer-events: none; }
.track-playlist-btn:hover { color: var(--accent); border-color: var(--accent); }
/* ── Playlist drag-and-drop reorder ── */
.track-item.dragging { opacity: 0.25; pointer-events: none; }
.track-item.drag-over-above { box-shadow: 0 3px 0 0 var(--accent) inset; }
.track-item.drag-over-below { box-shadow: 0 -3px 0 0 var(--accent) inset; }
.playlist-drag-ghost {
  position: fixed; z-index: 200; pointer-events: none;
  background: var(--surface2); border: 1px solid var(--accent);
  border-radius: 8px; padding: 0.5rem 1rem; opacity: 0.92;
  font-size: 0.88rem; color: var(--fg); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; max-width: 280px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  display: flex; align-items: center; gap: 0.5rem;
}
.playlist-drag-ghost img { width: 32px; height: 32px; border-radius: 4px; object-fit: cover; }
body.playlist-dragging { user-select: none; -webkit-user-select: none; }
body.playlist-dragging .track-list { overflow: visible; }
/* ── Playlist modal (add-to / create) ── */
.playlist-modal-backdrop {
  position: fixed; inset: 0; z-index: 60; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.playlist-modal-backdrop[hidden] { display: none; }
.playlist-modal {
  width: min(420px, 100%); background: var(--surface);
  border: 1px solid #444; border-radius: 14px;
  padding: 1.25rem 1.25rem 1rem;
  box-shadow: 0 20px 48px rgba(0,0,0,0.55);
  max-height: 70vh; display: flex; flex-direction: column;
}
.playlist-modal-heading { font-size: 1rem; font-weight: 700; margin-bottom: 0.75rem; }
.playlist-modal-list {
  list-style: none; margin: 0; padding: 0; overflow: auto;
  flex: 1 1 auto; min-height: 0;
}
.playlist-modal-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.5rem; border-radius: 8px; cursor: pointer;
  transition: background 0.12s;
}
.playlist-modal-item:hover { background: var(--surface2); }
.playlist-modal-item-name { flex: 1; font-size: 0.9rem; }
.playlist-modal-item-count { font-size: 0.75rem; color: var(--sub); }
.playlist-modal-new {
  display: flex; gap: 0.4rem; margin-top: 0.75rem; padding-top: 0.75rem;
  border-top: 1px solid #333;
}
.playlist-modal-new input {
  flex: 1; background: var(--surface2); border: 1px solid #444; border-radius: 6px;
  color: var(--text); font-size: 0.85rem; padding: 0.4rem 0.6rem; outline: none;
}
.playlist-modal-new input:focus { border-color: var(--accent); }
.playlist-modal-new button {
  background: var(--accent); color: #000; border: none; border-radius: 6px;
  padding: 0.4rem 0.75rem; cursor: pointer; font-size: 0.85rem; font-weight: 600;
}
.playlist-modal-close {
  display: flex; justify-content: flex-end; margin-top: 0.75rem;
}
.playlist-modal-close button {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.35rem 0.75rem; cursor: pointer; font-size: 0.8rem;
}
.playlist-modal-close button:hover { border-color: var(--text); color: var(--text); }
/* ── Playlist library panel (removed — playlists as pseudo-folders) ── */
/* ── Playlist pseudo-folder cards ── */
.playlist-folder-card { position: relative; }
.playlist-folder-icon {
  width: 100%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  background: var(--surface2); border-radius: 8px; color: var(--sub);
}
.playlist-folder-icon svg { width: 36px; height: 36px; }
.playlist-new-card { opacity: 0.65; border: 2px dashed #444; }
.playlist-new-card:hover { opacity: 1; border-color: var(--accent); }
/* Smart playlist badge — small lightning bolt overlay on the IC_PLAYLIST logo. */
.playlist-folder-icon { position: relative; }
.smart-pl-badge {
  position: absolute; right: -4px; bottom: -4px;
  width: 18px; height: 18px;
  background: var(--accent); color: #000; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 0 2px var(--surface2);
}
.smart-pl-badge svg { width: 11px; height: 11px; }
.smart-playlist-card .folder-name::after {
  content: ''; /* badge is on the icon, no extra text */
}
.playlist-folder-refresh {
  position: absolute; top: 6px; left: 6px;
  width: 24px; height: 24px; border: none; border-radius: 50%;
  background: rgba(0,0,0,0.5); color: var(--text);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; opacity: 0.7; padding: 0;
}
.playlist-folder-refresh:hover { opacity: 1; background: var(--accent); color: #000; }
.smart-new-card .tools-row-icon { color: var(--accent); }

/* Smart Playlist Editor Modal */
.smart-editor-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.smart-editor-modal {
  background: var(--surface); color: var(--text);
  border-radius: 10px; padding: 0; min-width: 320px; max-width: 560px;
  width: 90vw; max-height: 90vh; display: flex; flex-direction: column;
  box-shadow: 0 12px 32px rgba(0,0,0,0.5);
}
.smart-editor-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--surface2); font-weight: 600;
}
.smart-editor-header svg { width: 16px; height: 16px; vertical-align: middle; margin-right: 6px; color: var(--accent); }
.smart-editor-close {
  background: none; border: none; color: var(--sub); font-size: 1.5rem;
  cursor: pointer; line-height: 1; padding: 0 4px;
}
.smart-editor-body { padding: 14px 16px; overflow-y: auto; flex: 1; }
.smart-editor-label {
  display: block; margin: 8px 0; font-size: 0.88rem; color: var(--sub);
}
.smart-editor-label input {
  display: block; width: 100%; margin-top: 4px; padding: 6px 8px;
  background: var(--surface2); color: var(--text); border: 1px solid #444; border-radius: 4px;
  box-sizing: border-box;
}
.smart-editor-match {
  display: flex; flex-direction: column; gap: 4px; margin: 10px 0; padding: 8px;
  background: var(--surface2); border-radius: 6px;
}
.smart-editor-match label { font-size: 0.88rem; cursor: pointer; }
.smart-editor-rules { display: flex; flex-direction: column; gap: 6px; margin: 10px 0; }
.smart-rule-row {
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  padding: 6px; background: var(--surface2); border-radius: 6px;
}
.smart-rule-row select, .smart-rule-row input {
  background: var(--bg, #1a1a1a); color: var(--text);
  border: 1px solid #444; border-radius: 4px; padding: 4px 6px;
  font-size: 0.85rem;
}
.smart-rule-row select { min-width: 110px; }
.smart-rule-row input { flex: 1; min-width: 80px; }
.smart-rule-pl-list {
  flex: 1 1 100%; display: flex; flex-direction: column; gap: 2px;
  max-height: 120px; overflow-y: auto;
  padding: 4px 6px; background: var(--bg, #1a1a1a);
  border: 1px solid #444; border-radius: 4px;
}
.smart-rule-pl-opt {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.85rem; cursor: pointer; padding: 2px 0;
}
.smart-rule-pl-opt input[type="checkbox"] {
  flex: 0 0 auto; min-width: auto; margin: 0;
}
.smart-rule-empty {
  flex: 1; font-size: 0.85rem; color: var(--sub); font-style: italic;
}
.smart-rule-del {
  background: none; border: none; color: var(--sub); cursor: pointer;
  font-size: 1.2rem; line-height: 1; padding: 0 6px;
}
.smart-rule-del:hover { color: #e44; }
.smart-editor-add {
  background: var(--surface2); color: var(--text); border: 1px dashed #555;
  border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.85rem;
  width: 100%;
}
.smart-editor-add:hover { border-color: var(--accent); color: var(--accent); }
.smart-editor-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--surface2);
}
.smart-editor-cancel, .smart-editor-save {
  padding: 7px 14px; border-radius: 5px; border: none; cursor: pointer; font-size: 0.9rem;
}
.smart-editor-cancel { background: var(--surface2); color: var(--text); }
.smart-editor-save { background: var(--accent); color: #000; font-weight: 600; }
/* Compact "tools row" on root: Downloaded + Neue Playlist + Titel.
   Spans full width of the folder-grid (CSS grid). */
.playlist-tools-row {
  grid-column: 1 / -1;
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;
}
.tools-row-item {
  flex: 1 1 0; min-width: 110px;
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  background: var(--surface2); border: 1px solid #333; color: var(--text);
  cursor: pointer; font: inherit; text-align: left;
  transition: border-color 0.12s, background 0.12s;
}
.tools-row-item:hover { border-color: var(--accent); background: var(--surface); }
.tools-row-item.playlist-new-card { opacity: 0.75; border: 1px dashed #444; background: transparent; }
.tools-row-item.playlist-new-card:hover { opacity: 1; border-color: var(--accent); background: var(--surface2); }
.tools-row-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; color: var(--sub); flex-shrink: 0;
}
.tools-row-icon svg { width: 18px; height: 18px; }
.tools-row-label {
  flex: 1 1 auto; font-size: 0.85rem; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.tools-row-count {
  font-size: 0.75rem; color: var(--sub); flex-shrink: 0;
  padding: 1px 6px; border-radius: 8px; background: rgba(255,255,255,0.05);
}
.tools-row-count:empty { display: none; }
.playlist-folder-del {
  position: absolute; top: 6px; right: 6px; z-index: 2;
  background: rgba(0,0,0,0.55); border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 24px; height: 24px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0.6; transition: opacity 0.15s, color 0.12s, border-color 0.12s;
}
.playlist-folder-card:hover .playlist-folder-del { opacity: 1; }
.playlist-folder-del:hover { color: #ff5555; border-color: #ff5555; opacity: 1; }
.track-thumb {
  width: 40px; height: 40px; border-radius: 4px; object-fit: cover;
  flex-shrink: 0; background: var(--surface2);
}
/* ── Rating bar overlay on thumbnails ── */
.thumb-wrap {
  position: relative; flex-shrink: 0; overflow: hidden;
}
.thumb-wrap.track-thumb-wrap {
  width: 40px; height: 40px; border-radius: 4px;
}
.thumb-wrap.track-thumb-wrap .track-thumb {
  width: 100%; height: 100%; border-radius: 0;
}
.thumb-wrap.folder-thumb-wrap {
  width: 100%; border-radius: 6px; margin-bottom: 0.4rem;
}
.thumb-wrap.folder-thumb-wrap .folder-thumb {
  margin-bottom: 0; border-radius: 0;
}
.rating-bar {
  position: absolute; bottom: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, #ff8800, #ffcc00);
  opacity: 0.85; pointer-events: none;
  border-radius: 0 1px 0 0;
}
.folder-grid.list-mode .thumb-wrap.folder-thumb-wrap {
  width: 40px; height: 40px; border-radius: 4px;
  margin-bottom: 0; flex-shrink: 0;
}
.folder-grid.list-mode .thumb-wrap.folder-thumb-wrap .folder-thumb {
  width: 100%; height: 100%; aspect-ratio: auto; border-radius: 0;
}
.folder-thumb {
  width: 100%; aspect-ratio: 1; border-radius: 6px; object-fit: cover;
  margin-bottom: 0.4rem; background: var(--surface2);
}
.folder-grid.list-mode .folder-thumb {
  width: 40px; height: 40px; aspect-ratio: auto; border-radius: 4px;
  margin-bottom: 0; flex-shrink: 0;
}
.empty-hint { text-align: center; color: var(--sub); padding: 3rem 1rem; font-size: 0.9rem; }

/* ── Bottom player bar — shared ── */
.player-bar {
  padding-bottom: var(--sab);
  background: var(--surface);
  border-top: 1px solid #333; flex-shrink: 0;
  position: relative; z-index: 100;
}
.player-info { min-width: 0; }
.player-title {
  font-size: 0.85rem; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.player-artist {
  font-size: 0.75rem; color: var(--sub);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.player-controls { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
.ctrl-btn {
  background: none; border: none; color: var(--text);
  cursor: pointer; line-height: 1;
  padding: 0.35rem; border-radius: 50%; transition: color 0.12s;
  -webkit-tap-highlight-color: transparent;
  display: flex; align-items: center; justify-content: center;
}
.ctrl-btn svg { width: 18px; height: 18px; fill: currentColor; pointer-events: none; }
.ctrl-btn:hover { color: var(--accent); }
.ctrl-btn.play-pause {
  background: var(--accent); color: #000;
  width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;
}
.ctrl-btn.play-pause svg { width: 16px; height: 16px; }
.ctrl-btn.play-pause:hover { background: #1ed760; }
.ctrl-btn.pip-btn { position: relative; }
.ctrl-btn.pip-btn svg { width: 16px; height: 16px; }
.ctrl-btn.pip-btn.active { color: var(--accent); }
.ctrl-btn.pip-btn[hidden] { display: none; }
/* Shuffle button active states */
.ctrl-btn.shuffle-btn.shuffle-active { color: var(--accent); }
.ctrl-btn.shuffle-btn.shuffle-weighted { color: var(--accent); background: rgba(29, 185, 84, 0.15); border-radius: 50%; }
/* Repeat button active states */
.ctrl-btn.repeat-btn.repeat-active { color: var(--accent); }
.ctrl-btn.repeat-btn.repeat-one { color: var(--accent); background: rgba(29, 185, 84, 0.15); border-radius: 50%; }
/* Rating stars in player */
.player-rating { display: flex; gap: 1px; margin-top: 2px; }
.player-rating[hidden] { display: none; }
.player-rating-star { background: none; border: none; padding: 1px; cursor: pointer; color: #555; width: 15px; height: 15px; flex-shrink: 0; transition: color 0.1s; -webkit-tap-highlight-color: transparent; display: flex; align-items: center; justify-content: center; }
.player-rating-star svg { width: 12px; height: 12px; }
.player-rating-star.active { color: #ffd700; }
.player-rating-star.hover { color: #ffd700; }
.time-label { font-size: 0.68rem; color: var(--sub); flex-shrink: 0; min-width: 2.2rem; }
.time-label.end { text-align: left; }

/* ── Classic player bar — single row, wraps progress below controls on small screens ── */
.player-bar.classic {
  display: flex; flex-wrap: wrap; align-items: center;
  min-height: calc(var(--player-h) + var(--sab));
  padding-left: max(0.75rem, var(--sal)); padding-right: max(0.75rem, var(--sar));
  padding-bottom: max(0.4rem, var(--sab));
  gap: 0.65rem;
}
.player-bar.classic .player-info { flex: 0 0 150px; }
.player-bar.classic .progress-wrap {
  flex: 1 1 160px; min-width: 0; display: flex; align-items: center; gap: 0.4rem;
}
.player-bar.classic .progress-track {
  flex: 1 1 0; position: relative; min-width: 0;
  height: 28px;
  background: rgba(255,255,255,0.035);
  border: 1px solid #282828;
  border-radius: 6px;
  cursor: pointer;
}
.player-bar.classic .waveform-canvas {
  display: block; width: 100%; height: 100%; border-radius: 5px;
}
.player-bar.classic input[type=range] {
  -webkit-appearance: none; appearance: none;
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; opacity: 0;
  cursor: pointer; margin: 0; z-index: 2;
  background: transparent;
}
.player-bar.classic input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 1px; height: 1px; background: transparent;
}

/* ── Waveform player bar — two rows ── */
.player-bar.waveform {
  display: flex; flex-direction: column;
}
.player-bar-top {
  display: flex; align-items: center;
  padding: 0.4rem max(0.75rem, var(--sal)) 0 max(0.75rem, var(--sar));
  gap: 0.65rem;
}
.player-bar-top .player-info { flex: 0 1 auto; max-width: 45%; }
.player-bar-top .player-controls { flex: 1 1 0; justify-content: center; }
.player-bar.waveform .progress-wrap {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.25rem max(0.75rem, var(--sal)) 0.5rem max(0.75rem, var(--sar));
}
.player-bar.waveform .progress-track {
  flex: 1 1 0; position: relative; height: 48px; min-width: 0; cursor: pointer;
}
.player-bar.waveform .progress-track.video-mode { height: 28px; }
.waveform-canvas {
  display: block; width: 100%; height: 100%; border-radius: 4px;
}
.player-bar.waveform .progress-track input[type=range] {
  -webkit-appearance: none; appearance: none;
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; opacity: 0;
  cursor: pointer; margin: 0; z-index: 2;
  background: transparent;
}
.player-bar.waveform .progress-track input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 1px; height: 1px; background: transparent;
}

/* ── Video thumbnail preview ── */
.thumb-preview {
  display: none; position: absolute; bottom: calc(100% + 8px);
  transform: translateX(-50%);
  background: var(--surface2); border: 2px solid #444;
  border-radius: 6px; padding: 4px; z-index: 100;
  pointer-events: none;
}
.thumb-preview.visible { display: block; }
.thumb-preview canvas {
  display: block; max-width: 200px; border-radius: 3px;
}
.thumb-time {
  display: block; text-align: center; font-size: 0.72rem;
  color: var(--text); margin-top: 3px;
}

/* ── Folder grid ── */
.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem; padding: 1rem max(1rem, var(--sar)) 1rem max(1rem, var(--sal));
  overflow-y: auto; flex: 1 1 0;
}
.folder-card {
  background: var(--surface2); border-radius: 8px;
  padding: 1rem; cursor: pointer; position: relative;
  transition: background 0.15s, transform 0.1s;
}
.folder-card:hover { background: #333; transform: translateY(-2px); }
.folder-icon { font-size: 2rem; margin-bottom: 0.3rem; }
.folder-name {
  font-size: 0.95rem; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.folder-count { font-size: 0.78rem; color: var(--sub); margin-top: 2px; }
.folder-play-btn {
  position: absolute; bottom: 0.75rem; right: 0.75rem;
  background: var(--accent); color: #000; border: none;
  border-radius: 50%; width: 36px; height: 36px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.15s;
}
.folder-play-btn svg { width: 16px; height: 16px; fill: currentColor; pointer-events: none; }
/* Touch devices: always show play button at low opacity */
@media (hover: none) {
  .folder-play-btn { opacity: 0.55; }
}
/* Mouse/trackpad: reveal on hover */
@media (hover: hover) {
  .folder-card:hover .folder-play-btn { opacity: 1; }
}
.folder-play-btn:hover { background: #1ed760; }
.back-btn {
  background: var(--surface2); border: 1px solid #444; color: var(--accent);
  cursor: pointer; padding: 0.3rem 0.5rem;
  border-radius: 6px; display: none;
  transition: background 0.12s, color 0.12s;
  line-height: 0;
}
.back-btn svg { width: 18px; height: 18px; fill: currentColor; }
.back-btn:hover { background: #333; color: #1ed760; }
.play-all-btn {
  background: var(--accent); color: #000; border: none;
  border-radius: 20px; padding: 0.3rem 0.8rem; cursor: pointer;
  font-size: 0.8rem; font-weight: 600; display: none;
  transition: background 0.12s; white-space: nowrap;
  align-items: center; gap: 4px;
}
.play-all-btn svg { width: 14px; height: 14px; fill: currentColor; display: inline-block; vertical-align: middle; }
.play-all-btn:hover { background: #1ed760; }
.file-card .folder-icon { font-size: 1.6rem; }
.view-hidden { display: none !important; }

/* ── Breadcrumb navigation ── */
.breadcrumb {
  display: none; padding: 0.4rem max(1rem, var(--sal)) 0.4rem max(1rem, var(--sar));
  background: var(--surface);
  border-bottom: 1px solid #333; font-size: 0.82rem; flex-shrink: 0;
  overflow-x: auto; white-space: nowrap;
}
.breadcrumb.visible { display: block; }
.breadcrumb a {
  color: var(--accent); text-decoration: none; cursor: pointer;
}
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb .sep { color: var(--sub); margin: 0 0.4rem; }
.breadcrumb .current { color: var(--text); font-weight: 500; }

/* ── View toggle (list / grid) ── */
.view-toggle {
  background: none; border: 1px solid #444; color: var(--sub);
  border-radius: 4px; padding: 0.25rem 0.4rem; cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0; line-height: 0;
}
.view-toggle svg { width: 16px; height: 16px; fill: currentColor; }
.view-toggle:hover { color: var(--accent); border-color: var(--accent); }
.view-toggle.view-toggle-locked { opacity: 0.45; cursor: default; pointer-events: none; }
.audit-btn {
  background: none; border: 1px solid #333; color: var(--sub);
  border-radius: 4px; padding: 0.25rem 0.4rem; cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0; line-height: 0; text-decoration: none; display: inline-flex; align-items: center;
}
.audit-btn svg { width: 16px; height: 16px; }
.audit-btn:hover { color: var(--accent); border-color: var(--accent); }

/* ── Refresh catalog card in tools-row ── */
.refresh-catalog-card {
  flex: 0 0 auto; min-width: unset;
  width: 40px; height: 40px;
  padding: 0; justify-content: center;
  margin-right: 6px;
  opacity: 0.75; border: 1px dashed #444; background: transparent;
}
.refresh-catalog-card:hover { opacity: 1; border-color: var(--accent); background: var(--surface2); }
.refresh-catalog-card.spinning .tools-row-icon svg { animation: spin 0.8s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
/* ── Global Tools button in tools panel ── */
.tools-global-refresh-btn {
  flex-shrink: 0; margin-left: 0.5rem;
  background: none; border: 1px solid #3a3a3a; border-radius: 6px;
  color: var(--sub); font-size: 0.8rem; padding: 0.4rem 0.8rem;
  cursor: pointer; text-align: center; white-space: nowrap;
  transition: color 0.12s, border-color 0.12s;
}
.tools-global-refresh-btn:hover { color: var(--accent); border-color: var(--accent); }

/* ── Folder list mode ── */
.folder-grid.list-mode {
  display: flex; flex-direction: column; gap: 0; padding: 0;
}
.folder-grid.list-mode .folder-card {
  border-radius: 0; padding: 0.6rem 1rem;
  display: flex; align-items: center; gap: 0.75rem;
  border-bottom: 1px solid #282828;
}
.folder-grid.list-mode .folder-card:hover { transform: none; }
.folder-grid.list-mode .folder-icon { font-size: 1.3rem; margin-bottom: 0; flex-shrink: 0; }
.folder-grid.list-mode .folder-name { font-size: 0.9rem; flex: 1 1 0; }
.folder-grid.list-mode .folder-count { margin-top: 0; flex-shrink: 0; }
.folder-grid.list-mode .folder-play-btn {
  position: static; opacity: 0; width: 30px; height: 30px; font-size: 0.8rem;
  flex-shrink: 0;
}
@media (hover: none) {
  .folder-grid.list-mode .folder-play-btn { opacity: 0.55; }
}
@media (hover: hover) {
  .folder-grid.list-mode .folder-card:hover .folder-play-btn { opacity: 1; }
}

@media (max-width: 480px) {
  .player-info { flex: 0 0 90px; }
  .folder-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
}
/* toast notification */
.ht-toast {
  position: fixed; bottom: 5rem; left: 50%; transform: translateX(-50%);
  background: #e53935; color: #fff; padding: 0.6rem 1.2rem;
  border-radius: 8px; font-size: 0.85rem; z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5); opacity: 0;
  transition: opacity 0.3s; pointer-events: none;
  max-width: 90vw; text-align: center; word-break: break-word;
}
.ht-toast.visible { opacity: 1; }
/* indexing toast (top-right info notification) */
.ht-indexing-toast {
  position: fixed; top: 0.75rem; right: 0.75rem;
  background: rgba(50,50,50,0.92); color: #ccc; padding: 0.45rem 0.9rem;
  border-radius: 6px; font-size: 0.78rem; z-index: 9998;
  box-shadow: 0 2px 8px rgba(0,0,0,0.35); opacity: 0;
  transition: opacity 0.3s; pointer-events: none;
  max-width: 320px; text-align: left; word-break: break-word;
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.06);
}
.ht-indexing-toast.visible { opacity: 1; }
.ht-indexing-toast .spinner {
  display: inline-block; width: 10px; height: 10px;
  border: 2px solid #666; border-top-color: #ccc;
  border-radius: 50%; animation: ht-spin 0.8s linear infinite;
  margin-right: 6px; vertical-align: middle;
}
@keyframes ht-spin { to { transform: rotate(360deg); } }

/* ── Lyrics panel ── */
.lyrics-panel {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: var(--surface); border-top: 1px solid #333;
  z-index: 500; display: flex; flex-direction: column;
  max-height: 55vh; transform: translateY(100%);
  transition: transform 0.28s cubic-bezier(.4,0,.2,1);
}
.lyrics-panel.visible { transform: translateY(0); }
.lyrics-panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.6rem 1rem 0.4rem; border-bottom: 1px solid #2a2a2a; flex-shrink: 0;
}
.lyrics-panel-title { font-size: 0.82rem; font-weight: 600; color: var(--sub); text-transform: uppercase; letter-spacing: .06em; }
.lyrics-close-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  font-size: 1.2rem; line-height: 1; padding: 0.2rem 0.4rem;
  border-radius: 4px; transition: color 0.12s;
}
.lyrics-close-btn:hover { color: var(--accent); }
.lyrics-body {
  overflow-y: auto; padding: 0.75rem 1rem 1.5rem;
  flex: 1 1 0; -webkit-overflow-scrolling: touch;
}
.lyrics-text {
  white-space: pre-wrap; font-size: 0.9rem; line-height: 1.75;
  color: var(--text); font-family: inherit;
}
.lyrics-empty { color: var(--sub); font-size: 0.85rem; font-style: italic; }
.lyrics-loading { color: var(--sub); font-size: 0.85rem; }
.ctrl-btn.lyrics-btn.has-lyrics { color: var(--accent); }

/* ── Queue panel ── */
.queue-panel {
  position: fixed;
  left: 0; right: 0;
  /* bottom set dynamically by _syncQueueBottom() */
  bottom: 0;
  background: var(--surface); border-top: 1px solid #333;
  border-radius: 12px 12px 0 0;
  z-index: 500; display: flex; flex-direction: column;
  overflow: hidden;
  /* max-height set dynamically by _syncQueueBottom() — user-resizable via drag handle */
  max-height: 70vh;
  box-shadow: 0 -8px 32px rgba(0,0,0,0.55);
  clip-path: inset(100% 0 0 0); pointer-events: none;
  transition: clip-path 0.3s cubic-bezier(.4,0,.2,1);
}
.queue-panel.visible { clip-path: inset(0); pointer-events: auto; }
.queue-panel.dragging { transition: none; }
.queue-drag-handle {
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  padding: 6px 0 2px; cursor: grab; touch-action: none; user-select: none; -webkit-user-select: none;
}
.queue-drag-handle:active { cursor: grabbing; }
.queue-drag-handle-bar {
  width: 36px; height: 4px; border-radius: 2px; background: #555;
  transition: background 0.15s;
}
.queue-drag-handle:hover .queue-drag-handle-bar { background: var(--accent); }
.queue-panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.6rem 1rem 0.4rem; border-bottom: 1px solid #2a2a2a; flex-shrink: 0;
}
.queue-panel-title { font-size: 0.82rem; font-weight: 600; color: var(--sub); text-transform: uppercase; letter-spacing: .06em; }
.queue-close-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  font-size: 1.2rem; line-height: 1; padding: 0.2rem 0.4rem;
  border-radius: 4px; transition: color 0.12s;
}
.queue-close-btn:hover { color: var(--accent); }
.queue-body {
  overflow-y: auto; padding: 0; flex: 1 1 auto; min-height: 0; -webkit-overflow-scrolling: touch;
}
.queue-list { list-style: none; margin: 0; padding: 0; }
.queue-item {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.5rem 1rem; border-bottom: 1px solid #222; cursor: default;
}
.queue-item:hover { background: var(--surface2); }
.queue-item-thumb {
  width: 36px; height: 36px; border-radius: 4px; object-fit: cover; flex-shrink: 0;
}
.queue-item-info { flex: 1; min-width: 0; }
.queue-item-title {
  font-size: 0.85rem; color: var(--text); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.queue-item-artist {
  font-size: 0.72rem; color: var(--sub); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.queue-item-remove {
  background: none; border: none; color: var(--sub); cursor: pointer;
  padding: 0.3rem; border-radius: 4px; flex-shrink: 0; display: flex;
  align-items: center; justify-content: center;
}
.queue-item-remove svg { width: 16px; height: 16px; }
.queue-item-remove:hover { color: #ff5555; }
.queue-empty { color: var(--sub); font-size: 0.85rem; padding: 1.5rem 1rem; text-align: center; font-style: italic; }
.ctrl-btn.queue-btn { position: relative; }
.ctrl-btn.queue-btn svg { width: 16px; height: 16px; }
.queue-badge {
  position: absolute; top: 0; right: 0;
  background: var(--accent); color: #000; font-size: 0.6rem; font-weight: 700;
  min-width: 14px; height: 14px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px; pointer-events: none;
}
.queue-badge:empty { display: none; }
.track-queue-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  padding: 0.25rem; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; border-radius: 4px; transition: color 0.12s;
}
.track-queue-btn svg { width: 16px; height: 16px; }
.track-queue-btn:hover { color: var(--accent); }
.track-queue-btn.in-queue { color: var(--accent); }
.ctrl-btn.queue-btn.queue-active { color: var(--accent); }
.queue-item.drag-over-above { box-shadow: 0 3px 0 0 var(--accent) inset; }
.queue-item.drag-over-below { box-shadow: 0 -3px 0 0 var(--accent) inset; }

/* ── Video overlay (video-mode only) ── */
/* ── Video overlay: 3-zone flex column (header | video | controls) ── */
.video-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  /* Explicit dimensions fix iOS Safari: position:fixed inside body{overflow:hidden;display:flex}
     gets clipped to the flex container. Setting width/height explicitly + will-change bypasses this. */
  width: 100vw;
  height: 100vh; height: 100dvh;
  background: #000; z-index: 500;
  display: flex; flex-direction: column;
  will-change: transform; /* new compositor layer → no iOS clipping */
}
.video-overlay.view-hidden { display: none; }
/* Zone 1: header bar — proper flex item (not absolute) so it reserves real height */
.video-overlay-header {
  display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;
  height: calc(var(--header-h) + env(safe-area-inset-top, 0px));
  padding-top: env(safe-area-inset-top, 0px);
  padding-left: max(0.75rem, env(safe-area-inset-left, 0.75rem));
  padding-right: max(0.75rem, env(safe-area-inset-right, 0.75rem));
  background: var(--surface);
  border-bottom: 1px solid #333;
  z-index: 2;
}
.video-overlay-close {
  background: none; border: none; color: #fff;
  border-radius: 50%; width: 36px; height: 36px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.video-overlay-close:hover { background: rgba(255,255,255,0.1); }
.video-overlay-close svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
.video-overlay-title-text {
  flex: 1; font-size: 1rem; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff;
}
.video-fs-btn {
  background: none; border: none; color: #fff;
  border-radius: 50%; width: 36px; height: 36px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.video-fs-btn:hover { background: rgba(255,255,255,0.1); }
.video-fs-btn svg { width: 18px; height: 18px; }
/* Zone 2: video — fills all remaining space between header and controls */
.video-wrap {
  flex: 1 1 0; min-height: 0; overflow: hidden;
  background: #000;
}
.video-wrap video {
  /* Fill entire wrap, scale content to fit while keeping aspect ratio.
     width/height:100% on a flex item with definite container height works correctly
     now that the legacy #player{max-height:35vh} override has been removed.
     object-fit:contain handles letterbox/pillarbox automatically. */
  display: block;
  width: 100%; height: 100%;
  object-fit: contain;
}
/* Zone 3: controls bar — anchored at bottom */
.video-overlay .player-bar {
  flex-shrink: 0;
  background: var(--surface);
  border-top: 1px solid #333;
  padding-bottom: max(var(--sab), env(safe-area-inset-bottom, 0px));
}
.video-overlay .player-bar.view-hidden { display: none; }
/* ── Video mini bar (compact strip when overlay is closed) ── */
.video-mini-bar {
  background: var(--surface); border-top: 1px solid #333;
  display: flex; align-items: center; gap: 0.65rem;
  min-height: var(--player-h); flex-shrink: 0; z-index: 100;
  padding: 0.4rem max(0.75rem, env(safe-area-inset-right, 0.75rem)) calc(0.4rem + var(--sab)) max(0.75rem, env(safe-area-inset-left, 0.75rem));
  cursor: pointer;
}
.video-mini-bar[hidden] { display: none; }
.video-mini-bar .track-thumb {
  width: 40px; height: 40px; object-fit: cover; border-radius: 4px; flex-shrink: 0;
}
.mini-info { flex: 1; min-width: 0; }
.mini-title { font-size: 0.85rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mini-artist { font-size: 0.75rem; color: var(--sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mini-btn {
  background: none; border: none; color: var(--text); cursor: pointer;
  padding: 0.35rem; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  -webkit-tap-highlight-color: transparent;
}
.mini-btn svg { width: 22px; height: 22px; fill: currentColor; }
.mini-btn:hover { color: var(--accent); }
.mini-play-btn { background: var(--accent); color: #000; width: 38px; height: 38px; }
.mini-play-btn:hover { background: #1ed760; color: #000; }
.mini-play-btn svg { width: 16px; height: 16px; }

/* ── Floating mini-player (appears when exiting overlay via Escape / fullscreenchange) ── */
.video-float-container {
  position: fixed; bottom: 80px; right: 16px;
  width: 300px; height: 170px;
  background: #000; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.65), 0 0 0 1px rgba(255,255,255,0.08);
  z-index: 700; overflow: hidden;
  display: none; touch-action: none;
  transition: box-shadow 0.15s;
}
.video-float-container.active { display: block; }
.video-float-container.dragging { box-shadow: 0 16px 48px rgba(0,0,0,0.8); transition: none; cursor: grabbing; }
.video-float-container video { width: 100%; height: 100%; object-fit: contain; display: block; }
.video-float-controls {
  position: absolute; top: 5px; right: 5px;
  display: flex; gap: 4px; z-index: 2;
  opacity: 0; transition: opacity 0.2s;
}
.video-float-container:hover .video-float-controls { opacity: 1; }
.video-float-btn {
  background: rgba(0,0,0,0.65); border: none; color: #fff;
  border-radius: 50%; width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.video-float-btn svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; }
.video-float-btn svg[fill=currentColor] { fill: currentColor; stroke: none; }
.video-float-btn:hover { background: rgba(255,255,255,0.25); }
@media (max-width: 480px) {
  .video-float-container { width: 200px; height: 113px; bottom: 60px; right: 8px; }
}
"""
