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
 * `getOfflineUrl` is called from `playOfflineOrStream()` in
 * `_track_render.py` (not yet ported) — bridged onto `window.getOfflineUrl`
 * by `main.ts`. `revokeOfflineUrl` is ALSO called bare from
 * `playItem()` in `_library_tools.py` (not yet ported, 2 call sites) —
 * it must be exported + bridged onto `window.revokeOfflineUrl` too, or the
 * bare identifier throws a ReferenceError in that (still non-module,
 * shared-scope) legacy script, silently breaking playback before the
 * player-bar UI even updates (see docs/architecture.md incident notes).
 */

let currentOfflineUrl: string | null = null;

export function revokeOfflineUrl(): void {
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

