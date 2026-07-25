"""CSS fragment: playlist cards (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_playlist_cards_css() -> str:
    """Return the playlist cards section of the dark-theme CSS."""
    return """/* ── Playlist pseudo-folder cards ── */
.playlist-folder-card { position: relative; }
.fav-folder.playlist-folder-card,
.playlist-folder-card:not(.smart-playlist-card):not(.playlist-new-card) { border: 1px solid var(--accent); border-radius: 8px; }
.smart-playlist-card { border: 1px solid #a259e6; border-radius: 8px; }

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
.smart-new-card .tools-row-icon { color: var(--accent); }

/* Cover play button — the cover itself is the "Abspielen" affordance:
   a centered circular overlay on the thumbnail, revealed on hover. */
.playlist-thumb-wrap {
  position: relative; width: 100%; margin-bottom: 0.4rem;
}
.folder-grid.list-mode .playlist-thumb-wrap {
  width: 40px; height: 40px; flex-shrink: 0; margin-bottom: 0;
}
.folder-grid.list-mode .playlist-cover-play-btn { width: 30px; height: 30px; }
.folder-grid.list-mode .playlist-cover-play-btn svg { width: 14px; height: 14px; }
.playlist-cover-play-btn {
  position: absolute; inset: 0; margin: auto;
  width: 44px; height: 44px; border-radius: 50%;
  background: var(--accent); color: #000; border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; opacity: 0; transition: opacity 0.15s; padding: 0; z-index: 2;
}
.playlist-cover-play-btn svg { width: 20px; height: 20px; fill: currentColor; pointer-events: none; }
@media (hover: none) { .playlist-cover-play-btn { opacity: 0.75; } }
@media (hover: hover) { .playlist-thumb-wrap:hover .playlist-cover-play-btn { opacity: 1; } }
.playlist-cover-play-btn:hover { background: #1ed760; }

/* Kebab menu trigger — always top-right corner, same spot as every other
   three-dot menu button in the UI (consistent placement rule). */
.playlist-folder-kebab {
  position: absolute; top: 6px; right: 6px; z-index: 3;
  background: rgba(0,0,0,0.55); border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 26px; height: 26px; cursor: pointer; padding: 0;
  display: flex; align-items: center; justify-content: center;
  opacity: 0.7; transition: opacity 0.15s, color 0.12s, border-color 0.12s;
}
.playlist-folder-kebab svg { width: 14px; height: 14px; pointer-events: none; }
.playlist-folder-card:hover .playlist-folder-kebab { opacity: 1; }
.playlist-folder-kebab:hover { color: var(--accent); border-color: var(--accent); }

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
.track-thumb {
  width: 40px; height: 40px; border-radius: 4px; object-fit: cover;
  flex-shrink: 0; background: var(--surface2);
}
"""
