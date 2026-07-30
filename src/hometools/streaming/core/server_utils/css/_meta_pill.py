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
/* Table/detail view: BPM becomes its own grid column (see css/_table_view.py) */
.track-list.table-mode .track-bpm-cell { display: inline-flex; }
"""
