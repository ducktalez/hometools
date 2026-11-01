/**
 * Metadata edit modal (title/artist/album + rating stars).
 * Ported from `player_js/_library_tools.py` (renderEditModalRating,
 * _initEditModalRatingEvents, openEditModal, closeEditModal, submitEditModal).
 * `_editModalRating` was private to this block -> module-private here.
 */

import { getState } from "./stateBridge";
import { editModalRatingStars, toggleEditRating } from "./playerControls";

export interface EditModalHooks {
  metadataEditEnabled: boolean;
  ratingWriteEnabled: boolean;
  metadataEditPath: string;
  ratingApiPath: string;
  icStarFilled: string;
  icStarEmpty: string;
  toast(msg: string): void;
  applyFilter(): void;
  renderPlayerRating(stars: number): void;
  rebuildShuffleQueue(idx: number): void;
  setPlayerText(title: string, artist: string): void;
}

let _editModalRating = 0;

function input(id: string): HTMLInputElement | null {
  return document.getElementById(id) as HTMLInputElement | null;
}

export function renderEditModalRating(stars: number, h: EditModalHooks): void {
  const container = document.getElementById("edit-modal-rating");
  if (!container) return;
  const view = editModalRatingStars(stars);
  _editModalRating = view.rounded;
  container.innerHTML = "";
  view.stars.forEach((sv) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "edit-modal-rating-star" + (sv.active ? " active" : "");
    btn.innerHTML = sv.active ? h.icStarFilled : h.icStarEmpty;
    btn.dataset.star = String(sv.star);
    btn.title = sv.title;
    container.appendChild(btn);
  });
}

/** Wire hover/click on the modal's star row. Call once at startup. */
export function initEditModalRatingEvents(h: EditModalHooks): void {
  const container = document.getElementById("edit-modal-rating");
  if (!container) return;
  container.addEventListener("mouseover", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>(".edit-modal-rating-star");
    if (!btn) return;
    const n = parseInt(btn.dataset.star || "0", 10);
    container.querySelectorAll(".edit-modal-rating-star").forEach((b, i) => b.classList.toggle("hover", i < n));
  });
  container.addEventListener("mouseleave", () => {
    container.querySelectorAll(".edit-modal-rating-star").forEach((b) => b.classList.remove("hover"));
  });
  container.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>(".edit-modal-rating-star");
    if (!btn) return;
    const n = parseInt(btn.dataset.star || "0", 10);
    renderEditModalRating(toggleEditRating(n, _editModalRating), h);
  });
}

export function openEditModal(idx: number, h: EditModalHooks): void {
  const s = getState();
  if (!s || !h.metadataEditEnabled) return;
  const t = s.filteredItems[idx];
  const backdrop = document.getElementById("edit-modal-backdrop");
  if (!t || !backdrop) return;
  const titleIn = input("edit-modal-title-input");
  const artistIn = input("edit-modal-artist-input");
  const albumIn = input("edit-modal-album-input");
  const pathIn = input("edit-modal-path");
  const idxIn = input("edit-modal-idx");
  if (!titleIn || !artistIn || !albumIn || !pathIn || !idxIn) return;
  titleIn.value = t.title || "";
  artistIn.value = t.artist || "";
  albumIn.value = "";
  pathIn.value = t.relative_path || "";
  idxIn.value = String(idx);
  const ratingField = document.getElementById("edit-modal-rating-field");
  if (h.ratingWriteEnabled) {
    if (ratingField) ratingField.style.display = "";
    renderEditModalRating(t.rating || 0, h);
  } else if (ratingField) {
    ratingField.style.display = "none";
  }
  backdrop.removeAttribute("hidden");
  document.body.classList.add("modal-open");
  titleIn.focus();
}

export function closeEditModal(): void {
  const backdrop = document.getElementById("edit-modal-backdrop");
  if (backdrop) backdrop.setAttribute("hidden", "");
  document.body.classList.remove("modal-open");
}

export function submitEditModal(h: EditModalHooks): void {
  const s = getState();
  if (!s) return;
  const path = input("edit-modal-path")?.value || "";
  const idx = parseInt(input("edit-modal-idx")?.value || "-1", 10);
  const title = (input("edit-modal-title-input")?.value || "").trim();
  const artist = (input("edit-modal-artist-input")?.value || "").trim();
  const album = (input("edit-modal-album-input")?.value || "").trim();
  const saveBtn = document.getElementById("edit-modal-save-btn") as HTMLButtonElement | null;
  if (!path) return;
  if (saveBtn) saveBtn.disabled = true;

  const t = s.filteredItems[idx];
  const oldRating = t ? Math.round(t.rating || 0) : 0;
  const newRating = _editModalRating;
  const ratingChanged = h.ratingWriteEnabled && newRating !== oldRating;

  const post = (url: string, body: unknown) =>
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  const metaPromise = post(h.metadataEditPath, { path, title, artist, album: album || null }).then((r) => r.json());
  const ratingPromise = ratingChanged
    ? post(h.ratingApiPath, { path, rating: newRating }).then((r) => (r.ok ? r.json() : null))
    : Promise.resolve(null);

  Promise.all([metaPromise, ratingPromise])
    .then(([d, rd]: [{ ok?: boolean }, { ok?: boolean; rating?: number } | null]) => {
      if (saveBtn) saveBtn.disabled = false;
      if (!d.ok) {
        h.toast("Fehler beim Speichern");
        return;
      }
      const ratingOk = !!(rd && rd.ok);
      const updates: Partial<LegacyMediaItem> = { title, artist };
      if (ratingOk) updates.rating = rd!.rating;
      if (s.filteredItems[idx]) s.filteredItems[idx] = { ...s.filteredItems[idx], ...updates } as LegacyMediaItem;
      for (let i = 0; i < s.allItems.length; i++) {
        if (s.allItems[i].relative_path === path) {
          s.allItems[i] = { ...s.allItems[i], ...updates } as LegacyMediaItem;
          break;
        }
      }
      closeEditModal();
      h.applyFilter();
      if (idx === s.currentIndex) {
        h.setPlayerText(title, artist);
        if (ratingOk) h.renderPlayerRating(rd!.rating || 0);
      }
      if (ratingOk && s.shuffleMode === "weighted") h.rebuildShuffleQueue(s.currentIndex);
      h.toast("Gespeichert \u2713");
    })
    .catch(() => {
      if (saveBtn) saveBtn.disabled = false;
      h.toast("Netzwerkfehler beim Speichern");
    });
}

