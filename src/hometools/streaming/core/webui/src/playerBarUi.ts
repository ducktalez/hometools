/**
 * Player-bar wiring: rating-star hover/click + bar fullscreen button.
 * Ported from `player_js/_library_tools.py`. Zustandslos.
 */

export interface RatingEventsOpts {
  writeEnabled: boolean;
  /** Current track rating (0 if none). */
  currentRating(): number;
  setRating(stars: number): void;
}

/** Hover preview + click (clicking the set star clears to 0). */
export function initPlayerRatingEvents(o: RatingEventsOpts): void {
  const el = document.getElementById("player-rating");
  if (!el) return;
  const star = (t: EventTarget | null): HTMLElement | null =>
    (t as HTMLElement | null)?.closest<HTMLElement>(".player-rating-star") ?? null;
  el.addEventListener("mouseover", (e) => {
    const btn = star(e.target);
    if (!btn || !o.writeEnabled) return;
    const n = parseInt(btn.dataset.star || "0", 10);
    el.querySelectorAll(".player-rating-star").forEach((b, i) => b.classList.toggle("hover", i < n));
  });
  el.addEventListener("mouseleave", () => {
    el.querySelectorAll(".player-rating-star").forEach((b) => b.classList.remove("hover"));
  });
  el.addEventListener("click", (e) => {
    const btn = star(e.target);
    if (!btn || !o.writeEnabled) return;
    const clicked = parseInt(btn.dataset.star || "0", 10);
    const current = Math.round(o.currentRating() || 0);
    o.setRating(clicked === current ? 0 : clicked);
  });
}

type FsPlayer = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void;
  webkitRequestFullscreen?: () => void;
};
type FsDoc = Document & { webkitFullscreenEnabled?: boolean };

/** Show + wire `#btn-fs` (video only; native or iOS webkit fullscreen). */
export function initBarFullscreen(player: HTMLMediaElement, isVideoPlayer: boolean): void {
  const btn = document.getElementById("btn-fs") as HTMLButtonElement | null;
  if (!btn) return;
  const p = player as FsPlayer;
  const supported =
    isVideoPlayer &&
    !!(document.fullscreenEnabled || (document as FsDoc).webkitFullscreenEnabled || typeof p.webkitEnterFullscreen === "function");
  if (supported) btn.hidden = false;
  btn.addEventListener("click", () => {
    if (p.requestFullscreen) p.requestFullscreen().catch(() => {});
    else if (p.webkitRequestFullscreen) p.webkitRequestFullscreen();
  });
}

