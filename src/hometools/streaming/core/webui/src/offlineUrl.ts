/**
 * Blob-URL bookkeeping for offline media playback.
 *
 * (`revokeOfflineUrl`/
 * `getOfflineUrl`) and the `currentOfflineUrl` var formerly declared in
 * `webui/README.md`): `currentOfflineUrl` was only ever read/written by
 * these two functions — private state, despite living in a different
 *
 * `getOfflineUrl` is called from `playOfflineOrStream()` in
 * by `main.ts`. `revokeOfflineUrl` is ALSO called bare from
 * bare identifier throws a ReferenceError in that (still non-module,
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

