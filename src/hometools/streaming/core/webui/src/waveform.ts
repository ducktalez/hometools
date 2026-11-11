/**
 * Player-bar waveform (audio) / progress indicator (video). Ported from
 * `_player_js.py` (classic layout). Peaks come from the server-side cache
 * (`GET <api>/waveform?path=`), never from decoding the audio client-side.
 * Peak state + abort controller are module-private; legacy calls
 * `drawWaveform(frac)` / `generateWaveform(url, relPath)` through window.
 */

export interface WaveformPeaks {
  left: number[];
  /** null = mono */
  right: number[] | null;
}

export interface WaveformHooks {
  canvas: HTMLCanvasElement | null;
  isAudioMode: boolean;
  apiPath: string; // e.g. "/api/audio/waveform"
  /** Current playback fraction 0..1 (player fallback when no peaks drawn yet). */
  currentFraction(): number;
  /** Fraction used on window resize (progress bar value/max). */
  resizeFraction(): number;
}

/** Normalise the API payload: stereo (`peaks_l`/`peaks_r`) or legacy mono (`peaks`). */
export function parseWaveformPeaks(data: unknown): WaveformPeaks | null {
  if (!data || typeof data !== "object") return null;
  const d = data as { peaks_l?: unknown; peaks_r?: unknown; peaks?: unknown };
  if (Array.isArray(d.peaks_l) && d.peaks_l.length) {
    const r = Array.isArray(d.peaks_r) && d.peaks_r.length ? (d.peaks_r as number[]) : null;
    return { left: d.peaks_l as number[], right: r };
  }
  if (Array.isArray(d.peaks) && d.peaks.length) return { left: d.peaks as number[], right: null };
  return null;
}

let _h: WaveformHooks | null = null;
let _ctx: CanvasRenderingContext2D | null = null;
let _peaks: WaveformPeaks | null = null;
let _abort: AbortController | null = null;
let _resizeCleanup: (() => void) | null = null;

function accentColor(): string {
  try {
    return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#1db954";
  } catch {
    return "#1db954";
  }
}

export function drawWaveform(progress: number): void {
  const h = _h;
  const canvas = h && h.canvas;
  const ctx = _ctx;
  if (!h || !canvas || !ctx) return;
  const W = canvas.offsetWidth || 600;
  const H = canvas.offsetHeight || 28;
  canvas.width = W;
  canvas.height = H;
  ctx.clearRect(0, 0, W, H);
  const accent = accentColor();
  const prog = progress || 0;
  const cy = H / 2;
  const playedW = W * prog;
  const pk = h.isAudioMode ? _peaks : null;
  const hasStereo = !!(pk && pk.right);
  const hasMono = !!(pk && !pk.right);

  /* Layer 1: base progress indicator */
  if (hasStereo) {
    ctx.fillStyle = "rgba(255,255,255,0.12)";
    ctx.fillRect(0, cy - 0.5, W, 1);
  } else {
    ctx.fillStyle = "#333";
    ctx.fillRect(0, cy - 2.5, W, 5);
    if (playedW > 0) {
      ctx.fillStyle = accent;
      ctx.fillRect(0, cy - 2.5, playedW, 5);
    }
  }

  /* Layer 2: amplitude bars */
  if (pk && (hasStereo || hasMono)) {
    const segs = pk.left.length;
    const slotW = W / segs;
    const gapW = Math.max(0.5, slotW * 0.15);
    const bW = Math.max(1, slotW - gapW);
    if (hasStereo && pk.right) {
      const maxH = cy - 1;
      for (let i = 0; i < segs; i++) {
        const x = i * slotW;
        const played = i < prog * segs;
        ctx.globalAlpha = played ? 0.72 : 0.28;
        ctx.fillStyle = played ? accent : "#999";
        const lh = Math.max(1, pk.left[i] * maxH);
        ctx.fillRect(x, cy - lh, bW, lh);
        const rh = Math.max(1, pk.right[i] * maxH);
        ctx.fillRect(x, cy, bW, rh);
      }
    } else {
      const maxBH = H * 0.88;
      for (let i = 0; i < segs; i++) {
        const bh = Math.max(2, pk.left[i] * maxBH);
        ctx.globalAlpha = i < prog * segs ? 0.38 : 0.22;
        ctx.fillStyle = "#fff";
        ctx.fillRect(i * slotW, cy - bh / 2, bW, bh);
      }
    }
    ctx.globalAlpha = 1;
  }

  /* Layer 3: playhead dot */
  const px = Math.max(6, Math.min(W - 6, playedW));
  ctx.fillStyle = prog > 0 ? "#fff" : "transparent";
  ctx.beginPath();
  ctx.arc(px, cy, 6, 0, Math.PI * 2);
  ctx.fill();
}

export function generateWaveform(_url: string, relativePath?: string): void {
  const h = _h;
  if (!h || !h.isAudioMode || !h.canvas) return;
  if (_abort) _abort.abort();
  _abort = new AbortController();
  const signal = _abort.signal;
  _peaks = null;
  drawWaveform(0);
  if (!relativePath) return;
  try {
    fetch(h.apiPath + "?path=" + encodeURIComponent(relativePath), { signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const pk = parseWaveformPeaks(data);
        if (!pk || signal.aborted) return;
        _peaks = pk;
        drawWaveform(h.currentFraction());
      })
      .catch((e: { name?: string } | null) => {
        if (!e || e.name !== "AbortError") _peaks = null;
      });
  } catch {
    _peaks = null;
  }
}

export function destroyWaveform(): void {
  if (_resizeCleanup) {
    _resizeCleanup();
    _resizeCleanup = null;
  }
  if (_abort) _abort.abort();
  _abort = null;
  _peaks = null;
}

/** Wire canvas + initial draw + redraw on resize. Re-init safe. */
export function initWaveform(h: WaveformHooks): void {
  destroyWaveform();
  _h = h;
  _ctx = h.canvas ? h.canvas.getContext("2d") : null;
  drawWaveform(0);
  const onResize = () => drawWaveform(h.resizeFraction());
  window.addEventListener("resize", onResize);
  _resizeCleanup = () => window.removeEventListener("resize", onResize);
}

