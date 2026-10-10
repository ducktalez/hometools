/** Test helpers: fake window.htState + item factory (node env, no DOM). */
import type { HtState } from "../src/stateBridge";

export type Item = LegacyMediaItem;

export function item(rp: string, extra: Partial<Item> = {}): Item {
  return { relative_path: rp, title: rp, artist: "", ...extra } as Item;
}

/** Install a plain-object htState on a fresh global window; returns it. */
export function installState(over: Partial<HtState> = {}): HtState {
  const s: HtState = {
    allItems: [],
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
    ...over,
  };
  (globalThis as unknown as { window: { htState: HtState } }).window = { htState: s };
  return s;
}

/** Remove the bridge (simulates bundle loaded before legacy script). */
export function removeState(): void {
  (globalThis as unknown as { window: object }).window = {};
}

