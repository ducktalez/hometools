"""CSS fragment: modals (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_modals_css() -> str:
    """Return the modals section of the dark-theme CSS."""
    return """/* ── Edit metadata modal ── */
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
"""
