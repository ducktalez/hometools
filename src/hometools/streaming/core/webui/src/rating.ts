/**
 * Player/list rating: star render, local patching, POST + undo toast.
 * Ported from `player_js/_library_tools.py` (renderPlayerRating,
 * _patchAllItemsRating, _updateTrackRatingBar, setRating,
 * showRatingToastWithUndo, undoRating). Just-rated timer private here;
 * `justRatedPath` read by legacy filter -> `htState.justRatedPath`.
 */

import { getState } from "./stateBridge";
import { playerRatingStars, ratingBarWidthPct } from "./playerControls";
import { replaceItemFields, indexOfPath, ratingToastLabel } from "./catalogQuery";

export interface RatingHooks {
  writeEnabled: boolean;
  ratingApiPath: string;
  auditUndoPath: string;
  icStarFilled: string;
  icStarEmpty: string;
  toast(msg: string): void;
  applyFilter(keepScroll: boolean): void;
  markActive(): void;
  rebuildShuffleQueue(idx: number): void;
}

type Item = LegacyMediaItem;
const JUST_RATED_MS = 5000;
let _justRatedTimer: ReturnType<typeof setTimeout> | null = null;

export function renderPlayerRating(stars: number, h: RatingHooks): void {
  const el = document.getElementById("player-rating");
  if (!el) return;
  el.innerHTML = "";
  playerRatingStars(stars).forEach((sv) => {
    const btn = document.createElement("button");
    btn.className = "player-rating-star" + (sv.active ? " active" : "");
    btn.innerHTML = sv.active ? h.icStarFilled : h.icStarEmpty;
    btn.dataset.star = String(sv.star);
    btn.title = sv.title;
    if (!h.writeEnabled) btn.style.pointerEvents = "none";
    el.appendChild(btn);
  });
  el.removeAttribute("hidden");
}

export function patchAllItemsRating(relativePath: string, rating: number): void {
  const s = getState();
  if (!s) return;
  replaceItemFields([s.allItems, s.playlistItems, s.filteredItems, s.userQueue], relativePath, { rating });
}

/** Update .rating-bar + inline stars of one list row without re-render. */
export function updateTrackRatingBar(idx: number, rating: number, h: RatingHooks): void {
  const li = document.querySelector<HTMLElement>('.track-item[data-index="' + idx + '"]');
  if (!li) return;
  const wrap = li.querySelector<HTMLElement>(".track-thumb-wrap");
  if (wrap) {
    let bar = wrap.querySelector<HTMLElement>(".rating-bar");
    const pct = ratingBarWidthPct(rating);
    if (pct > 0) {
      if (!bar) {
        bar = document.createElement("div");
        bar.className = "rating-bar";
        wrap.appendChild(bar);
      }
      bar.style.width = pct + "%";
    } else if (bar) {
      bar.remove();
    }
  }
  const container = li.querySelector<HTMLElement>(".track-inline-rating");
  if (container) {
    const rounded = Math.round(rating || 0);
    container.querySelectorAll<HTMLElement>(".track-inline-rating-star").forEach((b) => {
      const st = Number(b.dataset.star);
      b.className = "track-inline-rating-star" + (st <= rounded ? " active" : "");
      b.innerHTML = st <= rounded ? h.icStarFilled : h.icStarEmpty;
    });
  }
}

/** Keep rated track visible (grayed) until undo window ends. */
function armJustRated(path: string, h: RatingHooks): void {
  const s = getState();
  if (!s) return;
  s.justRatedPath = path;
  if (_justRatedTimer) clearTimeout(_justRatedTimer);
  _justRatedTimer = setTimeout(() => {
    s.justRatedPath = null;
    if (s.inPlaylist) h.applyFilter(true);
  }, JUST_RATED_MS);
}

export function setRating(stars: number, h: RatingHooks): void {
  const s = getState();
  if (!s || !h.writeEnabled) return;
  const t = s.filteredItems[s.currentIndex];
  if (!t) return;
  const prevRating = t.rating || 0;
  const ratedPath = t.relative_path;
  fetch(h.ratingApiPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: ratedPath, rating: stars }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((d: { ok?: boolean; rating?: number; entry_id?: string } | null) => {
      if (!d || !d.ok) return;
      const rating = d.rating || 0;
      t.rating = rating;
      patchAllItemsRating(ratedPath, rating);
      renderPlayerRating(rating, h);
      armJustRated(ratedPath, h);
      if (s.inPlaylist) {
        h.applyFilter(true);
        const relocated = indexOfPath(s.filteredItems, ratedPath);
        if (relocated >= 0) s.currentIndex = relocated;
        h.markActive();
      } else {
        updateTrackRatingBar(s.currentIndex, rating, h);
      }
      if (s.shuffleMode === "weighted") h.rebuildShuffleQueue(s.currentIndex);
      if (d.entry_id) showRatingToastWithUndo(stars, prevRating, d.entry_id, t, h);
      else h.toast(ratingToastLabel(stars));
    })
    .catch(() => {});
}

export function showRatingToastWithUndo(stars: number, prevStars: number, entryId: string, t: Item, h: RatingHooks): void {
  const toast = document.getElementById("toast") as (HTMLElement & { _hideTimer?: ReturnType<typeof setTimeout> }) | null;
  const label = ratingToastLabel(stars);
  if (!toast) {
    h.toast(label);
    return;
  }
  toast.innerHTML = "";
  const span = document.createElement("span");
  span.textContent = label;
  toast.appendChild(span);
  const undoBtn = document.createElement("button");
  undoBtn.textContent = "Rueckgaengig";
  undoBtn.style.cssText =
    "margin-left:0.5rem;background:none;border:1px solid #888;color:inherit;border-radius:4px;padding:1px 8px;cursor:pointer;font-size:0.8rem;";
  undoBtn.addEventListener("click", () => undoRating(undoBtn, entryId, prevStars, t, h));
  toast.appendChild(undoBtn);
  toast.classList.add("show");
  if (toast._hideTimer) clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("show"), JUST_RATED_MS);
}

export function undoRating(btn: HTMLButtonElement, entryId: string, prevStars: number, t: Item | null, h: RatingHooks): void {
  const s = getState();
  if (!s) return;
  btn.disabled = true;
  btn.textContent = "…";
  fetch(h.auditUndoPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_id: entryId }),
  })
    .then((r) => r.json())
    .then((d: { ok?: boolean; detail?: string }) => {
      const t2 = t || s.filteredItems[s.currentIndex];
      if (d.ok && t2) {
        t2.rating = prevStars;
        patchAllItemsRating(t2.relative_path, prevStars);
        const cur = s.currentIndex >= 0 ? s.filteredItems[s.currentIndex] : null;
        if (cur && cur.relative_path === t2.relative_path) renderPlayerRating(prevStars, h);
        armJustRated(t2.relative_path, h);
        if (s.inPlaylist) {
          h.applyFilter(true);
          h.markActive();
        } else {
          const idx2 = s.filteredItems.indexOf(t2);
          if (idx2 >= 0) updateTrackRatingBar(idx2, prevStars, h);
        }
        if (s.shuffleMode === "weighted") h.rebuildShuffleQueue(s.currentIndex);
      }
      const toast = document.getElementById("toast") as (HTMLElement & { _hideTimer?: ReturnType<typeof setTimeout> }) | null;
      if (toast) {
        toast.innerHTML = d.ok ? "Rückgängig gemacht ✓" : "Fehler: " + (d.detail || "?");
        if (toast._hideTimer) clearTimeout(toast._hideTimer);
        toast._hideTimer = setTimeout(() => toast.classList.remove("show"), 2500);
      }
    })
    .catch(() => h.toast("Netzwerkfehler beim Rückgängig"));
}

