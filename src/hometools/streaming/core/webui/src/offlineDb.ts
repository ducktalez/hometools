/**
 * Offline-download IndexedDB data layer ("hometools-downloads" / "downloads").
 *
 * Ported 1:1 from `player_js/_track_render.py` (initDownloadDB,
 * getDownloadByStreamUrl, getAllDownloads, deleteDownloadById,
 * deleteDownloadByStreamUrl). The `downloadDB` handle was only touched by
 * these functions → moved as module-private state (no bridge needed).
 *
 * CONTRACT: DB_NAME/DB_VERSION must match the Service Worker's
 * `indexedDB.open(...)` in `server_utils/_pwa.py` (it reads blobs for
 * offline playback). Version mismatch = VersionError in one of them.
 * Guarded by tests/test_offline_downloads.py.
 *
 * Never rejects except initDownloadDB (caller handles); reads/deletes
 * resolve to null/[]/false on any failure (project rule: never crash caller).
 */

import { pickEvictionVictims } from "./offlineDownloads";

export const DB_NAME = "hometools-downloads";
export const DB_VERSION = 2;
const STORE = "downloads";

export interface DownloadRecord {
  id: number;
  streamUrl: string;
  title?: string;
  status?: string;
  timestamp?: number;
  [key: string]: unknown;
}

let downloadDB: IDBDatabase | null = null;

/** Open (and create/upgrade) the downloads DB. Rejects on open error. */
export function initDownloadDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      downloadDB = req.result;
      resolve(req.result);
    };
    req.onupgradeneeded = () => {
      const db = req.result;
      const store = db.objectStoreNames.contains(STORE)
        ? (req.transaction as IDBTransaction).objectStore(STORE)
        : db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      if (!store.indexNames.contains("streamUrl")) store.createIndex("streamUrl", "streamUrl", { unique: true });
      if (!store.indexNames.contains("status")) store.createIndex("status", "status", { unique: false });
      if (!store.indexNames.contains("timestamp")) store.createIndex("timestamp", "timestamp", { unique: false });
      if (!store.indexNames.contains("title")) store.createIndex("title", "title", { unique: false });
    };
  });
}

/** Close + forget the handle (tests, or before deleting the DB). */
export function closeDownloadDB(): void {
  if (downloadDB) {
    try {
      downloadDB.close();
    } catch {
      /* ignore */
    }
  }
  downloadDB = null;
}

export function getDownloadByStreamUrl(streamUrl: string): Promise<DownloadRecord | null> {
  return new Promise((resolve) => {
    if (!downloadDB) return resolve(null);
    try {
      const req = downloadDB.transaction(STORE, "readonly").objectStore(STORE).index("streamUrl").get(streamUrl);
      req.onerror = () => resolve(null);
      req.onsuccess = () => resolve((req.result as DownloadRecord) || null);
    } catch {
      resolve(null);
    }
  });
}

export function getAllDownloads(): Promise<DownloadRecord[]> {
  return new Promise((resolve) => {
    if (!downloadDB) return resolve([]);
    try {
      const req = downloadDB.transaction(STORE, "readonly").objectStore(STORE).getAll();
      req.onerror = () => resolve([]);
      req.onsuccess = () => resolve((req.result as DownloadRecord[]) || []);
    } catch {
      resolve([]);
    }
  });
}

export function deleteDownloadById(id: number): Promise<boolean> {
  return new Promise((resolve) => {
    if (!downloadDB) return resolve(false);
    try {
      const tx = downloadDB.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch {
      resolve(false);
    }
  });
}

/**
 * Free space for `requiredBytes` by deleting oldest "ready" downloads
 * (never `protectedStreamUrl`). true = fits now. false = cannot fit even
 * after evicting everything → nothing deleted. Sequential deletes (same
 * as legacy chain). Ported from `_track_render.py::pruneOldDownloads`;
 * UI refresh stays in legacy wrapper.
 */
export function evictForBudget(
  requiredBytes: number,
  softLimit: number,
  protectedStreamUrl?: string | null
): Promise<boolean> {
  return getAllDownloads().then((downloads) => {
    const victims = pickEvictionVictims(downloads, requiredBytes, softLimit, protectedStreamUrl);
    if (victims === null) return false;
    return victims
      .reduce<Promise<unknown>>((chain, v) => chain.then(() => deleteDownloadById(v.id)), Promise.resolve())
      .then(() => true);
  });
}

/** Delete by stream URL + tell the Service Worker to drop its copy. */
export function deleteDownloadByStreamUrl(streamUrl: string): Promise<boolean> {
  return getDownloadByStreamUrl(streamUrl).then((download) => {
    if (!download) return false;
    return deleteDownloadById(download.id).then((ok) => {
      const sw = typeof navigator !== "undefined" ? navigator.serviceWorker : undefined;
      if (ok && sw && sw.controller) {
        sw.controller.postMessage({ type: "DELETE_DOWNLOAD", url: streamUrl });
      }
      return ok;
    });
  });
}



