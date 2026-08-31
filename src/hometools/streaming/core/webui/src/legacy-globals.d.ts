/**
 * Ambient types contract for the shared, cross-fragment JS globals that
 * still live in `player_js/*.py` (see docs/IMPLEMENTATION_PLAN.md Design
 * Discussions → "Player-JS-Modulkopplung" for why they exist and
 * `webui/README.md` → "Rules while this migration is in progress" for the
 * process this file supports).
 *
 * WHY THIS FILE EXISTS (the ".d.ts contract" step):
 * Every `player_js/*.py` fragment is concatenated into ONE shared,
 * non-strict browser function scope — a fragment reading/writing an
 * identifier declared in a *different* fragment "just works" today only
 * because they're not real JS modules. Porting such a fragment to a real
 * `.ts` module (a separate closure, bundled by Vite) requires that any
 * identifier it reads/writes from the *other* side (the still-Python-
 * generated script) be reachable via `window.<name>` — the same bridge
 * pattern `main.ts` already uses for `fmtTime`/`escHtml`/`formatBytes`/
 * `renderBpmPill`. Declaring the TYPES for that future bridge here — even
 * before the runtime bridging code exists for identifiers whose owning
 * fragment (mostly `_core.py`) hasn't been ported yet — lets `tsc` type-
 * check new ported modules against the eventual contract instead of
 * `any`, and documents in one place which globals are "shared state" vs.
 * fragment-private.
 *
 * IMPORTANT — this file does NOT itself make these globals exist at
 * runtime. `window.allItems` etc. only becomes real once `_core.py` (the
 * fragment that owns most of this state) is actually ported and starts
 * assigning to `window` at the bottom of its `.ts` replacement, exactly
 * like `main.ts` does today for the three already-ported helpers. Until
 * then, a `.ts` module may reference these types for its OWN parameters/
 * return values, but must not assume `window.allItems` is populated in
 * the browser.
 *
 * No `export`/`import` here on purpose — an ambient `.d.ts` without them
 * is a global script file, so this `interface Window` merges into the
 * lib.dom.d.ts one automatically (no `declare global` wrapper needed).
 */

/** Minimal shape of a catalog item as used by the player UI (mirrors
 * `streaming/core/models.py::MediaItem.to_dict()` — see
 * `.github/instructions/clients.instructions.md` for the same contract
 * on the native-client side). Intentionally loose (`[key: string]: unknown`)
 * since the legacy script freely reads server-added fields; tighten only
 * as ported modules need specific fields. */
interface LegacyMediaItem {
  relative_path: string;
  title: string;
  artist?: string;
  stream_url?: string;
  thumbnail_url?: string;
  thumbnail_lg_url?: string;
  rating?: number;
  genre?: string;
  duration?: number;
  file_size?: number;
  mtime?: number;
  season?: number;
  episode?: number;
  bpm?: number;
  media_type?: string;
  [key: string]: unknown;
}

interface Window {
  // ── Core catalog/playback state (declared in `player_js/_core.py`) ──
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
  showHidden: boolean;
  filterRating: number;
  filterFav: boolean;
  filterGenre: string;
  /** Set once from the server-rendered header text
   * (`document.getElementById('header-title').textContent`) in `_core.py`
   * and never reassigned — the "no folder open" header title (used by
   * `leafName()`, see pathUtils.ts). */
  originalTitle: string;

  /** Bridged onto `window` by `_core.py` right after declaration — read/
   * mutated by `applyLocalMutations()` (webui/src/catalogCache.ts). Object
   * identity matters: `_core.py`/`_queue.py`/`_library_tools.py` must only
   * ever mutate keys in place, never reassign the local `_locallyDeletedPaths`
   * var with a fresh `{}` (would desync from this window reference). */
  _locallyDeletedPaths: Record<string, boolean>;
  _currentPlaylistId: string;
  _globalSearchActive: boolean;
  _userQueue: LegacyMediaItem[];
  _queueOpen: boolean;
  _effectiveThreshold: number;
  _savedFavorites: Record<string, boolean>;
  _dupeMap: Record<string, number[]> | null;
  _dupePaths: Set<string> | null;
  _dupeSafety: Record<string, boolean> | null;

  // ── Config flags/constants (rendered once in `_player_js.py`'s header
  // from the `#ht-config` blob — see `PlayerConfig` in main.ts) ──
  ITEM_NOUN: string;
  PLAYLISTS_ENABLED: boolean;
  METADATA_EDIT_ENABLED: boolean;
  RATING_WRITE_ENABLED: boolean;
  DEBUG_FILTER: boolean;
  BPM_MIN: number;
  BPM_MAX: number;
  FILE_PLACEHOLDER: string;

  // ── DOM element refs (all declared in `_core.py`; many more of the
  // same shape exist there — trackList/folderGrid/trackView/filterBar/
  // playerBar/playAllBtn/headerTitle/backBtn/searchInput/sortField/
  // player etc. — add here individually only as a ported module needs
  // to reference one, to keep this contract's size proportional to
  // actual usage) ──
  trackList: HTMLElement | null;
  player: HTMLMediaElement | null;

  // ── Shared functions (owning fragment noted per entry) ──
  showFolderView(): void;
  showPlaylist(items: LegacyMediaItem[], autoplay: boolean, startIdx?: number): void;
  playItem(item: LegacyMediaItem, idx: number): void;
  playTrack(idx: number): void;
  renderTracks(tracks: LegacyMediaItem[], force?: boolean): void;
  applyFilter(): void;
  markActive(): void;
  /** Owned by `toast.ts` now (bridged in main.ts), not by the legacy script. */
  showToast(msg: string, durationMs?: number): void;
  rebuildShuffleQueue(startIndex: number): void;
  itemsUnder(path: string): LegacyMediaItem[];
  contentsAt(path: string): { folders: string[]; files: LegacyMediaItem[] };
  _invalidateDupeMap(): void;
  _ensureDupeMap(): void;
  refreshCatalog(): void;
}

