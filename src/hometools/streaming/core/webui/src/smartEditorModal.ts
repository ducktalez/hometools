/**
 * Smart-playlist editor modal shell + "add to playlist" modal list.
 * Ported from `_smart_playlists.py::_smartRenderEditor` (markup half) and
 * `renderPlaylistModalList` (markup half). Wiring stays legacy.
 */

import { smartRenderRuleRow } from "./smartPlaylist";
import type { SmartEditorState, UserPlaylist } from "./smartPlaylist";

type Esc = (s: unknown) => string;

export function smartEditorModalHtml(
  s: SmartEditorState,
  userPlaylists: UserPlaylist[],
  esc: Esc,
  icSmartPlaylist: string
): string {
  const rulesHtml = s.rules.map((r, i) => smartRenderRuleRow(r, i, userPlaylists, s.id, esc)).join("");
  return (
    '<div class="smart-editor-backdrop" id="smart-editor-backdrop">' +
    '<div class="smart-editor-modal" role="dialog" aria-modal="true">' +
    '<div class="smart-editor-header">' +
    "<span>" + icSmartPlaylist + " Intelligente Playlist</span>" +
    '<button type="button" class="smart-editor-close" id="smart-editor-close" title="Schlie\u00dfen">\u00d7</button>' +
    "</div>" +
    '<div class="smart-editor-body">' +
    '<label class="smart-editor-label">Name' +
    '<input type="text" id="smart-editor-name" value="' + esc(s.name) + '" placeholder="Best of Rock">' +
    "</label>" +
    '<div class="smart-editor-match">' +
    '<label><input type="radio" name="smart-match" value="all"' + (s.match === "all" ? " checked" : "") + "> Alle Regeln erf\u00fcllen (UND)</label>" +
    '<label><input type="radio" name="smart-match" value="any"' + (s.match === "any" ? " checked" : "") + "> Eine Regel erf\u00fcllen (ODER)</label>" +
    "</div>" +
    '<div class="smart-editor-rules" id="smart-editor-rules">' + rulesHtml + "</div>" +
    '<button type="button" class="smart-editor-add" id="smart-editor-add-rule">+ Regel hinzuf\u00fcgen</button>' +
    '<label class="smart-editor-label">Begrenzen auf (optional)' +
    '<input type="number" id="smart-editor-limit" value="' + esc(String(s.limit)) + '" placeholder="0 = unbegrenzt">' +
    "</label>" +
    "</div>" +
    '<div class="smart-editor-footer">' +
    '<button type="button" class="smart-editor-cancel" id="smart-editor-cancel">Abbrechen</button>' +
    '<button type="button" class="smart-editor-save" id="smart-editor-save">Speichern</button>' +
    "</div>" +
    "</div>" +
    "</div>"
  );
}

export function playlistModalListHtml(userPlaylists: UserPlaylist[], esc: Esc): string {
  if (!userPlaylists.length) {
    return '<li style="padding:0.5rem;color:var(--sub);font-size:0.85rem">Noch keine Playlists. Erstelle eine neue!</li>';
  }
  return userPlaylists
    .map((pl) => {
      const cnt = (pl.items || []).length;
      return (
        '<li class="playlist-modal-item" data-id="' + esc(pl.id) + '">' +
        '<span class="playlist-modal-item-name">' + esc(pl.name) + "</span>" +
        '<span class="playlist-modal-item-count">' + cnt + " Titel</span></li>"
      );
    })
    .join("");
}

