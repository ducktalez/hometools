/**
 * Track picker for (empty) manual playlists: green "Titel hinzufuegen" button
 * in the empty view + searchable modal that adds library items one by one.
 * Reuses the playlist-modal styles; DOM is built on demand.
 */

import { getState } from "./stateBridge";

export const PICKER_LIMIT = 100;
export const ADD_BTN_ID = "pl-add-tracks-btn";

interface PlaylistRef {
  id: string;
  name?: string;
  items?: string[];
  smart?: unknown;
}

function playlistById(id: string): PlaylistRef | undefined {
  const st = getState();
  return ((st ? st.userPlaylists : []) as PlaylistRef[]).find((p) => p.id === id);
}

/** Id of the manual (non-smart) user playlist currently shown and still empty, else "". */
export function emptyManualPlaylistId(): string {
  const st = getState();
  if (!st || !st.inPlaylist || !st.currentPlaylistId || st.currentPlaylistId.startsWith("__")) return "";
  if (st.playlistItems.length > 0) return "";
  const pl = playlistById(st.currentPlaylistId);
  return pl && !pl.smart ? pl.id : "";
}

/** Empty-state row with the green add button. */
export function emptyPlaylistHtml(): string {
  return (
    '<li class="empty-hint">Diese Playlist ist leer.<br>' +
    '<button type="button" class="btn-add-tracks" id="' +
    ADD_BTN_ID +
    '">Titel hinzuf\u00fcgen</button></li>'
  );
}

/** True when a manual (non-smart, non-virtual) user playlist is currently shown. */
export function isManualPlaylistView(): boolean {
  const st = getState();
  if (!st || !st.inPlaylist || !st.currentPlaylistId || st.currentPlaylistId.indexOf("__") === 0) return false;
  const pl = playlistById(st.currentPlaylistId);
  return !!pl && !pl.smart;
}

/**
 * Re-resolve playlist `plId` and re-render, but only while it is still the
 * view on screen (async add/remove callbacks may fire after navigation).
 */
export function reloadPlaylistView(
  plId: string,
  resolve: (id: string) => { resolved: LegacyMediaItem[] } | null,
  applyFilter: (force?: boolean) => void,
  force?: boolean
): void {
  const st = getState();
  if (!st || !st.inPlaylist || st.currentPlaylistId !== plId) return;
  const data = resolve(plId);
  st.playlistItems = data ? data.resolved : [];
  applyFilter(force);
}

/** Library items matching `needle` (title/artist/path), capped. */
export function pickerMatches(
  items: LegacyMediaItem[],
  needle: string,
  limit: number = PICKER_LIMIT
): { shown: LegacyMediaItem[]; total: number } {
  const n = (needle || "").trim().toLowerCase();
  const all = n
    ? items.filter((t) =>
        ((t.title || "") + " " + (t.artist || "") + " " + (t.relative_path || "")).toLowerCase().includes(n)
      )
    : items;
  return { shown: all.slice(0, limit), total: all.length };
}

export interface PickerHooks {
  playlistId: string;
  esc(s: unknown): string;
  addToPlaylist(plId: string, relativePath: string): void;
  /** Called after each add and on close (re-resolve + re-render the playlist view). */
  refresh(): void;
}

export function closeTrackPicker(): void {
  document.getElementById("track-picker-backdrop")?.remove();
}

export function openTrackPicker(h: PickerHooks): void {
  const st = getState();
  if (!st) return;
  closeTrackPicker();
  const backdrop = document.createElement("div");
  backdrop.className = "playlist-modal-backdrop";
  backdrop.id = "track-picker-backdrop";
  backdrop.innerHTML =
    '<div class="playlist-modal track-picker" role="dialog" aria-modal="true">' +
    '<div class="playlist-modal-heading">Titel hinzuf\u00fcgen</div>' +
    '<input class="track-picker-search" id="track-picker-search" type="search" placeholder="Suchen\u2026" autocomplete="off" />' +
    '<ul class="playlist-modal-list" id="track-picker-list"></ul>' +
    '<div class="track-picker-note" id="track-picker-note"></div>' +
    '<div class="playlist-modal-close"><button type="button" class="btn-add-tracks" id="track-picker-done">Fertig</button></div>' +
    "</div>";
  document.body.appendChild(backdrop);

  const list = backdrop.querySelector("#track-picker-list") as HTMLElement;
  const note = backdrop.querySelector("#track-picker-note") as HTMLElement;
  const search = backdrop.querySelector("#track-picker-search") as HTMLInputElement;

  const inPlaylist = (): Record<string, true> => {
    const pl = playlistById(h.playlistId);
    const set: Record<string, true> = Object.create(null);
    ((pl && pl.items) || []).forEach((rp) => (set[rp] = true));
    return set;
  };

  function render(): void {
    const { shown, total } = pickerMatches(st!.allItems, search.value);
    const added = inPlaylist();
    list.innerHTML = shown
      .map((t) => {
        const done = !!added[t.relative_path];
        return (
          '<li class="playlist-modal-item track-picker-item' +
          (done ? " is-added" : "") +
          '" data-path="' +
          h.esc(t.relative_path) +
          '"><span class="playlist-modal-item-name">' +
          h.esc(t.title || t.relative_path) +
          (t.artist ? ' <span class="playlist-modal-item-count">' + h.esc(t.artist) + "</span>" : "") +
          '</span><span class="playlist-modal-item-count">' +
          (done ? "Hinzugef\u00fcgt" : "Hinzuf\u00fcgen") +
          "</span></li>"
        );
      })
      .join("");
    note.textContent = total > shown.length ? "Zeige " + shown.length + " von " + total + " \u2014 Suche eingrenzen" : "";
  }

  list.addEventListener("click", (e) => {
    const li = (e.target as HTMLElement).closest<HTMLElement>(".track-picker-item");
    if (!li || li.classList.contains("is-added")) return;
    h.addToPlaylist(h.playlistId, li.dataset.path || "");
    h.refresh();
    render();
  });
  search.addEventListener("input", render);
  const close = (): void => {
    closeTrackPicker();
    h.refresh();
  };
  backdrop.querySelector("#track-picker-done")?.addEventListener("click", close);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });
  backdrop.addEventListener("keydown", (e) => {
    if ((e as KeyboardEvent).key === "Escape") close();
  });
  render();
  search.focus();
}

