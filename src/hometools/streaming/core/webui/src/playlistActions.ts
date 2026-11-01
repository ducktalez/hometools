/**
 * Playlist CRUD actions with optimistic UI — ported from
 * `player_js/_smart_playlists.py` (deleteUserPlaylist, renameUserPlaylist,
 * addToPlaylist, createAndAddToPlaylist).
 *
 * State via `htState.userPlaylists/playlistRevision` (see stateBridge.ts);
 * view/DOM side effects come in through `PlaylistHooks` so this module stays
 * free of legacy closure reads.
 */

import { getState } from "./stateBridge";
import { snapshotPlaylists, restorePlaylists } from "./playlistSync";

export interface PlaylistLike {
  id: string;
  name: string;
  items?: string[];
  [k: string]: unknown;
}

export interface PlaylistHooks {
  /** `PLAYLISTS_API_PATH` */
  apiPath: string;
  toast(msg: string): void;
  /** Re-render root folder view iff it is currently shown. */
  refreshRoot(): void;
  /** Close the add-to-playlist modal (addToPlaylist only). */
  closeModal?(): void;
}

function lists(): PlaylistLike[] {
  const st = getState();
  return st ? (st.userPlaylists as PlaylistLike[]) : [];
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function deleteUserPlaylist(plId: string, h: PlaylistHooks): void {
  const st = getState();
  if (!st) return;
  const pl = lists().find((p) => p.id === plId);
  const name = pl ? pl.name : "Playlist";
  if (!confirm('Playlist "' + name + '" wirklich löschen?')) return;
  const snap = snapshotPlaylists();
  st.userPlaylists = lists().filter((p) => p.id !== plId);
  h.refreshRoot();
  fetch(h.apiPath + "?id=" + encodeURIComponent(plId), { method: "DELETE" })
    .then((r) => r.json())
    .then((d) => {
      st.userPlaylists = d.items || [];
      if (typeof d.revision === "number") st.playlistRevision = d.revision;
      h.toast("Playlist gelöscht");
      h.refreshRoot();
    })
    .catch(() => {
      restorePlaylists(snap);
      h.toast("Fehler beim Löschen — rückgängig");
      h.refreshRoot();
    });
}

export function renameUserPlaylist(plId: string, h: PlaylistHooks): void {
  const pl = lists().find((p) => p.id === plId);
  if (!pl) return;
  const newName = prompt("Neuer Name:", pl.name);
  if (!newName || !newName.trim() || newName.trim() === pl.name) return;
  const trimmed = newName.trim();
  const oldName = pl.name;
  pl.name = trimmed; // optimistic
  h.refreshRoot();
  fetch(h.apiPath, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify({ playlist_id: plId, name: trimmed }),
  })
    .then((r) => {
      if (!r.ok) throw new Error();
      return r.json();
    })
    .then((d) => {
      if (d.playlist) {
        const l = lists();
        const i = l.findIndex((p) => p.id === plId);
        if (i >= 0) l[i] = d.playlist;
      }
      h.toast("Playlist umbenannt");
      h.refreshRoot();
    })
    .catch(() => {
      pl.name = oldName;
      h.toast("Fehler beim Umbenennen");
      h.refreshRoot();
    });
}

export function addToPlaylist(plId: string, relativePath: string, h: PlaylistHooks): void {
  const snap = snapshotPlaylists();
  const localPl = lists().find((p) => p.id === plId);
  if (localPl && (localPl.items || []).indexOf(relativePath) < 0) {
    localPl.items = (localPl.items || []).slice();
    localPl.items.push(relativePath);
  }
  if (h.closeModal) h.closeModal();
  h.toast("Zur Playlist hinzugefügt");
  fetch(h.apiPath + "/items", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ playlist_id: plId, relative_path: relativePath }),
  })
    .then((r) => r.json())
    .then((d) => {
      if (d.playlist) {
        const l = lists();
        const idx = l.findIndex((p) => p.id === plId);
        if (idx >= 0) l[idx] = d.playlist;
      }
    })
    .catch(() => {
      restorePlaylists(snap);
      h.toast("Fehler beim Hinzufügen — rückgängig");
    });
}

export function createAndAddToPlaylist(name: string, relativePath: string, h: PlaylistHooks): void {
  fetch(h.apiPath, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ name }),
  })
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then((d) => {
      if (d.playlist) {
        lists().unshift(d.playlist);
        addToPlaylist(d.playlist.id, relativePath, h);
      } else {
        h.toast("Fehler beim Erstellen");
      }
    })
    .catch(() => h.toast("Fehler beim Erstellen"));
}

