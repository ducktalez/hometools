/**
 * Late metadata refresh for the playing track. Ported from
 * `player_js/_library_tools.py::refreshMetadata`. Fetches `<base>/metadata`
 * and patches title/artist/rating in place. Stale responses (track switched
 * meanwhile) are dropped via the progress-path guard.
 */

import { getProgressPath } from "./progress";

export interface MetadataItem {
  relative_path: string;
  title?: string;
  artist?: string;
  rating?: number;
}

export interface MetadataRefreshHooks {
  /** Catalog API path, e.g. `/api/audio/items`; metadata lives next to it. */
  apiPath: string;
  setTitle(s: string): void;
  setArtist(s: string): void;
  renderPlayerRating(stars: number): void;
  updateMediaSession(t: MetadataItem): void;
  applyFilter(): void;
  markActive(): void;
}

/** `/api/x/items` -> `/api/x/metadata?path=<rel>` */
export function metadataUrl(apiPath: string, relPath: string): string {
  return apiPath.substring(0, apiPath.lastIndexOf("/")) + "/metadata?path=" + encodeURIComponent(relPath);
}

/** Never throws; resolves once the (optional) patch is applied. */
export function refreshMetadata(t: MetadataItem, h: MetadataRefreshHooks): Promise<void> {
  const requestedFor = t.relative_path;
  let p: Promise<Response>;
  try {
    p = fetch(metadataUrl(h.apiPath, requestedFor));
  } catch {
    return Promise.resolve();
  }
  return p
    .then((r) => (r.ok ? r.json() : null))
    .then((meta: { title?: string; artist?: string; rating?: number } | null) => {
      if (!meta) return;
      // Late response for a superseded track would show a mismatched title/artist.
      if (getProgressPath() !== requestedFor) return;
      let changed = false;
      if (meta.title && meta.title !== t.title) {
        t.title = meta.title;
        h.setTitle(meta.title);
        changed = true;
      }
      if (meta.artist && meta.artist !== t.artist) {
        t.artist = meta.artist;
        h.setArtist(meta.artist);
        changed = true;
      }
      if (typeof meta.rating === "number") {
        t.rating = meta.rating;
        h.renderPlayerRating(meta.rating);
      }
      if (changed) {
        h.updateMediaSession(t);
        h.applyFilter();
        h.markActive();
      }
    })
    .catch(() => {});
}

