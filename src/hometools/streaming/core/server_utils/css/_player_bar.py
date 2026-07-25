"""CSS fragment: player bar (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_player_bar_css() -> str:
    """Return the player bar section of the dark-theme CSS."""
    return """/* ── Rating bar overlay on thumbnails ── */
.thumb-wrap {
  position: relative; flex-shrink: 0; overflow: hidden;
}
.thumb-wrap.track-thumb-wrap {
  width: 40px; height: 40px; border-radius: 4px;
}
.thumb-wrap.track-thumb-wrap .track-thumb {
  width: 100%; height: 100%; border-radius: 0;
}
/* Hover-play button overlaying the track thumbnail (left of the row) */
.track-play-btn {
  position: absolute; inset: 0; margin: auto;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--accent); color: #000; border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; opacity: 0; transition: opacity 0.15s;
  padding: 0;
}
.track-play-btn svg { width: 11px; height: 11px; fill: currentColor; pointer-events: none; }
@media (hover: none) {
  .track-play-btn { opacity: 0.7; }
}
@media (hover: hover) {
  .track-thumb-wrap:hover .track-play-btn { opacity: 1; }
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
/* Clickable album cover in player bar */
.player-thumb-clickable {
  cursor: pointer; border-radius: 4px;
  transition: opacity 0.15s, box-shadow 0.15s;
}
.player-thumb-clickable:hover { opacity: 0.82; box-shadow: 0 0 0 2px var(--accent); }
/* Player bar right-side actions (kebab always; move+trash in tool mode) */
.player-bar-actions {
  display: flex; flex-direction: column; align-items: flex-end;
  justify-content: center; gap: 3px; flex-shrink: 0; margin-left: 4px;
  min-width: 28px;
}
.player-bar-actions-row { display: flex; align-items: center; gap: 3px; }
/* Move-folder select in player bar — compact */
.player-bar-move-select {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 6px; padding: 2px 6px; font-size: 0.72rem; cursor: pointer;
  max-width: 130px; flex-shrink: 1;
}
.player-bar-move-select:focus { border-color: var(--accent); outline: none; }
/* Trash button in player bar */
.player-bar-trash-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  padding: 4px; display: flex; align-items: center; justify-content: center;
  border-radius: 4px; flex-shrink: 0; transition: color 0.12s;
  -webkit-tap-highlight-color: transparent;
}
.player-bar-trash-btn svg { width: 14px; height: 14px; pointer-events: none; }
.player-bar-trash-btn:hover { color: #e57373; }
/* Kebab button in player bar */
.player-bar-kebab-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  padding: 4px; display: flex; align-items: center; justify-content: center;
  border-radius: 4px; flex-shrink: 0; opacity: 0.65; transition: opacity 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.player-bar-kebab-btn svg { width: 14px; height: 14px; pointer-events: none; }
.player-bar-kebab-btn:hover { opacity: 1; }
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
  touch-action: none;
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
  touch-action: none;
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

"""
