"""CSS fragment: metric pill (generic per-track numeric metadata badge).

Introduced for the BPM feature (docs/architecture.md → "Metric Pill
Architecture"); designed to be reused by future single-value metadata
badges (mood score, key brightness, ...) without new CSS — only a new
``.meta-pill--<key>`` modifier plus JS-side config is needed per field.
"""

from __future__ import annotations


def render_meta_pill_css() -> str:
    """Return the metric-pill section of the dark-theme CSS."""
    return """/* ── Generic metric pill (BPM today; future: mood/key/...) ──────────────────
   Rendered by webui/src/metricPill.ts (window.renderBpmPill bridge).
   Two independent CSS custom properties, both set inline per pill:
     --pill-fill  (0%-100%) — value position within [min, max]
     --pill-color (rgb(...)) — heatmap color at that position
   combined into one linear-gradient so the badge encodes the value both
   as a left-to-right fill AND a heatmap color at once. */
.track-bpm-cell {
  display: inline-flex; align-items: center; flex-shrink: 0; margin-left: 4px;
}
.meta-pill {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 2.6rem; height: 1.35rem; padding: 0 0.55rem;
  border-radius: 999px; font-size: 0.68rem; font-weight: 700;
  color: #fff; white-space: nowrap; flex-shrink: 0; line-height: 1;
  border: 1px solid rgba(255,255,255,0.1);
  background: linear-gradient(to right,
    var(--pill-color, #666) var(--pill-fill, 0%),
    rgba(255,255,255,0.06) var(--pill-fill, 0%));
  text-shadow: 0 1px 1px rgba(0,0,0,0.45);
}
.meta-pill--missing {
  background: #3a3a3a; color: #888; border: 1px solid #4a4a4a;
  font-weight: 700; cursor: default; text-shadow: none;
}
.meta-pill--calc {
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  animation: meta-pill-glow 1.8s ease-in-out infinite;
}
.meta-pill--calc:hover { background: #4a4a4a; color: #eee; }
.meta-pill--calc:disabled,
.meta-pill--calc.meta-pill--calculating {
  animation: none; opacity: 0.55; cursor: wait;
}
@keyframes meta-pill-glow {
  0%, 100% { box-shadow: 0 0 2px 0px rgba(255,214,0,0.35); }
  50%      { box-shadow: 0 0 9px 3px rgba(255,214,0,0.8); }
}
/* Known-value pill rendered as a <button> when the Tools-panel "BPM
   berechnen" toggle is active — opens the BPM-adjust popup on click
   (player_js/_track_render.py::_openBpmAdjustMenu). No glow (that's
   reserved for "unknown, click to calculate") — a subtle hover
   brightening is enough to signal it's interactive. */
.meta-pill--editable {
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  font: inherit;
}
.meta-pill--editable:hover { filter: brightness(1.18); }
.meta-pill--editable:disabled { opacity: 0.55; cursor: wait; filter: none; }
/* Table/detail view: BPM becomes its own grid column (see css/_table_view.py) */
.track-list.table-mode .track-bpm-cell { display: inline-flex; }

/* ── BPM-adjust popup ─────────────────────────────────────────────────────
   Opened by clicking a BPM pill while the Tools-panel "BPM berechnen"
   toggle is active. Reuses `.ht-ctx-menu`'s base look (dark card, fixed
   position, shadow — see css/_table_view.py) with its own content layout
   (action-button row + manual numeric-entry row) instead of `.ht-ctx-item`
   click-only rows, since it needs a live `<input>`. */
.bpm-adjust-menu { padding: 10px 12px; width: 236px; }
.bpm-adjust-current {
  font-size: 0.78rem; color: var(--sub); text-align: center; margin-bottom: 8px;
}
.bpm-adjust-actions { display: flex; gap: 6px; margin-bottom: 10px; }
.bpm-adjust-btn {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
  background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 6px;
  color: var(--fg); font-size: 0.66rem; padding: 7px 4px; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.bpm-adjust-btn svg { width: 15px; height: 15px; }
.bpm-adjust-btn:hover:not(:disabled) { background: #3a3a3a; border-color: var(--accent); }
.bpm-adjust-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.bpm-adjust-manual { display: flex; gap: 6px; border-top: 1px solid #333; padding-top: 10px; }
.bpm-adjust-input {
  flex: 1; min-width: 0; background: #111; border: 1px solid #3a3a3a; border-radius: 6px;
  color: var(--fg); font-size: 0.82rem; padding: 6px 8px;
}
.bpm-adjust-apply {
  background: var(--accent); color: #000; border: none; border-radius: 6px;
  padding: 6px 10px; font-size: 0.78rem; font-weight: 600; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.bpm-adjust-apply:disabled { opacity: 0.55; cursor: wait; }
"""
