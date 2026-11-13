/**
 * URL routing / deep linking. Ported from `player_js/_library_tools.py`.
 * The URL mirrors the current view (view/path/id/track/q + sort/filter/view-mode
 * + tools panel) so reload / bookmarks / share-links restore navigation state.
 * Shared state via htState; UI filter state + view actions via hooks.
 */

import { getState } from "./stateBridge";

export interface UrlState {
  view: string;
  path: string;
  id: string;
  track: string;
  q: string;
  sort: string;
  fr: string;
  ff: string;
  fg: string;
  fh: string;
  vm: string;
  panel: string;
}

export interface UiState {
  rating: number;
  fav: boolean;
  genre: string;
  showHidden: boolean;
  viewMode: string;
}

export interface RouterHooks {
  getUi(): UiState;
  setUi(p: Partial<UiState>): void;
  toolsOpen(): boolean;
  openToolsPanel(): void;
  contentsAt(path: string): { files: LegacyMediaItem[] };
  itemsUnder(path: string): LegacyMediaItem[];
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean, startIndex?: number): void;
  showFolderView(): void;
  showUserPlaylistView(id: string): void;
  openOfflineLibrary(): void;
  globalSearch(q: string): void;
  markActive(): void;
  updateFilterChips(): void;
}

const KEYS = ["view", "path", "id", "track", "q", "sort", "fr", "ff", "fg", "fh", "vm", "panel"] as const;

function emptyState(): UrlState {
  return { view: "", path: "", id: "", track: "", q: "", sort: "", fr: "", ff: "", fg: "", fh: "", vm: "", panel: "" };
}

export function readUrl(search: string): UrlState {
  const p = new URLSearchParams(search);
  const s = emptyState();
  for (const k of KEYS) s[k] = p.get(k) || "";
  return s;
}

export function buildUrl(s: UrlState, pathname: string): string {
  const p = new URLSearchParams();
  for (const k of KEYS) if (s[k]) p.set(k, s[k]);
  const qs = p.toString();
  return pathname + (qs ? "?" + qs : "");
}

/** Key drives pushState vs replaceState: track/filter/sort changes share the key -> replace. */
export function stateKey(s: UrlState): string {
  return (s.view || "") + "|" + (s.path || "") + "|" + (s.id || "") + "|" + (s.q || "");
}

function lsSet(k: string, v: string): void {
  try {
    localStorage.setItem(k, v);
  } catch {
    /* quota / private mode */
  }
}

export interface Router {
  update(): void;
  restore(): void;
  init(): void;
}

export function createRouter(h: RouterHooks): Router {
  /* Stays true until restore() runs, else the initial showFolderView() would
     overwrite the deep-link URL the user reloaded with. */
  let suppress = true;
  let lastKey = "";

  function collectUiState(s: UrlState): UrlState {
    const sortField = document.getElementById("sort-field") as HTMLSelectElement | null;
    if (sortField && sortField.value && sortField.value !== "custom") s.sort = sortField.value;
    const ui = h.getUi();
    if (typeof ui.rating === "number" && ui.rating > 0) s.fr = String(ui.rating);
    if (ui.fav) s.ff = "1";
    if (ui.genre) s.fg = ui.genre;
    if (!ui.showHidden) s.fh = "0"; // default true -> encode only when disabled
    if (ui.viewMode && ui.viewMode !== "list") s.vm = ui.viewMode;
    try {
      if (h.toolsOpen()) s.panel = "tools";
    } catch {
      /* ignore */
    }
    return s;
  }

  function currentState(): UrlState {
    const s = emptyState();
    const st = getState();
    if (!st) return s;
    if (st.inPlaylist && st.filteredItems && st.currentIndex >= 0 && st.currentIndex < st.filteredItems.length) {
      const t = st.filteredItems[st.currentIndex];
      if (t && t.relative_path) s.track = t.relative_path;
    }
    if (st.globalSearchActive) {
      s.view = "search";
      const inp = document.getElementById("global-search-input") as HTMLInputElement | null;
      if (inp && inp.value) s.q = inp.value.trim();
      return collectUiState(s);
    }
    if (st.currentPath === "__offline__") {
      s.view = "offline";
      return collectUiState(s);
    }
    if (st.currentPlaylistId === "__favorites__") {
      s.view = "favorites";
      return collectUiState(s);
    }
    if (st.currentPlaylistId && st.currentPlaylistId !== "__folder__") {
      s.view = "userplaylist";
      s.id = st.currentPlaylistId;
      return collectUiState(s);
    }
    if (st.inPlaylist) {
      s.view = "playlist";
      s.path = st.currentPath || "";
      return collectUiState(s);
    }
    s.view = "folder";
    s.path = st.currentPath || "";
    return collectUiState(s);
  }

  function update(): void {
    if (suppress) return;
    const s = currentState();
    const url = buildUrl(s, window.location.pathname);
    const cur = window.location.pathname + window.location.search;
    const k = stateKey(s);
    if (url === cur) {
      lastKey = k;
      return;
    }
    try {
      if (k === lastKey) history.replaceState(s, "", url);
      else history.pushState(s, "", url);
    } catch {
      /* ignore */
    }
    lastKey = k;
  }

  function markTrack(trackRp: string): void {
    const st = getState();
    if (!trackRp || !st || !st.filteredItems || !st.filteredItems.length) return;
    const i = st.filteredItems.findIndex((it) => it && it.relative_path === trackRp);
    if (i >= 0) {
      st.currentIndex = i;
      h.markActive();
    }
  }

  /** URL wins over localStorage; absent param leaves saved default untouched. */
  function applyUiStateFromUrl(u: UrlState): void {
    const sortField = document.getElementById("sort-field") as HTMLSelectElement | null;
    if (u.sort && sortField) {
      try {
        sortField.value = u.sort;
      } catch {
        /* unknown option */
      }
    }
    if (u.fr !== "") {
      const fr = parseInt(u.fr, 10);
      if (!isNaN(fr) && fr >= 0 && fr <= 5) {
        h.setUi({ rating: fr });
        lsSet("ht-filter-rating", String(fr));
      }
    }
    if (u.ff !== "") {
      const fav = u.ff === "1";
      h.setUi({ fav });
      lsSet("ht-filter-fav", fav ? "1" : "0");
    }
    if (u.fg !== "") {
      h.setUi({ genre: u.fg });
      lsSet("ht-filter-genre", u.fg);
    }
    if (u.fh !== "") {
      const sh = u.fh !== "0";
      h.setUi({ showHidden: sh });
      lsSet("ht-show-hidden", sh ? "1" : "0");
    }
    if (u.vm === "grid" || u.vm === "list") {
      h.setUi({ viewMode: u.vm });
      lsSet("ht-view-mode", u.vm);
    }
    try {
      h.updateFilterChips();
    } catch {
      /* ignore */
    }
  }

  function applyPanelFromUrl(u: UrlState): void {
    if (u.panel === "tools") {
      try {
        h.openToolsPanel();
      } catch {
        /* ignore */
      }
    }
  }

  function restore(): void {
    const u = readUrl(window.location.search);
    const st = getState();
    if (!st) {
      suppress = false;
      return;
    }
    applyUiStateFromUrl(u);

    /* Legacy ?id= deep link -> auto-play */
    if (!u.view && u.id && st.allItems.length) {
      const target = st.allItems.find((it) => it.relative_path === u.id);
      if (target) {
        const slash = u.id.lastIndexOf("/");
        const parent = slash > 0 ? u.id.substring(0, slash) : "";
        suppress = true;
        try {
          st.currentPath = parent;
          const c = h.contentsAt(parent);
          const siblings = c.files.length ? c.files : h.itemsUnder(parent);
          const idx = siblings.findIndex((it) => it.relative_path === u.id);
          h.showPlaylist(siblings, true, idx >= 0 ? idx : 0);
        } finally {
          suppress = false;
        }
        applyPanelFromUrl(u);
        update();
        return;
      }
      suppress = false;
      return;
    }

    if (!u.view) {
      suppress = false;
      applyPanelFromUrl(u);
      return;
    }

    suppress = true;
    try {
      if (u.view === "offline") {
        h.openOfflineLibrary();
        /* offline list loads async -> defer track marker */
        if (u.track) setTimeout(() => markTrack(u.track), 200);
      } else if (u.view === "favorites") {
        h.showUserPlaylistView("__favorites__");
        markTrack(u.track);
      } else if (u.view === "userplaylist" && u.id) {
        h.showUserPlaylistView(u.id);
        markTrack(u.track);
      } else if (u.view === "playlist") {
        st.currentPath = u.path || "";
        const pc = h.contentsAt(st.currentPath);
        const pItems = pc.files.length ? pc.files : h.itemsUnder(st.currentPath);
        if (pItems.length) {
          let pStart = 0;
          if (u.track) {
            const pi = pItems.findIndex((it) => it.relative_path === u.track);
            if (pi >= 0) pStart = pi;
          }
          h.showPlaylist(pItems, false, pStart);
          markTrack(u.track);
        } else {
          h.showFolderView();
        }
      } else if (u.view === "search" && u.q) {
        st.currentPath = "";
        h.showFolderView();
        const inp = document.getElementById("global-search-input") as HTMLInputElement | null;
        if (inp) inp.value = u.q;
        h.globalSearch(u.q);
        markTrack(u.track);
      } else {
        st.currentPath = u.path || "";
        h.showFolderView();
      }
    } finally {
      suppress = false;
    }
    applyPanelFromUrl(u);
    /* Reflect actually-restored state (e.g. fallback to folder view) */
    update();
  }

  function init(): void {
    /* Back/forward -> re-render; final update() is a no-op (URL already matches). */
    window.addEventListener("popstate", () => restore());
  }

  return { update, restore, init };
}

