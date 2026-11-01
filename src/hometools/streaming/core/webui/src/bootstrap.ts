/**
 * App bootstrap sequence — ported from the tail of
 * `player_js/_drag_drop_init.py`. Order matters: catalog -> router init ->
 * favorites -> user playlists -> router restore -> default root view ->
 * playlist sync. All steps via hooks; `currentPath`/`inPlaylist` via `htState`.
 */

import { getState } from "./stateBridge";

export interface BootstrapHooks {
  loadInitialCatalog(): Promise<unknown>;
  routerInit(): void;
  loadFavorites(): void;
  loadUserPlaylists(): Promise<unknown>;
  routerRestore(): void;
  showFolderView(): void;
  startPlaylistSync(): void;
}

export function bootstrapApp(h: BootstrapHooks): Promise<void> {
  return h.loadInitialCatalog().then(() => {
    h.routerInit();
    h.loadFavorites();
    return h.loadUserPlaylists().then(() => {
      // Restore view from URL once catalog + user playlists are ready.
      h.routerRestore();
      // Router is a no-op for clean URLs -> render root folder view.
      const st = getState();
      if (st && !st.currentPath && !st.inPlaylist) h.showFolderView();
      h.startPlaylistSync();
    });
  });
}

