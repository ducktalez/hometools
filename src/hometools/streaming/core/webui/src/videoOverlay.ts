/**
 * Video overlay, auto-hiding controls, mini bar and draggable float player.
 * Ported from `player_js/_core.py` (open/closeVideoOverlay, _show/_hide/
 * _toggleVidControls, enter/exitFloatPlayer, _syncMiniBar/_syncMiniPlayBtn,
 * float drag, fullscreen-exit + Escape -> float). `_isFloating` and the
 * control-hide timer are module-private; legacy calls the exported
 * functions through window bridges. No-op in audio mode (elements absent).
 */

export interface VideoOverlayEls {
  player: HTMLMediaElement;
  isVideoMode: boolean;
  overlay: HTMLElement | null;
  miniBar: HTMLElement | null;
  miniTitle: HTMLElement | null;
  miniArtist: HTMLElement | null;
  miniThumb: HTMLImageElement | null;
  miniPlayBtn: HTMLElement | null;
  miniExpandBtn: HTMLElement | null;
  overlayTitleText: HTMLElement | null;
  videoWrap: HTMLElement | null;
  floatContainer: HTMLElement | null;
  floatWrap: HTMLElement | null;
  floatCloseBtn: HTMLElement | null;
  floatExpandBtn: HTMLElement | null;
  closeBtn: HTMLElement | null;
  icPlay: string;
  icPause: string;
}

interface SyncItem {
  title?: string;
  artist?: string;
  thumbnail_url?: string;
  thumbnail_lg_url?: string;
}

const CTRL_HIDE_MS = 3000;

let _e: VideoOverlayEls | null = null;
let _floating = false;
let _ctrlTimer: ReturnType<typeof setTimeout> | null = null;
let _cleanup: (() => void) | null = null;

function fixOverlaySize(): void {
  /* iOS Safari clips position:fixed inside body{overflow:hidden}; explicit
     pixel size is the only reliable fix. */
  if (!_e || !_e.overlay) return;
  _e.overlay.style.height = window.innerHeight + "px";
  _e.overlay.style.width = window.innerWidth + "px";
}

export function isFloating(): boolean {
  return _floating;
}

export function showVidControls(): void {
  const e = _e;
  if (!e || !e.overlay) return;
  e.overlay.classList.remove("controls-hidden");
  if (_ctrlTimer) clearTimeout(_ctrlTimer);
  if (!e.player.paused) _ctrlTimer = setTimeout(hideVidControls, CTRL_HIDE_MS);
}

function hideVidControls(): void {
  const e = _e;
  if (!e || !e.overlay) return;
  e.overlay.classList.add("controls-hidden");
  if (_ctrlTimer) clearTimeout(_ctrlTimer);
  _ctrlTimer = null;
}

function toggleVidControls(): void {
  const e = _e;
  if (!e || !e.overlay) return;
  if (e.overlay.classList.contains("controls-hidden")) showVidControls();
  else hideVidControls();
}

export function openVideoOverlay(): void {
  const e = _e;
  if (!e || !e.overlay) return;
  _floating = false;
  fixOverlaySize();
  e.overlay.classList.remove("view-hidden");
  if (e.miniBar) e.miniBar.hidden = true;
  if (e.floatContainer) e.floatContainer.classList.remove("active");
  /* Move <video> back to overlay if it was in float container */
  if (e.videoWrap && e.player.parentNode !== e.videoWrap) e.videoWrap.appendChild(e.player);
  e.player.style.display = "block";
  showVidControls();
}

export function closeVideoOverlay(): void {
  const e = _e;
  if (!e || !e.overlay) return;
  e.overlay.classList.add("view-hidden");
  /* Mini bar only when a video source is loaded */
  if (e.miniBar) e.miniBar.hidden = !e.player.currentSrc;
}

export function enterFloatPlayer(): void {
  const e = _e;
  if (!e || !e.overlay || !e.floatContainer || !e.floatWrap || !e.isVideoMode) return;
  if (_floating) return;
  _floating = true;
  e.overlay.classList.add("view-hidden");
  if (e.miniBar) e.miniBar.hidden = true;
  e.floatWrap.appendChild(e.player);
  e.player.style.display = "block";
  e.floatContainer.classList.add("active");
  /* Reset position to default bottom-right */
  const s = e.floatContainer.style;
  s.bottom = "80px";
  s.right = "16px";
  s.left = "";
  s.top = "";
}

export function exitFloatPlayer(): void {
  const e = _e;
  if (!e || !_floating) return;
  _floating = false;
  if (e.floatContainer) e.floatContainer.classList.remove("active");
  if (e.videoWrap) e.videoWrap.appendChild(e.player);
  e.player.style.display = "block";
  openVideoOverlay();
}

export function syncMiniBar(t: SyncItem): void {
  const e = _e;
  if (!e || !e.miniBar) return;
  if (e.miniTitle) e.miniTitle.textContent = t.title || "";
  if (e.miniArtist) e.miniArtist.textContent = t.artist || "";
  if (e.miniThumb) {
    const src = t.thumbnail_lg_url || t.thumbnail_url || "";
    e.miniThumb.src = src;
    e.miniThumb.style.display = src ? "" : "none";
  }
  if (e.overlayTitleText) e.overlayTitleText.textContent = t.title || "";
}

function syncMiniPlayBtn(): void {
  const e = _e;
  if (!e || !e.miniPlayBtn) return;
  e.miniPlayBtn.innerHTML = e.player.paused ? e.icPlay : e.icPause;
}

function togglePlay(p: HTMLMediaElement): void {
  if (p.paused) void p.play();
  else p.pause();
}

/** Float-drag wiring; returns its cleanup. */
function initFloatDrag(fc: HTMLElement): () => void {
  let dragging = false;
  let startX = 0;
  let startY = 0;

  const pt = (ev: MouseEvent | TouchEvent) => {
    const t = (ev as TouchEvent).touches;
    return t && t.length
      ? { x: t[0].clientX, y: t[0].clientY }
      : { x: (ev as MouseEvent).clientX, y: (ev as MouseEvent).clientY };
  };
  const notOnButton = (ev: Event): boolean => {
    let t = ev.target as Node | null;
    while (t && t !== fc) {
      if ((t as HTMLElement).tagName === "BUTTON") return false;
      t = t.parentNode;
    }
    return true;
  };
  const onDown = (ev: MouseEvent | TouchEvent) => {
    if (!fc.classList.contains("active")) return;
    if (!notOnButton(ev)) return;
    dragging = true;
    const rect = fc.getBoundingClientRect();
    const p = pt(ev);
    startX = p.x - rect.left;
    startY = p.y - rect.top;
    fc.classList.add("dragging");
    fc.style.right = "";
    fc.style.bottom = "";
    fc.style.left = rect.left + "px";
    fc.style.top = rect.top + "px";
    ev.preventDefault();
  };
  const onMove = (ev: MouseEvent | TouchEvent) => {
    if (!dragging) return;
    const p = pt(ev);
    const maxL = window.innerWidth - fc.offsetWidth;
    const maxT = window.innerHeight - fc.offsetHeight;
    fc.style.left = Math.max(0, Math.min(p.x - startX, maxL)) + "px";
    fc.style.top = Math.max(0, Math.min(p.y - startY, maxT)) + "px";
    ev.preventDefault();
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    fc.classList.remove("dragging");
  };
  const opt = { passive: false } as AddEventListenerOptions;
  fc.addEventListener("mousedown", onDown as EventListener, opt);
  fc.addEventListener("touchstart", onDown as EventListener, opt);
  document.addEventListener("mousemove", onMove as EventListener, opt);
  document.addEventListener("touchmove", onMove as EventListener, opt);
  document.addEventListener("mouseup", onUp);
  document.addEventListener("touchend", onUp);
  return () => {
    fc.removeEventListener("mousedown", onDown as EventListener);
    fc.removeEventListener("touchstart", onDown as EventListener);
    document.removeEventListener("mousemove", onMove as EventListener);
    document.removeEventListener("touchmove", onMove as EventListener);
    document.removeEventListener("mouseup", onUp);
    document.removeEventListener("touchend", onUp);
  };
}

export function destroyVideoOverlay(): void {
  if (_cleanup) {
    _cleanup();
    _cleanup = null;
  }
  if (_ctrlTimer) clearTimeout(_ctrlTimer);
  _ctrlTimer = null;
}

/** Wire everything. Re-init safe (previous document/window listeners removed). */
export function initVideoOverlay(els: VideoOverlayEls): void {
  destroyVideoOverlay();
  _e = els;
  _floating = false;
  const undo: Array<() => void> = [];
  const on = (target: Document | Window, ev: string, fn: (e: Event) => void) => {
    target.addEventListener(ev, fn);
    undo.push(() => target.removeEventListener(ev, fn));
  };

  if (els.isVideoMode) {
    on(window, "resize", fixOverlaySize);
    fixOverlaySize();
  }

  if (els.closeBtn) {
    els.closeBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      closeVideoOverlay();
    });
  }
  if (els.miniExpandBtn) {
    els.miniExpandBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      openVideoOverlay();
    });
  }
  const mb = els.miniBar;
  if (mb) {
    mb.addEventListener("click", (ev) => {
      /* Clicking the bar (not its buttons) reopens the overlay */
      const t = ev.target as Node;
      if (els.miniPlayBtn && (t === els.miniPlayBtn || els.miniPlayBtn.contains(t))) return;
      if (els.miniExpandBtn && (t === els.miniExpandBtn || els.miniExpandBtn.contains(t))) return;
      openVideoOverlay();
    });
  }
  if (els.miniPlayBtn) {
    els.miniPlayBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      togglePlay(els.player);
    });
  }
  /* Tap on video area: toggle controls (ignore interactive children) + play/pause */
  if (els.isVideoMode && els.videoWrap) {
    els.videoWrap.addEventListener("click", (ev) => {
      const t = ev.target as Element;
      if (t.closest && t.closest("button")) return;
      toggleVidControls();
    });
    els.videoWrap.addEventListener("click", () => togglePlay(els.player));
  }

  /* Exit native fullscreen / Escape while overlay visible -> float player */
  const fsChange = () => {
    const d = document as Document & { webkitFullscreenElement?: Element | null };
    const fsEl = document.fullscreenElement || d.webkitFullscreenElement;
    if (!fsEl && els.overlay && !els.overlay.classList.contains("view-hidden") && els.player.currentSrc) {
      enterFloatPlayer();
    }
  };
  on(document, "fullscreenchange", fsChange);
  on(document, "webkitfullscreenchange", fsChange);
  on(document, "keydown", (ev) => {
    if (!els.isVideoMode) return;
    if ((ev as KeyboardEvent).key !== "Escape") return;
    if (els.overlay && !els.overlay.classList.contains("view-hidden") && !document.fullscreenElement) {
      enterFloatPlayer();
    }
  });

  if (els.floatCloseBtn) {
    els.floatCloseBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      els.player.pause();
      if (els.floatContainer) els.floatContainer.classList.remove("active");
      _floating = false;
      /* Move <video> back to overlay (hidden) */
      if (els.videoWrap) els.videoWrap.appendChild(els.player);
    });
  }
  if (els.floatExpandBtn) {
    els.floatExpandBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      exitFloatPlayer();
    });
  }
  if (els.floatContainer && els.isVideoMode) undo.push(initFloatDrag(els.floatContainer));

  /* Keep mini-bar play button icon in sync */
  els.player.addEventListener("play", syncMiniPlayBtn);
  els.player.addEventListener("pause", syncMiniPlayBtn);
  undo.push(() => {
    els.player.removeEventListener("play", syncMiniPlayBtn);
    els.player.removeEventListener("pause", syncMiniPlayBtn);
  });

  _cleanup = () => undo.forEach((f) => f());
}


