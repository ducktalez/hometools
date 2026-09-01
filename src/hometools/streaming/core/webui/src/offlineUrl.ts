/**
 * Blob-URL bookkeeping for offline media playback.
 *
 * Ported from `player_js/_track_render.py` (`revokeOfflineUrl`/
 * `getOfflineUrl`) and the `currentOfflineUrl` var formerly declared in
 * `player_js/_core.py`. Bridging-pattern 1 ("state mitnehmen", see
 * `webui/README.md`): `currentOfflineUrl` was only ever read/written by
 * these two functions — private state, despite living in a different
 * Python fragment than its accessors — so it moves here as module-private
 * state, no `htState` bridge needed.
 *
 * `getOfflineUrl` is the only external call site (`playOfflineOrStream()`
 * in `_track_render.py`, not yet ported) — bridged onto
 * `window.getOfflineUrl` by `main.ts`. `revokeOfflineUrl` has no other
 * caller, so it stays module-private.
 */

let currentOfflineUrl: string | null = null;

function revokeOfflineUrl(): void {
  if (currentOfflineUrl) {
    URL.revokeObjectURL(currentOfflineUrl);
    currentOfflineUrl = null;
  }
}

export function getOfflineUrl(blob: Blob): string {
  revokeOfflineUrl();
  currentOfflineUrl = URL.createObjectURL(blob);
  return currentOfflineUrl;
}

