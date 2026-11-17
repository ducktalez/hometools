/**
 * Current-playback scratch state. Ported from `var currentStreamUrl` in
 * `player_js/_core.py` and the formerly undeclared (implicit global)
 * `_currentItemDuration`. One object, exposed as `window._playback`.
 */

export interface PlaybackState {
  /** Stream URL of the item being played ('' = none). */
  currentStreamUrl: string;
  /** Duration (s) reported by the catalog for the current item; 0 = unknown. */
  itemDuration: number;
  /** Global-search mode active (results span folders). */
  globalSearchActive: boolean;
  /** relative_path -> favorited. */
  savedFavorites: Record<string, boolean>;
  /** Path whose rating was just changed; never fully hidden by filters. */
  justRatedPath: string | null;
  allItems: LegacyMediaItem[];
  filteredItems: LegacyMediaItem[];
  playlistItems: LegacyMediaItem[];
  currentIndex: number;
  currentPath: string;
  inPlaylist: boolean;
  /** false = off, 'normal' = random, 'weighted' = rating-weighted. */
  shuffleMode: false | "normal" | "weighted";
  /** false = off, 'all' = repeat playlist, 'one' = repeat single track. */
  repeatMode: false | "all" | "one";
  /** Pre-built index queue for the shuffle session. */
  shuffleQueue: number[];
  shufflePos: number;
  /** Up-next queue. */
  userQueue: LegacyMediaItem[];
  userPlaylists: unknown[];
  playlistRevision: number;
  currentPlaylistId: string;
  playlistAddPath: string;
}

/**
 * Rating threshold below which items count as hidden. Explicit minRating wins;
 * else 2 (hides 1-star) when rating writes enabled; 0 = feature off.
 */
export function computeEffectiveThreshold(minRating: number, ratingWriteEnabled: boolean): number {
  if (minRating > 0) return minRating;
  return ratingWriteEnabled ? 2 : 0;
}

export function createPlaybackState(initialItems: LegacyMediaItem[] = []): PlaybackState {
  return {
    currentStreamUrl: "",
    itemDuration: 0,
    globalSearchActive: false,
    savedFavorites: {},
    justRatedPath: null,
    allItems: initialItems,
    filteredItems: [],
    playlistItems: [],
    currentIndex: -1,
    currentPath: "",
    inPlaylist: false,
    shuffleMode: false,
    repeatMode: false,
    shuffleQueue: [],
    shufflePos: -1,
    userQueue: [],
    userPlaylists: [],
    playlistRevision: 0,
    currentPlaylistId: "",
    playlistAddPath: "",
  };
}
