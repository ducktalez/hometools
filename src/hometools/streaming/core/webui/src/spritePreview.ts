/**
 * Video scrubber sprite-sheet preview. Ported from `_player_js.py`
 * (`sprite_preview_js`). Sprite meta + image are module-private; legacy
 * calls `loadSpriteData(relPath)` (via playItem hook) after each item start.
 */

export interface SpriteMeta {
  cols: number;
  rows?: number;
  frame_w: number;
  frame_h: number;
  count: number;
  interval: number;
}

export interface SpritePreviewEls {
  player: HTMLMediaElement;
  isVideoMode: boolean;
  track: HTMLElement | null;
  preview: HTMLElement | null;
  canvas: HTMLCanvasElement | null;
  timeEl: HTMLElement | null;
  fmtTime(sec: number): string;
}

let _els: SpritePreviewEls | null = null;
let _meta: SpriteMeta | null = null;
let _img: HTMLImageElement | null = null;

/** Source rect of frame `idx` inside the sprite sheet; idx clamped to count-1. */
export function spriteFrameRect(
  meta: SpriteMeta,
  seekTime: number
): { sx: number; sy: number; sw: number; sh: number } {
  const idx = Math.max(0, Math.min(Math.floor(seekTime / meta.interval), meta.count - 1));
  const col = idx % meta.cols;
  const row = Math.floor(idx / meta.cols);
  return { sx: col * meta.frame_w, sy: row * meta.frame_h, sw: meta.frame_w, sh: meta.frame_h };
}

export function loadSpriteData(relativePath: string): void {
  _meta = null;
  _img = null;
  const e = _els;
  if (!e || !e.isVideoMode || !relativePath) return;
  const q = encodeURIComponent(relativePath);
  try {
    fetch("/api/video/sprites?path=" + q)
      .then((r) => (r.ok ? r.json() : null))
      .then((meta: SpriteMeta | null) => {
        if (!meta || !meta.cols) return;
        _meta = meta;
        const img = new Image();
        img.onload = () => {
          /* ignore if another item started meanwhile */
          if (_meta === meta) _img = img;
        };
        img.src = "/thumb?path=" + q + "&size=sprite";
      })
      .catch(() => {});
  } catch {
    /* ignore */
  }
}

export function initSpritePreview(els: SpritePreviewEls): void {
  _els = els;
  _meta = null;
  _img = null;
  const track = els.track;
  if (!els.isVideoMode || !track || !els.preview) return;
  const preview = els.preview;
  track.addEventListener("mousemove", (ev) => {
    const p = els.player;
    if (!_meta || !_img || !p.duration || !isFinite(p.duration)) return;
    const rect = track.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, ((ev as MouseEvent).clientX - rect.left) / rect.width));
    const seekTime = ratio * p.duration;
    preview.style.left = Math.max(5, Math.min(95, ratio * 100)) + "%";
    preview.classList.add("visible");
    if (els.timeEl) els.timeEl.textContent = els.fmtTime(seekTime);
    const ctx = els.canvas ? els.canvas.getContext("2d") : null;
    if (ctx && els.canvas) {
      const r = spriteFrameRect(_meta, seekTime);
      els.canvas.width = _meta.frame_w;
      els.canvas.height = _meta.frame_h;
      ctx.drawImage(_img, r.sx, r.sy, r.sw, r.sh, 0, 0, _meta.frame_w, _meta.frame_h);
    }
  });
  track.addEventListener("mouseleave", () => preview.classList.remove("visible"));
}

