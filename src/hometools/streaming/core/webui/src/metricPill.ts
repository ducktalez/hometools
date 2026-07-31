/**
 * Generic "metric pill" renderer for per-track numeric metadata (BPM today;
 * designed so future fields — mood score, musical key brightness, etc. —
 * can reuse the same component instead of hand-rolling another pill).
 *
 * Architecture (see docs/architecture.md → "Metric Pill Architecture" and
 * docs/IMPLEMENTATION_PLAN.md for the full design writeup):
 *
 * - List view ("Listenansicht"): the pill renders inline next to the track
 *   (a small rounded badge).
 * - Table/detail view ("Detailansicht"): the *same* markup becomes a grid
 *   column via CSS alone (`.track-list.table-mode .track-bpm-cell`) — no
 *   separate "column renderer" is needed, one render call serves both
 *   views. This generalizes past the older genre/duration columns (which
 *   only ever existed in table mode) — see the Design Discussion entry for
 *   the follow-up to upgrade those the same way.
 * - Unknown value (``value <= 0``): renders a grey "?" pill. If the calling
 *   context marks the metric as calculable (`opts.calcEnabled`), the pill
 *   becomes a clickable `<button>` with a pulsing yellow glow — the visual
 *   affordance the Tools-panel "calculate" feature (e.g. "BPM berechnen")
 *   relies on to signal "click me".
 * - Known value: the pill's background encodes the value twice at once —
 *   a heatmap color (blue → yellow → red, interpolated across
 *   `cfg.colorStops`) AND a left-to-right fill percentage — combining both
 *   visual-encoding options that were on the table for BPM into one
 *   design, via a single CSS `linear-gradient` driven by two custom
 *   properties (`--pill-fill` / `--pill-color`) set inline per pill.
 *
 * Bridge pattern: see main.ts's header comment. This module's render
 * function is pure (no DOM mutation, no fetch) — a deliberate choice
 * mirroring the Phase 5 "dependency-free leaf function" precedent
 * (fmtTime/escHtml/formatBytes). The click-to-calculate *behavior*
 * (fetch + in-memory state sync + toast) stays in the legacy
 * Python-generated script for now because it needs `filteredItems`/
 * `allItems`/`showToast` — identifiers private to that script's own
 * closure (not reachable from here) — see the Design Discussion on
 * player-JS module coupling for why that boundary is still there.
 */

export interface MetricPillColorStop {
  /** Normalized position in [0, 1]. */
  at: number;
  /** CSS color (any valid `background`-color value). */
  color: string;
}

export interface MetricPillConfig {
  /** Short machine key, e.g. "bpm" — becomes the `meta-pill--<key>` class and the `data-action="calc-<key>"` value. */
  key: string;
  /** Human label used in title/aria text, e.g. "BPM". */
  label: string;
  /** Suffix appended to the displayed number, e.g. "" for BPM (number is self-explanatory) or " min" for a duration-like metric. */
  unit: string;
  /** Display range for the fill/heatmap normalization — values are clamped into [min, max]. */
  min: number;
  max: number;
  /** Decimal places for the displayed number. 0 (default) rounds to an integer. */
  decimals?: number;
  /** Color stops for the heatmap gradient, sorted by `at` ascending. Defaults to a blue→yellow→red ramp. */
  colorStops?: MetricPillColorStop[];
}

export interface MetricPillOptions {
  /** Zero-based row index — forwarded as `data-index` for the legacy click delegation handler. */
  index?: number;
  /** `relative_path` of the track — forwarded as `data-relative-path`. */
  relativePath?: string;
  /** When true, render a clickable `<button>` instead of a static `<span>`
   * — a grey "?" calculate affordance when the value is missing (`<= 0`),
   * or the normal colored pill made clickable (`.meta-pill--editable`)
   * when a value is already known, so a click opens the BPM-adjust popup
   * (`player_js/_track_render.py::_openBpmAdjustMenu`) either way. */
  calcEnabled?: boolean;
}

const DEFAULT_COLOR_STOPS: MetricPillColorStop[] = [
  { at: 0, color: "#4fc3f7" }, // slow / low — cool blue
  { at: 0.5, color: "#ffca28" }, // mid — amber
  { at: 1, color: "#ff5252" }, // fast / high — red
];

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function escAttr(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Parse a CSS hex color (`#rgb` or `#rrggbb`) into `[r, g, b]` (0-255 each). Falls back to grey on any other format. */
function parseColor(c: string): [number, number, number] {
  const hex = c.trim().replace("#", "");
  if (hex.length === 3) {
    const r = parseInt(hex[0] + hex[0], 16);
    const g = parseInt(hex[1] + hex[1], 16);
    const b = parseInt(hex[2] + hex[2], 16);
    return [r, g, b];
  }
  if (hex.length === 6) {
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return [r, g, b];
  }
  return [136, 136, 136];
}

/** Linearly interpolate a CSS color across `stops` at normalized position `t` (0..1). */
export function interpolateColor(stops: MetricPillColorStop[], t: number): string {
  const sorted = [...stops].sort((a, b) => a.at - b.at);
  const clamped = clamp01(t);
  if (sorted.length === 0) return "#888888";
  if (clamped <= sorted[0].at) return sorted[0].color;
  if (clamped >= sorted[sorted.length - 1].at) return sorted[sorted.length - 1].color;
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i];
    const b = sorted[i + 1];
    if (clamped >= a.at && clamped <= b.at) {
      const span = b.at - a.at;
      const localT = span > 0 ? (clamped - a.at) / span : 0;
      const [ar, ag, ab] = parseColor(a.color);
      const [br, bg, bb] = parseColor(b.color);
      const r = Math.round(ar + (br - ar) * localT);
      const g = Math.round(ag + (bg - ag) * localT);
      const bch = Math.round(ab + (bb - ab) * localT);
      return `rgb(${r}, ${g}, ${bch})`;
    }
  }
  return sorted[sorted.length - 1].color;
}

/**
 * Render one metric pill as an HTML string.
 *
 * `value <= 0` (or `null`/`undefined`) is treated as "unknown" — matches
 * the `MediaItem` convention used across the codebase (`0.0` = unset) for
 * every optional numeric field (rating, bpm, intro markers, ...).
 *
 * `opts.calcEnabled` gates a clickable affordance in **both** branches
 * (not just "unknown"): when true, a *known* value also renders as a
 * `<button>` (`.meta-pill--editable`, same `data-action="calc-<key>"`
 * attribute as the "unknown" button) so the player UI's BPM-adjust popup
 * (`player_js/_track_render.py::_openBpmAdjustMenu`) can open from a
 * click on an already-analyzed pill, not only an unanalyzed one.
 */
export function renderMetricPill(value: number | null | undefined, cfg: MetricPillConfig, opts: MetricPillOptions = {}): string {
  const idxAttr = opts.index != null ? ` data-index="${opts.index}"` : "";
  const pathAttr = opts.relativePath ? ` data-relative-path="${escAttr(opts.relativePath)}"` : "";

  if (value == null || value <= 0) {
    if (opts.calcEnabled) {
      return (
        `<button type="button" class="meta-pill meta-pill--missing meta-pill--calc" ` +
        `data-action="calc-${cfg.key}"${idxAttr}${pathAttr} ` +
        `title="${escAttr(cfg.label)} berechnen (Klick)">?</button>`
      );
    }
    return `<span class="meta-pill meta-pill--missing" title="${escAttr(cfg.label)} unbekannt">?</span>`;
  }

  const min = cfg.min;
  const max = cfg.max;
  const clamped = Math.max(min, Math.min(max, value));
  const t = max > min ? (clamped - min) / (max - min) : 0;
  const color = interpolateColor(cfg.colorStops || DEFAULT_COLOR_STOPS, t);
  const fillPct = Math.round(t * 100);
  const decimals = cfg.decimals || 0;
  const display = decimals > 0 ? value.toFixed(decimals) : String(Math.round(value));
  const style = `--pill-fill:${fillPct}%;--pill-color:${color};`;

  if (opts.calcEnabled) {
    const title = `${cfg.label}: ${display}${cfg.unit} \u2014 klicken zum Anpassen`;
    return (
      `<button type="button" class="meta-pill meta-pill--${cfg.key} meta-pill--editable" style="${style}" ` +
      `data-action="calc-${cfg.key}"${idxAttr}${pathAttr} title="${escAttr(title)}">` +
      `${escAttr(display)}${escAttr(cfg.unit)}</button>`
    );
  }

  const title = `${cfg.label}: ${display}${cfg.unit}`;

  return (
    `<span class="meta-pill meta-pill--${cfg.key}" style="${style}" title="${escAttr(title)}">` +
    `${escAttr(display)}${escAttr(cfg.unit)}</span>`
  );
}

/** BPM-specific convenience wrapper around {@link renderMetricPill}. */
export function renderBpmPill(bpm: number | null | undefined, min: number, max: number, opts: MetricPillOptions = {}): string {
  return renderMetricPill(bpm, { key: "bpm", label: "BPM", unit: "", min, max }, opts);
}

