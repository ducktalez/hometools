/**
 * Download button state. Ported from `player_js/_track_render.py`
 * (`updateAllDownloadButtons`, `cancelDownload`). The in-flight controller map
 * (`activeDownloads`) stays legacy (shared with `downloadTrack`) and is passed in.
 */
import {
  getAllDownloads,
  isDownloadDbReady,
  getDownloadByStreamUrl,
  deleteDownloadByStreamUrl,
  addDownloadRecord,
} from "./offlineDb";
import type { DownloadRecord } from "./offlineDb";
import { getOfflineUrl } from "./offlineUrl";
import { readyStreamUrls } from "./offlineDownloads";
export interface DlButton {
  dataset: { streamUrl?: string };
  classList: { add(c: string): void; remove(c: string): void; contains(c: string): boolean };
  innerHTML: string;
  title: string;
  textContent?: string | null;
}
export interface DlIcons {
  icDl: string;
  icCheck: string;
}
/** Sync every `.track-dl-btn` with the ready-set from IndexedDB. Never rejects. */
export function updateAllDownloadButtons(icons: DlIcons): Promise<void> {
  if (!isDownloadDbReady()) return Promise.resolve();
  return getAllDownloads()
    .then((downloads) => {
      const cached = readyStreamUrls(downloads);
      document.querySelectorAll<HTMLElement>(".track-dl-btn").forEach((el) => {
        const btn = el as unknown as DlButton & HTMLElement;
        const url = btn.dataset.streamUrl || "";
        btn.classList.remove("cached");
        if (!btn.classList.contains("downloading")) {
          btn.innerHTML = icons.icDl;
          btn.title = "Download";
        }
        if (cached[url]) {
          btn.classList.add("cached");
          btn.classList.remove("downloading");
          btn.innerHTML = icons.icCheck;
          btn.title = "Offline gespeichert \u2014 klicken zum Entfernen";
        }
      });
    })
    .catch(() => {});
}
/** Abort a running download, reset its button, toast. */
export function cancelDownload(
  streamUrl: string,
  btn: DlButton | null | undefined,
  active: Record<string, { abort(): void }>,
  h: { icDl: string; toast(msg: string): void },
): void {
  const controller = active[streamUrl];
  if (controller) {
    try {
      controller.abort();
    } catch {
      /* ignore */
    }
    delete active[streamUrl];
  }
  if (btn) {
    btn.classList.remove("downloading");
    btn.classList.remove("cached");
    btn.innerHTML = h.icDl;
    btn.title = "Download";
  }
  h.toast("Download abgebrochen");
}
export interface DownloadHooks {
  icDl: string;
  icCheck: string;
  itemNoun: string;
  /** Per-file cap (OFFLINE_SOFT_LIMIT). */
  softLimit: number;
  formatBytes(n: number): string;
  /** Evict old downloads if needed; false = no room. Legacy (UI refresh inside). */
  ensureStorageBudget(requiredBytes: number, protectedStreamUrl: string): Promise<boolean>;
  toast(msg: string): void;
  refreshLibrary(): void;
  updateButtons(): void;
}
export interface DownloadMeta {
  artist?: string;
  relativePath?: string;
  thumbnailUrl?: string;
  mediaType?: string;
}
/**
 * Fetch `streamUrl` into IndexedDB with progress on `btn`. Abortable via
 * `active[streamUrl]`. Never rejects; failures reset the button + toast.
 */
export async function downloadTrack(
  streamUrl: string,
  title: string | undefined,
  btn: DlButton,
  meta: DownloadMeta | undefined,
  active: Record<string, { abort(): void }>,
  h: DownloadHooks,
): Promise<void> {
  if (!isDownloadDbReady()) return;
  btn.classList.add("downloading");
  btn.classList.remove("cached");
  btn.textContent = "0%";
  btn.title = "Download l\u00e4uft \u2014 klicken zum Abbrechen";
  const controller = new AbortController();
  active[streamUrl] = controller;
  try {
    const response = await fetch(streamUrl, { signal: controller.signal });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const total = parseInt(response.headers.get("content-length") || "", 10) || 0;
    if (total > h.softLimit) {
      throw new Error(
        "Datei zu gro\u00df f\u00fcr Offline-Speicher (" + h.formatBytes(total) + ", max " + h.formatBytes(h.softLimit) + ")",
      );
    }
    const ok = total > 0 ? await h.ensureStorageBudget(total, streamUrl) : true;
    if (!ok) throw new Error("Offline-Speicher voll \u2014 l\u00f6sche alte Downloads oder erh\u00f6he den Speicher");
    let received = 0;
    const reader = response.body!.getReader();
    const chunks: Uint8Array[] = [];
    for (;;) {
      const r = await reader.read();
      if (r.done) break;
      chunks.push(r.value);
      received += r.value.length;
      if (total > 0) btn.textContent = Math.round((received / total) * 100) + "%";
    }
    const blob = new Blob(chunks as BlobPart[], { type: response.headers.get("content-type") || "application/octet-stream" });
    if (!(await h.ensureStorageBudget(blob.size, streamUrl))) throw new Error("Offline-Speicher voll");
    await deleteDownloadByStreamUrl(streamUrl);
    await addDownloadRecord({
      streamUrl,
      title,
      artist: meta && meta.artist ? meta.artist : "",
      relativePath: meta && meta.relativePath ? meta.relativePath : "",
      thumbnailUrl: meta && meta.thumbnailUrl ? meta.thumbnailUrl : "",
      mediaType: meta && meta.mediaType ? meta.mediaType : h.itemNoun,
      blob,
      size: blob.size,
      timestamp: Date.now(),
      status: "ready",
    });
    delete active[streamUrl];
    btn.classList.remove("downloading");
    btn.classList.add("cached");
    btn.innerHTML = h.icCheck;
    btn.title = "Offline gespeichert \u2014 klicken zum Entfernen";
    h.updateButtons();
    h.refreshLibrary();
  } catch (err) {
    delete active[streamUrl];
    const e = err as { name?: string; message?: string } | null;
    if (e && e.name === "AbortError") return;
    console.error("Download failed:", err);
    btn.classList.remove("downloading");
    btn.classList.remove("cached");
    btn.innerHTML = h.icDl;
    btn.title = "Download fehlgeschlagen";
    h.toast(e && e.message ? e.message : "Download fehlgeschlagen");
    h.refreshLibrary();
  }
}
/** Remove a stored download; on success reset `btn` and refresh UI. */
export function deleteTrackDownload(
  streamUrl: string,
  btn: DlButton | null | undefined,
  h: Pick<DownloadHooks, "icDl" | "refreshLibrary" | "updateButtons">,
): Promise<void> {
  return deleteDownloadByStreamUrl(streamUrl)
    .then((deleted) => {
      if (!deleted) return;
      if (btn) {
        btn.classList.remove("cached");
        btn.classList.remove("downloading");
        btn.innerHTML = h.icDl;
        btn.title = "Download";
      }
      h.refreshLibrary();
      h.updateButtons();
    })
    .catch(() => {});
}
/** Stored download with a blob and status `ready`, else null. */
export function checkIfMediaCached(streamUrl: string): Promise<DownloadRecord | null> {
  return getDownloadByStreamUrl(streamUrl).then((d) => (d && d.status === "ready" && d.blob ? d : null));
}
export interface PlaybackSource {
  url: string;
  offline: boolean;
  fallbackUrl: string;
}
/** Offline blob URL when downloaded, else the stream URL. Never rejects. */
export function playOfflineOrStream(streamUrl: string): Promise<PlaybackSource> {
  return checkIfMediaCached(streamUrl)
    .then((d): PlaybackSource => {
      if (d && d.blob) return { url: getOfflineUrl(d.blob as Blob), offline: true, fallbackUrl: streamUrl };
      return { url: streamUrl, offline: false, fallbackUrl: streamUrl };
    })
    .catch(() => ({ url: streamUrl, offline: false, fallbackUrl: streamUrl }));
}