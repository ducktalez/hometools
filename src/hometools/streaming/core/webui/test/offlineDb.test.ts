import { describe, it, expect, beforeEach } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import {
  DB_NAME,
  DB_VERSION,
  initDownloadDB,
  closeDownloadDB,
  getDownloadByStreamUrl,
  getAllDownloads,
  deleteDownloadById,
  deleteDownloadByStreamUrl,
} from "../src/offlineDb";

/** Insert a record directly (downloadTrack/SW write path not ported yet). */
function put(db: IDBDatabase, rec: object): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("downloads", "readwrite");
    tx.objectStore("downloads").add(rec);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

beforeEach(() => {
  closeDownloadDB();
  (globalThis as unknown as { indexedDB: IDBFactory }).indexedDB = new IDBFactory();
});

describe("offlineDb", () => {
  it("before init: safe defaults, no throw", async () => {
    expect(await getDownloadByStreamUrl("/x")).toBeNull();
    expect(await getAllDownloads()).toEqual([]);
    expect(await deleteDownloadById(1)).toBe(false);
    expect(await deleteDownloadByStreamUrl("/x")).toBe(false);
  });

  it("init creates store + all four indexes at the SW-shared version", async () => {
    const db = await initDownloadDB();
    expect(db.name).toBe(DB_NAME);
    expect(db.version).toBe(DB_VERSION);
    const store = db.transaction("downloads", "readonly").objectStore("downloads");
    expect([...store.indexNames].sort()).toEqual(["status", "streamUrl", "timestamp", "title"]);
    expect(store.autoIncrement).toBe(true);
  });

  it("upgrade from v1 store without indexes adds them, keeps data", async () => {
    const v1 = await new Promise<IDBDatabase>((resolve) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore("downloads", { keyPath: "id", autoIncrement: true });
      req.onsuccess = () => resolve(req.result);
    });
    await put(v1, { streamUrl: "/old", title: "Old" });
    v1.close();
    await initDownloadDB();
    expect((await getDownloadByStreamUrl("/old"))?.title).toBe("Old");
  });

  it("get / getAll / delete round trip", async () => {
    const db = await initDownloadDB();
    await put(db, { streamUrl: "/a", title: "A" });
    await put(db, { streamUrl: "/b", title: "B" });
    expect((await getAllDownloads()).map((d) => d.streamUrl).sort()).toEqual(["/a", "/b"]);
    const a = await getDownloadByStreamUrl("/a");
    expect(a?.title).toBe("A");
    expect(await deleteDownloadById(a!.id)).toBe(true);
    expect(await getDownloadByStreamUrl("/a")).toBeNull();
    expect(await deleteDownloadByStreamUrl("/b")).toBe(true);
    expect(await deleteDownloadByStreamUrl("/missing")).toBe(false);
    expect(await getAllDownloads()).toEqual([]);
  });
});

