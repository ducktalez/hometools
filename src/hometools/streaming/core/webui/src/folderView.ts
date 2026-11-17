/**
 * Folder-grid view (`showFolderView`) — ported from
 * `player_js/_folder_browse.py`. State via htState (inPlaylist,
 * currentPlaylistId, globalSearchActive, currentPath, allItems, userPlaylists,
 * savedFavorites); DOM container, config flags and cross-view actions via
 * `FolderViewHooks`.
 */

import { getState } from "./stateBridge";
import { wasDrag } from "./clickGuard";
import { toolsRowHtml, favoritesCardHtml, playlistCardHtml } from "./rootCards";
import { folderCardHtml, fileCardHtml } from "./folderCards";
import type { FolderCardOpts } from "./folderCards";
import type { FolderContents, FolderVariant } from "./folderContents";
import { extraFolderAliases, addExtraFolderPlaceholders, markExtraFolderCards } from "./extraFolders";
import { evaluateSmartPlaylist } from "./smartPlaylist";
import type { UserPlaylist } from "./smartPlaylist";
import { closeLangPicker, playlistCtxMenuItems } from "./folderBrowseUi";
import { openCtxMenu } from "./ctxMenu";

export interface FolderViewIcons {
  smartPlaylist: string;
  playlist: string;
  dl: string;
  refresh: string;
  star: string;
  folderPlay: string;
  dots: string;
  edit: string;
  trash: string;
}

export interface FolderViewHooks {
  folderGrid: HTMLElement;
  itemNoun: string;
  defaultLang: string;
  playlistsEnabled: boolean;
  offlineEnabled: boolean;
  recentEnabled: boolean;
  playlistsApiPath: string;
  icons: FolderViewIcons;
  esc(s: unknown): string;
  toast(msg: string): void;
  /** Card option bag (view mode, flags, placeholders, badge renderers). */
  cardOpts(showOrigNames: boolean): FolderCardOpts;
  toolActive(): boolean;
  contentsAt(path: string): FolderContents;
  destroyPlaylistDragDrop(): void;
  clearMoveGhosts(): void;
  enterFolderGridView(opts: { playAllDisabled?: boolean; trackCount?: string; contentHtml?: string }): void;
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean, startIdx?: number): void;
  loadRecentlyPlayed(): void;
  openOfflineLibrary(): void;
  updateOfflineFolderCount(): void;
  showUserPlaylistView(plId: string): void;
  playUserPlaylist(plId: string): void;
  openSmartPlaylistEditor(pl: UserPlaylist | null): void;
  refreshSmartPlaylist(plId: string): void;
  renameUserPlaylist(plId: string): void;
  deleteUserPlaylist(plId: string): void;
  navigateInto(name: string): void;
  playAllIn(name: string): void;
  showLangPicker(card: HTMLElement, variants: FolderVariant[], playMode: boolean): void;
  triggerSilentRefresh(): void;
}

/** Kebab menu of a playlist card (rename/delete, smart: refresh + edit rules). */
export function openPlaylistCtxMenu(btn: HTMLElement, plId: string, h: FolderViewHooks): void {
  const st = getState();
  const pl = st ? (st.userPlaylists as UserPlaylist[]).find((p) => p.id === plId) : undefined;
  if (!pl) return;
  openCtxMenu(
    btn,
    playlistCtxMenuItems(pl, {
      refresh: h.refreshSmartPlaylist,
      editRules: (p) => h.openSmartPlaylistEditor(p),
      rename: h.renameUserPlaylist,
      remove: h.deleteUserPlaylist,
      icEdit: h.icons.edit,
      icTrash: h.icons.trash,
    }),
    h.esc
  );
}

function wirePlaylistCards(h: FolderViewHooks): void {
  const grid = h.folderGrid;
  grid.querySelectorAll<HTMLElement>(".playlist-folder-card").forEach((card) => {
    const playBtn = card.querySelector<HTMLElement>(".playlist-cover-play-btn");
    const kebabBtn = card.querySelector<HTMLElement>(".playlist-folder-kebab");
    const id = (): string => card.dataset.playlistId || "";
    card.addEventListener("click", (e) => {
      if (wasDrag(e)) return;
      const t = e.target as HTMLElement;
      if (t.closest(".playlist-cover-play-btn") || t.closest(".playlist-folder-kebab")) return;
      h.showUserPlaylistView(id());
    });
    playBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      if (wasDrag(e)) return;
      h.playUserPlaylist(id());
    });
    kebabBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      if (wasDrag(e)) return;
      openPlaylistCtxMenu(kebabBtn, id(), h);
    });
  });

  document.getElementById("playlist-new-card")?.addEventListener("click", () => {
    const name = prompt("Playlist-Name:");
    if (!name || !name.trim()) return;
    fetch(h.playlistsApiPath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((d: { playlist?: UserPlaylist & { name: string } }) => {
        const st = getState();
        if (d.playlist && st) {
          st.userPlaylists.unshift(d.playlist);
          showFolderView(h);
          h.toast('Playlist "' + d.playlist.name + '" erstellt');
        } else {
          h.toast("Fehler beim Erstellen");
        }
      })
      .catch(() => h.toast("Fehler beim Erstellen"));
  });
  document.getElementById("smart-playlist-new-card")?.addEventListener("click", () => h.openSmartPlaylistEditor(null));
}

function wireFolderCards(h: FolderViewHooks): void {
  h.folderGrid
    .querySelectorAll<HTMLElement>(
      ".folder-card:not(.file-card):not(.offline-folder-card):not(.playlist-folder-card):not(.playlist-new-card)"
    )
    .forEach((card) => {
      const playBtn = card.querySelector<HTMLElement>(".folder-play-btn");
      const variants: FolderVariant[] | null = card.dataset.variants ? JSON.parse(card.dataset.variants) : null;
      const multi = !!variants && variants.length > 1;

      card.querySelectorAll<HTMLElement>(".lang-select-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          if (wasDrag(e)) return;
          if (btn.dataset.variantName) h.navigateInto(btn.dataset.variantName);
        });
      });

      card.addEventListener("click", (e) => {
        if (wasDrag(e)) return;
        const t = e.target as HTMLElement;
        if (t.closest(".folder-play-btn") || t.closest(".lang-select-btn")) return;
        if (multi) {
          /* default-language variant, else first */
          const def = variants!.find((v) => v.lang === h.defaultLang);
          h.navigateInto(def ? def.name : card.dataset.folder || "");
        } else {
          h.navigateInto(card.dataset.folder || "");
        }
      });
      playBtn?.addEventListener("click", (e) => {
        e.stopPropagation();
        if (wasDrag(e)) return;
        if (multi) h.showLangPicker(card, variants!, true);
        else h.playAllIn(card.dataset.folder || "");
      });
    });
}

export function showFolderView(h: FolderViewHooks): void {
  const st = getState();
  if (!st) return;
  h.destroyPlaylistDragDrop();
  closeLangPicker();
  st.inPlaylist = false;
  st.currentPlaylistId = "";
  st.globalSearchActive = false;
  h.clearMoveGhosts();
  const refreshInfo = document.getElementById("refresh-info");
  if (refreshInfo) refreshInfo.textContent = "";

  const c = h.contentsAt(st.currentPath);
  const isRoot = !st.currentPath;
  const showOrigNames = h.toolActive();
  const isVideo = h.itemNoun === "video";

  /* Extra library folders (video) */
  const xAliases = extraFolderAliases();
  if (isRoot && xAliases.length) addExtraFolderPlaceholders(c.folders, xAliases);

  if (c.folders.length === 0 && c.files.length === 0) {
    h.enterFolderGridView({
      playAllDisabled: true,
      trackCount: "",
      contentHtml: '<div class="empty-hint">No items found. Run a sync first.</div>',
    });
    return;
  }
  /* Leaf folder (no sub-folders) -> playlist */
  if (c.folders.length === 0) {
    h.showPlaylist(c.files, false);
    return;
  }

  let label = c.folders.length + " folder" + (c.folders.length !== 1 ? "s" : "");
  if (c.files.length > 0) {
    label += ", " + c.files.length + " " + (c.files.length !== 1 ? h.itemNoun + "s" : h.itemNoun);
  }
  h.enterFolderGridView({ trackCount: label });

  const ic = h.icons;
  let html = toolsRowHtml({
    isRoot,
    playlistsEnabled: h.playlistsEnabled,
    offlineEnabled: h.offlineEnabled,
    isVideo,
    allItemsCount: st.allItems.length,
    icSmartPlaylist: ic.smartPlaylist,
    icPlaylist: ic.playlist,
    icDl: ic.dl,
    icRefresh: ic.refresh,
  });

  const playlistCards = isRoot && h.playlistsEnabled;
  if (playlistCards) {
    const favs = st.savedFavorites;
    const favCount = st.allItems.filter((t) => !!favs[t.relative_path]).length;
    html += favoritesCardHtml(favCount, ic.star, ic.folderPlay);
    const playlists = st.userPlaylists as UserPlaylist[];
    playlists.forEach((pl) => {
      const isSmart = !!(pl.smart && pl.smart.rules);
      const cnt = isSmart
        ? evaluateSmartPlaylist(pl, st.allItems, playlists, favs).length
        : ((pl as { items?: string[] }).items || []).length;
      html += playlistCardHtml(pl as never, cnt, {
        escHtml: h.esc,
        icPlaylist: ic.playlist,
        icSmartPlaylist: ic.smartPlaylist,
        icFolderPlay: ic.folderPlay,
        icDots: ic.dots,
      });
    });
  }

  const opts = h.cardOpts(showOrigNames);
  c.folders.forEach((f) => (html += folderCardHtml(f, opts)));
  c.files.forEach((it, i) => (html += fileCardHtml(it, i, opts)));
  h.folderGrid.innerHTML = html;

  if (isRoot && xAliases.length) markExtraFolderCards(h.folderGrid, xAliases);

  const offCard = document.getElementById("offline-folder-card");
  if (offCard) {
    offCard.addEventListener("click", () => h.openOfflineLibrary());
    h.updateOfflineFolderCount();
  }

  if (playlistCards) wirePlaylistCards(h);

  /* Recently played: root only, catalog loaded, enabled */
  if (h.recentEnabled && isRoot && st.allItems.length > 0) {
    h.loadRecentlyPlayed();
  } else {
    const rs = document.getElementById("recent-section");
    if (rs) rs.hidden = true;
  }

  wireFolderCards(h);

  const looseFiles = c.files;
  h.folderGrid.querySelectorAll<HTMLElement>(".file-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (wasDrag(e)) return;
      h.triggerSilentRefresh(); /* freshest data on playlist entry */
      h.showPlaylist(looseFiles, true, Number(card.dataset.fileIdx));
    });
  });
}

