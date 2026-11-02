/**
 * Hover preview for video thumbnails: while the mouse rests on a thumbnail
 * (`[data-preview-path]`), cycle through the frames of its sprite sheet
 * (`/api/video/sprites` meta + `/thumb?size=sprite`, generated in the
 * background by the thumbnailer). Video-only, hover-capable devices only.
 * All state is module-private; listeners are named + removable (rule 14).
 */

export interface SpriteMeta {
  cols: number;
  rows: number;
  frame_w: number;
  frame_h: number;
  interval: number;
  count: number;
}

interface Sprite {
  meta: SpriteMeta;
  url: string;
}

export const HOVER_DELAY_MS = 300;
export const FRAME_MS = 450;
const NEGATIVE_TTL_MS = 30000;

/** Background CSS for frame `idx`, "cover"-fitted and centered in a W x H box. */
export function frameStyle(
  meta: SpriteMeta,
  boxW: number,
  boxH: number,
  idx: number
): { backgroundSize: string; backgroundPosition: string } {
  const scale = Math.max(boxW / meta.frame_w, boxH / meta.frame_h);
  const dw = meta.frame_w * scale;
  const dh = meta.frame_h * scale;
  const col = idx % meta.cols;
  const row = Math.floor(idx / meta.cols);
  const x = -col * dw + (boxW - dw) / 2;
  const y = -row * dh + (boxH - dh) / 2;
  return {
    backgroundSize: meta.cols * dw + "px " + meta.rows * dh + "px",
    backgroundPosition: x + "px " + y + "px",
  };
}

function validMeta(m: unknown): m is SpriteMeta {
  const x = m as Partial<SpriteMeta> | null;
  return !!x && !!x.cols && !!x.rows && !!x.frame_w && !!x.frame_h && !!x.count;
}

const cache = new Map<string, Promise<Sprite | null>>();

function loadSprite(path: string): Promise<Sprite | null> {
  const hit = cache.get(path);
  if (hit) return hit;
  const enc = encodeURIComponent(path);
  const p: Promise<Sprite | null> = fetch("/api/video/sprites?path=" + enc)
    .then((r) => (r.ok ? r.json() : null))
    .then((meta: unknown) => {
      if (!validMeta(meta)) return null;
      const url = "/thumb?path=" + enc + "&size=sprite";
      return new Promise<Sprite | null>((resolve) => {
        const img = new Image();
        img.onload = () => resolve({ meta, url });
        img.onerror = () => resolve(null);
        img.src = url;
      });
    })
    .catch(() => null);
  cache.set(path, p);
  // Sprite may not exist yet -> retry later instead of caching the miss forever.
  void p.then((s) => {
    if (!s) setTimeout(() => cache.delete(path), NEGATIVE_TTL_MS);
  });
  return p;
}

let _active: HTMLElement | null = null;
let _overlay: HTMLElement | null = null;
let _delayTimer: ReturnType<typeof setTimeout> | null = null;
let _frameTimer: ReturnType<typeof setInterval> | null = null;
let _token = 0;
let _cleanup: (() => void) | null = null;

function stop(): void {
  _token++;
  if (_delayTimer) clearTimeout(_delayTimer);
  if (_frameTimer) clearInterval(_frameTimer);
  _delayTimer = null;
  _frameTimer = null;
  if (_overlay) _overlay.remove();
  _overlay = null;
  _active = null;
}

function start(wrap: HTMLElement, path: string, token: number): void {
  void loadSprite(path).then((sprite) => {
    if (!sprite || token !== _token || _active !== wrap) return;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (!w || !h) return;
    const ov = document.createElement("div");
    ov.className = "hover-preview";
    ov.style.backgroundImage = 'url("' + sprite.url + '")';
    ov.style.backgroundRepeat = "no-repeat";
    let idx = Math.min(1, sprite.meta.count - 1);
    const paint = () => {
      const s = frameStyle(sprite.meta, w, h, idx);
      ov.style.backgroundSize = s.backgroundSize;
      ov.style.backgroundPosition = s.backgroundPosition;
    };
    paint();
    wrap.appendChild(ov);
    _overlay = ov;
    _frameTimer = setInterval(() => {
      idx = (idx + 1) % sprite.meta.count;
      paint();
    }, FRAME_MS);
  });
}

function onOver(e: Event): void {
  const t = e.target as HTMLElement | null;
  const wrap = t && t.closest ? t.closest<HTMLElement>("[data-preview-path]") : null;
  if (!wrap || wrap === _active) return;
  stop();
  const path = wrap.dataset.previewPath || "";
  if (!path) return;
  _active = wrap;
  const token = _token;
  _delayTimer = setTimeout(() => start(wrap, path, token), HOVER_DELAY_MS);
}

function onOut(e: Event): void {
  if (!_active) return;
  const to = (e as MouseEvent).relatedTarget as Node | null;
  if (to && _active.contains(to)) return;
  stop();
}

/** Install once. Returns a destroy function. No-op unless enabled + hover-capable. */
export function installHoverPreview(opts: { enabled: boolean }): () => void {
  destroyHoverPreview();
  const canHover = typeof window !== "undefined" && !!window.matchMedia && window.matchMedia("(hover: hover)").matches;
  if (!opts.enabled || !canHover) return () => {};
  document.addEventListener("mouseover", onOver);
  document.addEventListener("mouseout", onOut);
  _cleanup = () => {
    document.removeEventListener("mouseover", onOver);
    document.removeEventListener("mouseout", onOut);
    stop();
  };
  return destroyHoverPreview;
}

export function destroyHoverPreview(): void {
  if (_cleanup) {
    _cleanup();
    _cleanup = null;
  }
}

/** Test hook. */
export function _clearSpriteCache(): void {
  cache.clear();
}

