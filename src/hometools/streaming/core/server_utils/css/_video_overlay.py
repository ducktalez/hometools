"""CSS fragment: video overlay (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_video_overlay_css() -> str:
    """Return the video overlay section of the dark-theme CSS."""
    return """/* ── Video thumbnail preview ── */
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
  position: absolute; top: 50%; left: 0.6rem; transform: translateY(-50%);
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
/* indexing toast (top-right info notification, click to dismiss) */
.ht-indexing-toast {
  position: fixed; top: 0.75rem; right: 0.75rem;
  background: rgba(50,50,50,0.92); color: #ccc; padding: 0.45rem 0.9rem;
  border-radius: 6px; font-size: 0.78rem; z-index: 9998;
  box-shadow: 0 2px 8px rgba(0,0,0,0.35); opacity: 0;
  transition: opacity 0.3s; pointer-events: auto; cursor: pointer;
  -webkit-user-select: none; user-select: none;
  -webkit-tap-highlight-color: transparent;
  max-width: 320px; text-align: left; word-break: break-word;
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.06);
}
.ht-indexing-toast.visible { opacity: 1; }
.ht-indexing-toast:hover { background: rgba(60,60,60,0.96); }
.ht-indexing-toast .spinner {
  display: inline-block; width: 10px; height: 10px;
  border: 2px solid #666; border-top-color: #ccc;
  border-radius: 50%; animation: ht-spin 0.8s linear infinite;
  margin-right: 6px; vertical-align: middle;
}
.ht-indexing-toast .ht-index-row { display: flex; align-items: center; }
.ht-indexing-toast .ht-index-progress {
  margin-top: 6px; height: 4px; width: 100%;
  background: rgba(255,255,255,0.12); border-radius: 2px; overflow: hidden;
}
.ht-indexing-toast .ht-index-progress-fill {
  height: 100%; background: var(--accent, #1db954); border-radius: 2px;
  transition: width 0.4s ease;
}
@keyframes ht-spin { to { transform: rotate(360deg); } }
/* On narrow viewports the toast must not overlap the header search input. */
@media (max-width: 600px) {
  .ht-indexing-toast {
    top: auto; right: 0.5rem;
    bottom: calc(env(safe-area-inset-bottom, 0px) + 84px);
    max-width: 72vw; font-size: 0.72rem; padding: 0.35rem 0.7rem;
  }
}

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
/* ── Queue peek-handle — sits above the player bar, replaces the old
   queue icon button entirely. Only shown while the queue has items.
   Click or drag-up opens the queue panel. */
.queue-peek-handle {
  position: absolute; top: -16px; left: 50%; transform: translateX(-50%);
  display: none; align-items: center; justify-content: center;
  width: 64px; height: 18px; cursor: grab; touch-action: none;
  -webkit-user-select: none; user-select: none; z-index: 101;
  background: var(--surface); border: 1px solid #333; border-bottom: none;
  border-radius: 8px 8px 0 0;
}
.queue-peek-handle.has-items { display: flex; }
.queue-peek-handle:active { cursor: grabbing; }
.queue-peek-bar {
  width: 32px; height: 4px; border-radius: 2px; background: #555;
  transition: background 0.15s;
}
.queue-peek-handle:hover .queue-peek-bar { background: var(--accent); }
.queue-peek-badge {
  position: absolute; top: -6px; right: -6px;
  min-width: 15px; height: 15px; padding: 0 3px; border-radius: 8px;
  background: var(--accent); color: #000; font-size: 0.6rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.queue-peek-badge:empty { display: none; }
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
.ctrl-btn.queue-btn { position: relative; flex-shrink: 0; }
.ctrl-btn.queue-btn svg { width: 16px; height: 16px; }
/* Queue button as a top-level flex item in classic player bar (right-aligned, next to progress) */
.player-bar.classic > .ctrl-btn.queue-btn { margin-left: 2px; }
/* Queue button inside .progress-wrap (waveform mode) — keep small left gap */
.progress-wrap .ctrl-btn.queue-btn { margin-left: 4px; }
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
/* ── Video overlay: full-screen with floating controls overlay ── */
.video-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  /* Explicit dimensions fix iOS Safari: position:fixed inside body{overflow:hidden;display:flex}
     gets clipped to the flex container. Setting width/height explicitly + will-change bypasses this. */
  width: 100vw;
  height: 100vh; height: 100dvh;
  background: #000; z-index: 500;
  will-change: transform; /* new compositor layer → no iOS clipping */
}
.video-overlay.view-hidden { display: none; }
/* Header floats over the video top edge with a gradient scrim */
.video-overlay-header {
  position: absolute; top: 0; left: 0; right: 0; z-index: 10;
  display: flex; align-items: center; gap: 0.5rem;
  height: calc(var(--header-h) + env(safe-area-inset-top, 0px));
  padding-top: env(safe-area-inset-top, 0px);
  padding-left: max(0.75rem, env(safe-area-inset-left, 0.75rem));
  padding-right: max(0.75rem, env(safe-area-inset-right, 0.75rem));
  background: linear-gradient(to bottom, rgba(0,0,0,0.78) 0%, transparent 100%);
  transition: opacity 0.3s;
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
/* Cast button — mirrors .video-fs-btn shape, accent colour when connected */
.video-cast-btn {
  background: none; border: none; color: #fff;
  border-radius: 50%; width: 36px; height: 36px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.video-cast-btn:hover { background: rgba(255,255,255,0.1); }
.video-cast-btn svg { width: 18px; height: 18px; }
.video-cast-btn.active { color: var(--accent, #1db954); }
.video-cast-btn[hidden] { display: none; }
/* Video fills the entire overlay — controls float over it */
.video-wrap {
  position: absolute; inset: 0;
  background: #000;
}
.video-wrap video {
  display: block;
  width: 100%; height: 100%;
  object-fit: contain;
}
/* Player bar floats over video bottom edge with a gradient scrim */
.video-overlay .player-bar {
  position: absolute; bottom: 0; left: 0; right: 0; z-index: 10;
  background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.55) 65%, transparent 100%);
  border-top: none;
  padding-bottom: max(var(--sab), env(safe-area-inset-bottom, 0px));
  transition: opacity 0.3s;
}
.video-overlay .player-bar.view-hidden { display: none; }
/* Auto-hide: controls fade out when controls-hidden class is added */
.video-overlay.controls-hidden .video-overlay-header,
.video-overlay.controls-hidden .video-overlay .player-bar {
  opacity: 0;
  pointer-events: none;
}
/* Skip-intro button — anchored above the player bar */
.video-skip-intro-btn {
  position: absolute; bottom: calc(var(--player-h) + 8px + max(var(--sab), env(safe-area-inset-bottom, 0px)));
  right: max(1rem, env(safe-area-inset-right, 1rem));
  z-index: 20;
  display: flex; align-items: center; gap: 0.4rem;
  background: rgba(20,20,20,0.82); color: #fff;
  border: 1.5px solid rgba(255,255,255,0.35); border-radius: 20px;
  padding: 6px 14px; font-size: 0.82rem; font-weight: 600;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: background 0.15s, border-color 0.15s;
}
.video-skip-intro-btn:hover { background: rgba(40,40,40,0.92); border-color: rgba(255,255,255,0.6); }
.video-skip-intro-btn[hidden] { display: none; }
.video-skip-intro-btn svg { width: 16px; height: 16px; flex-shrink: 0; }
.video-skip-intro-btn.set-mode {
  border-style: dashed; border-color: var(--accent, #bb86fc); color: var(--accent, #bb86fc);
}
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
