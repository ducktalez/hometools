import { describe, it, expect, beforeEach } from "vitest";
import { IDBFactory } from "fake-indexeddb";
import { pickEvictionVictims } from "../src/offlineDownloads";
import { initDownloadDB, closeDownloadDB, getAllDownloads, evictForBudget } from "../src/offlineDb";

const MB = 1024 * 1024;
const d = (streamUrl: string, size: number, timestamp: number, status = "ready") => ({ streamUrl, size, timestamp, status });

describe("pickEvictionVictims", () => {
  const list = [d("/new", 40 * MB, 3), d("/old", 30 * MB, 1), d("/mid", 20 * MB, 2), d("/partial", 99 * MB, 0, "downloading")];

  it("fits already -> []", () => {
    expect(pickEvictionVictims(list, 5 * MB, 100 * MB)).toEqual([]);
  });
  it("oldest first, stops once it fits; ignores non-ready", () => {
    // usage 90 MB (+0 partial). need 30 -> 120 > 100 -> evict /old (30) -> 90 ok
    expect(pickEvictionVictims(list, 30 * MB, 100 * MB)?.map((v) => v.streamUrl)).toEqual(["/old"]);
    expect(pickEvictionVictims(list, 45 * MB, 100 * MB)?.map((v) => v.streamUrl)).toEqual(["/old", "/mid"]);
  });
  it("protected item never evicted", () => {
    expect(pickEvictionVictims(list, 30 * MB, 100 * MB, "/old")?.map((v) => v.streamUrl)).toEqual(["/mid"]);
  });
  it("impossible -> null", () => {
    expect(pickEvictionVictims(list, 101 * MB, 100 * MB)).toBeNull();
  });
});

describe("evictForBudget", () => {
  beforeEach(() => {
    closeDownloadDB();
    (globalThis as unknown as { indexedDB: IDBFactory }).indexedDB = new IDBFactory();
  });

  async function seed(recs: object[]) {
    const db = await initDownloadDB();
    for (const r of recs) {
      await new Promise<void>((res, rej) => {
        const tx = db.transaction("downloads", "readwrite");
        tx.objectStore("downloads").add(r);
        tx.oncomplete = () => res();
        tx.onerror = () => rej(tx.error);
      });
    }
  }

  it("deletes oldest until fits", async () => {
    await seed([d("/a", 30 * MB, 1), d("/b", 30 * MB, 2), d("/c", 30 * MB, 3)]);
    expect(await evictForBudget(30 * MB, 100 * MB)).toBe(true);
    expect((await getAllDownloads()).map((x) => x.streamUrl).sort()).toEqual(["/b", "/c"]);
  });
  it("impossible -> false, nothing deleted", async () => {
    await seed([d("/a", 30 * MB, 1), d("/b", 30 * MB, 2)]);
    expect(await evictForBudget(200 * MB, 100 * MB)).toBe(false);
    expect(await getAllDownloads()).toHaveLength(2);
  });
});

