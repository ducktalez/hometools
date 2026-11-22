/**
 *
 * of getter/setter closures over its `var`s. Reads are live, writes
 *
 * private state): use for functions coupled to *shared, reassigned*
 * globals like `filteredItems`/`shuffleQueue`. See IMPLEMENTATION_PLAN.md.
 *
 * per newly needed global.
 */

export interface HtState {
  allItems: CatalogItem[];
  filteredItems: CatalogItem[];
  playlistItems: CatalogItem[];
  currentIndex: number;
  currentPath: string;
  inPlaylist: boolean;
  shuffleMode: false | "normal" | "weighted";
  repeatMode: false | "all" | "one";
  shuffleQueue: number[];
  shufflePos: number;
  userQueue: CatalogItem[];
  userPlaylists: unknown[];
  playlistRevision: number;
  currentPlaylistId: string;
  playlistAddPath: string;
  globalSearchActive: boolean;
  savedFavorites: Record<string, boolean>;
  justRatedPath: string | null;
  currentStreamUrl: string;
}

/** State bridge or null before `startApp` ran. Callers must no-op then. */
export function getState(): HtState | null {
  const s = (window as unknown as { htState?: HtState }).htState;
  return s || null;
}
