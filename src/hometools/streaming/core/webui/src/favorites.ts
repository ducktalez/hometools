/**
 * Favorites (server-side "shortcuts"): load, pin-button sync, toggle.
 * Ported from `player_js/_library_tools.py` (loadFavorites,
 * updateFavoriteButtons, toggleFavorite). The `_savedFavorites` object is
 * shared with many legacy readers -> lives in legacy, accessed via
 * `htState.savedFavorites` (getter/setter pair).
 */

import { getState } from "./stateBridge";
import { favoriteBtnView } from "./playerControls";

export interface FavoritesHooks {
  /** API_PATH minus last segment, e.g. "/api/audio". */
  apiBase: string;
  toast(msg: string): void;
  applyFilter(): void;
  filterFavActive(): boolean;
}

export function updateFavoriteButtons(): void {
  const s = getState();
  if (!s) return;
  document.querySelectorAll<HTMLElement>(".track-pin-btn").forEach((btn) => {
    const v = favoriteBtnView(!!s.savedFavorites[btn.dataset.relativePath || ""]);
    btn.classList.toggle("pinned", v.pinned);
    btn.title = v.title;
  });
}

export function loadFavorites(h: FavoritesHooks): Promise<void> {
  const s = getState();
  if (!s) return Promise.resolve();
  return fetch(h.apiBase + "/shortcuts")
    .then((r) => (r.ok ? r.json() : null))
    .then((data: { items?: Array<{ id: string }> } | null) => {
      const fresh: Record<string, boolean> = {};
      if (data && Array.isArray(data.items)) data.items.forEach((x) => (fresh[x.id] = true));
      s.savedFavorites = fresh;
      updateFavoriteButtons();
      if (h.filterFavActive() && s.inPlaylist) h.applyFilter();
    })
    .catch(() => {});
}

export function toggleFavorite(
  item: { relative_path?: string; title?: string } | null,
  btn: HTMLElement | null,
  h: FavoritesHooks
): void {
  const s = getState();
  if (!s || !item || !item.relative_path) return;
  const rp = item.relative_path;
  if (s.savedFavorites[rp]) {
    fetch(h.apiBase + "/shortcuts?id=" + encodeURIComponent(rp), { method: "DELETE" })
      .then((r) => (r.ok ? r.json() : null))
      .then(() => {
        delete s.savedFavorites[rp];
        if (btn) {
          btn.classList.remove("pinned");
          btn.title = "Favorit";
        }
        h.toast("Favorit entfernt");
      })
      .catch(() => {});
    return;
  }
  fetch(h.apiBase + "/shortcuts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: rp,
      title: item.title || rp,
      icon: "/thumb?path=" + encodeURIComponent(rp),
    }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then(() => {
      s.savedFavorites[rp] = true;
      if (btn) {
        btn.classList.add("pinned");
        btn.title = "Favorit entfernen";
      }
      h.toast("Als Favorit gespeichert");
      const nav = navigator as Navigator & { maxTouchPoints?: number };
      if (nav.share && ("ontouchstart" in window || (nav.maxTouchPoints || 0) > 0)) {
        const deepUrl = window.location.origin + "/?id=" + encodeURIComponent(rp);
        setTimeout(() => {
          nav.share({ title: item.title || "Favorit", text: item.title || "", url: deepUrl }).catch(() => {});
        }, 600);
      }
    })
    .catch(() => h.toast("Favorit konnte nicht gespeichert werden"));
}


