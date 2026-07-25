"""CSS fragment: tools panel (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_tools_panel_css() -> str:
    """Return the tools panel section of the dark-theme CSS."""
    return """/* ── Tools pill + panel ── */
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
"""
