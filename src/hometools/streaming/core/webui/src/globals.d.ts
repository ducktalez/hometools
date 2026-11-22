/**
 * Ambient types shared across modules (global script file: no import/export,
 * so `interface Window` merges into lib.dom's).
 */

/** Catalog item as used by the player UI (mirrors
 * `streaming/core/models.py::MediaItem.to_dict()`). Loose index signature:
 * the server may add fields; tighten only as modules need them. */
interface CatalogItem {
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
  /** Live getter/setter view over `app.ts` state; see `stateBridge.ts`. */
  htState?: import("./stateBridge").HtState;
  /** Header title text without a folder open; set once by `app.ts`. */
  originalTitle: string;
}