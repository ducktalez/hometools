/**
 * Typed access to the legacy script's mutable core state.
 *
 * `_core.py` defines `window.htState` INSIDE the legacy IIFE as an object
 * of getter/setter closures over its `var`s. Reads are live, writes
 * reassign the original vars — so ported modules and the legacy script
 * always see one state, and no legacy mutation site needs touching.
 *
 * Fourth migration pattern (after window-bridge / explicit params / move
 * private state): use for functions coupled to *shared, reassigned*
 * globals like `filteredItems`/`shuffleQueue`. See IMPLEMENTATION_PLAN.md.
 *
 * Extend `HtState` + the `_core.py` object together, one property pair
 * per newly needed global.
 */

export interface HtState {
  allItems: LegacyMediaItem[];
  filteredItems: LegacyMediaItem[];
  playlistItems: LegacyMediaItem[];
  currentIndex: number;
  currentPath: string;
  inPlaylist: boolean;
  shuffleMode: false | "normal" | "weighted";
  repeatMode: false | "all" | "one";
  shuffleQueue: number[];
  shufflePos: number;
}

/** Bridge or null when the legacy script hasn't run (yet). Callers must no-op then. */
export function getState(): HtState | null {
  const s = (window as unknown as { htState?: HtState }).htState;
  return s || null;
}

