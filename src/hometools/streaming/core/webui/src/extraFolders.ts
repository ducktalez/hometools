/**
 * Extra library folders (video only): user-added folders outside the main
 * library root, shown as virtual top-level folders (alias = folder name).
 * Backend: `core/extra_folders.py` + `/api/video/folders`.
 *
 * Ported from `player_js/_queue.py` (_loadExtraFolders/addExtraFolder/
 * removeExtraFolder) + `_folder_browse.py` (root placeholders + badge).
 * Alias list is private state here; legacy reads it via `extraFolderAliases()`.
 */

import { getState } from "./stateBridge";
import type { FolderEntry } from "./folderContents";

export interface ExtraFolderHooks {
  /** API_PATH minus last segment, e.g. "/api/video". */
  apiBase: string;
  isVideo: boolean;
  toast(msg: string): void;
  refreshCatalog(): void;
  showFolderView(): void;
}

let aliases: string[] = [];

export function extraFolderAliases(): string[] {
  return aliases;
}

/** Test helper / reset. */
export function _setExtraFolderAliases(a: string[]): void {
  aliases = a;
}

const api = (h: ExtraFolderHooks): string => h.apiBase + "/folders";

/** Load alias list; with `cb` calls it afterwards, else re-renders root when the list changed. */
export function loadExtraFolders(h: ExtraFolderHooks, cb?: () => void): Promise<void> {
  if (!h.isVideo) {
    if (cb) cb();
    return Promise.resolve();
  }
  return fetch(api(h))
    .then((r) => (r.ok ? r.json() : { items: [] }))
    .then((d: { items?: Array<{ alias: string }> }) => {
      const next = (d.items || []).map((f) => f.alias);
      const changed = next.join("|") !== aliases.join("|");
      aliases = next;
      if (cb) {
        cb();
        return;
      }
      const s = getState();
      if (changed && s && !s.inPlaylist && !s.currentPath && s.allItems.length) h.showFolderView();
    })
    .catch(() => {
      if (cb) cb();
    });
}

export function addExtraFolder(h: ExtraFolderHooks): void {
  const path = prompt("Pfad des Ordners (auf dem Server erreichbar):");
  if (!path || !path.trim()) return;
  fetch(api(h), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: path.trim() }),
  })
    .then((r) =>
      r.text().then((t) => {
        let d: { detail?: unknown; folder?: { alias: string } } | null = null;
        try {
          d = JSON.parse(t);
        } catch {
          /* non-JSON body */
        }
        return { ok: r.ok, status: r.status, d };
      })
    )
    .then((x) => {
      if (!x.ok) {
        let det = x.d && x.d.detail;
        if (typeof det !== "string") {
          det = "HTTP " + x.status + (x.status === 404 || x.status === 405 ? " (Server neu starten?)" : "");
        }
        h.toast(det as string);
        return;
      }
      h.toast('Ordner "' + (x.d && x.d.folder ? x.d.folder.alias : "") + '" hinzugef\u00fcgt');
      void loadExtraFolders(h, () => h.refreshCatalog());
    })
    .catch((err) => h.toast("Ordner konnte nicht hinzugef\u00fcgt werden: " + ((err && err.message) || err)));
}

export function removeExtraFolder(h: ExtraFolderHooks): void {
  fetch(api(h))
    .then((r) => (r.ok ? r.json() : { items: [] }))
    .then((d: { items?: Array<{ alias: string }> }) => {
      const names = (d.items || []).map((f) => f.alias);
      if (!names.length) {
        h.toast("Keine hinzugef\u00fcgten Ordner");
        return;
      }
      const picked = prompt("Ordner entfernen (Dateien bleiben erhalten):\n" + names.join("\n"), names[0]);
      if (!picked || !picked.trim()) return;
      const alias = picked.trim();
      return fetch(api(h) + "?alias=" + encodeURIComponent(alias), { method: "DELETE" }).then((r) => {
        if (!r.ok) {
          h.toast("Ordner nicht gefunden");
          return;
        }
        h.toast("Ordner entfernt");
        const s = getState();
        if (s && (s.currentPath === alias || s.currentPath.indexOf(alias + "/") === 0)) s.currentPath = "";
        void loadExtraFolders(h, () => h.refreshCatalog());
      });
    })
    .catch(() => h.toast("Fehler beim Entfernen"));
}

/** Root only: append empty extra folders (no items yet) so they stay visible. Mutates `folders`. */
export function addExtraFolderPlaceholders(folders: FolderEntry[], names: string[]): FolderEntry[] {
  const have: Record<string, boolean> = {};
  folders.forEach((f) => (have[f.name] = true));
  names.forEach((a) => {
    if (have[a]) return;
    folders.push({
      name: a,
      displayName: a,
      isFavorite: false,
      count: 0,
      thumbnail_url: "",
      thumbnail_lg_url: "",
      languages: [],
      subLang: "",
      variants: null,
    });
  });
  return folders;
}

const BADGE_SVG =
  '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M19 11H7.83l4.88-4.88-1.42-1.41L4 12l7.29 7.29 1.42-1.41L7.83 13H19z" transform="rotate(180 12 12)"/></svg> Extern';

/** Root only: class + badge on cards of extra folders. */
export function markExtraFolderCards(grid: ParentNode, names: string[]): void {
  grid.querySelectorAll<HTMLElement>(".folder-card[data-folder]").forEach((card) => {
    if (names.indexOf(card.dataset.folder || "") < 0 || card.classList.contains("extra-folder")) return;
    card.classList.add("extra-folder");
    const b = document.createElement("span");
    b.className = "extra-folder-badge";
    b.title = "Zus\u00e4tzlicher Ordner (au\u00dferhalb der Bibliothek)";
    b.innerHTML = BADGE_SVG;
    card.appendChild(b);
  });
}

