import { describe, it, expect, vi, afterEach } from "vitest";
vi.mock("../src/offlineDb", () => ({
  getAllDownloads: vi.fn(),
  isDownloadDbReady: vi.fn(),
  getDownloadByStreamUrl: vi.fn(),
  deleteDownloadByStreamUrl: vi.fn(),
  addDownloadRecord: vi.fn(),
}));
vi.mock("../src/offlineUrl", () => ({ getOfflineUrl: vi.fn(() => "blob:x") }));
import { getAllDownloads, isDownloadDbReady, getDownloadByStreamUrl, deleteDownloadByStreamUrl, addDownloadRecord } from "../src/offlineDb";
import {
  updateAllDownloadButtons,
  cancelDownload,
  downloadTrack,
  deleteTrackDownload,
  checkIfMediaCached,
  playOfflineOrStream,
} from "../src/downloadButtons";
afterEach(() => vi.unstubAllGlobals());
function btn(url: string, classes: string[] = []) {
  const set = new Set(classes);
  return {
    dataset: { streamUrl: url },
    classList: {
      add: (c: string) => void set.add(c),
      remove: (c: string) => void set.delete(c),
      contains: (c: string) => set.has(c),
    },
    innerHTML: "",
    title: "",
    set,
  };
}
const icons = { icDl: "DL", icCheck: "OK" };
describe("updateAllDownloadButtons", () => {
  it("marks ready as cached, resets others, keeps downloading icon", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    vi.mocked(getAllDownloads).mockResolvedValue([{ id: 1, streamUrl: "a", status: "ready" }]);
    const a = btn("a", ["downloading"]);
    const b = btn("b", ["cached"]);
    const c = btn("c", ["downloading"]);
    vi.stubGlobal("document", { querySelectorAll: () => [a, b, c] });
    await updateAllDownloadButtons(icons);
    expect(a.set.has("cached")).toBe(true);
    expect(a.set.has("downloading")).toBe(false);
    expect(a.innerHTML).toBe("OK");
    expect(b.set.has("cached")).toBe(false);
    expect(b.innerHTML).toBe("DL");
    expect(b.title).toBe("Download");
    expect(c.set.has("downloading")).toBe(true);
    expect(c.innerHTML).toBe("");
  });
  it("no-op when DB not ready; never rejects on DB failure", async () => {
    vi.mocked(getAllDownloads).mockClear();
    vi.mocked(isDownloadDbReady).mockReturnValue(false);
    await updateAllDownloadButtons(icons);
    expect(getAllDownloads).not.toHaveBeenCalled();
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    vi.mocked(getAllDownloads).mockRejectedValue(new Error("x"));
    await expect(updateAllDownloadButtons(icons)).resolves.toBeUndefined();
  });
});
describe("cancelDownload", () => {
  it("aborts, removes controller, resets button, toasts", () => {
    const abort = vi.fn();
    const active: Record<string, { abort(): void }> = { u: { abort } };
    const b = btn("u", ["downloading", "cached"]);
    const toast = vi.fn();
    cancelDownload("u", b, active, { icDl: "DL", toast });
    expect(abort).toHaveBeenCalled();
    expect(active.u).toBeUndefined();
    expect(b.set.size).toBe(0);
    expect(b.innerHTML).toBe("DL");
    expect(toast).toHaveBeenCalledWith("Download abgebrochen");
  });
  it("tolerates missing controller/button and throwing abort", () => {
    const toast = vi.fn();
    cancelDownload("x", null, {}, { icDl: "DL", toast });
    const active = {
      y: {
        abort: () => {
          throw new Error("x");
        },
      },
    };
    cancelDownload("y", undefined, active, { icDl: "DL", toast });
    expect(toast).toHaveBeenCalledTimes(2);
    expect(active).toEqual({});
  });
});
function dlHooks(over = {}) {
  return {
    icDl: "DL",
    icCheck: "OK",
    itemNoun: "track",
    softLimit: 1000,
    formatBytes: (n: number) => n + "B",
    ensureStorageBudget: vi.fn(() => Promise.resolve(true)),
    toast: vi.fn(),
    refreshLibrary: vi.fn(),
    updateButtons: vi.fn(),
    ...over,
  };
}
function streamResponse(chunks: number[][], headers: Record<string, string> = {}, ok = true, status = 200) {
  let i = 0;
  return {
    ok,
    status,
    headers: { get: (k: string) => headers[k.toLowerCase()] ?? null },
    body: {
      getReader: () => ({
        read: () => Promise.resolve(i < chunks.length ? { done: false, value: new Uint8Array(chunks[i++]) } : { done: true, value: undefined }),
      }),
    },
  };
}
describe("downloadTrack", () => {
  it("stores blob + record, marks cached, refreshes", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    vi.mocked(deleteDownloadByStreamUrl).mockResolvedValue(true);
    vi.mocked(addDownloadRecord).mockClear();
    vi.mocked(addDownloadRecord).mockResolvedValue();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(streamResponse([[1, 2], [3, 4]], { "content-length": "4", "content-type": "audio/mpeg" }))));
    const b = btn("u", []);
    const active: Record<string, { abort(): void }> = {};
    const h = dlHooks();
    await downloadTrack("u", "T", b, { artist: "A", relativePath: "r" }, active, h);
    const rec = vi.mocked(addDownloadRecord).mock.calls[0][0] as Record<string, unknown>;
    expect(rec).toMatchObject({ streamUrl: "u", title: "T", artist: "A", relativePath: "r", mediaType: "track", size: 4, status: "ready" });
    expect(active.u).toBeUndefined();
    expect(b.set.has("cached")).toBe(true);
    expect(b.set.has("downloading")).toBe(false);
    expect(b.innerHTML).toBe("OK");
    expect(h.updateButtons).toHaveBeenCalled();
    expect(h.refreshLibrary).toHaveBeenCalled();
  });
  it("too large file -> toast, button reset, nothing stored", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    vi.mocked(addDownloadRecord).mockClear();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(streamResponse([], { "content-length": "5000" }))));
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    const b = btn("u", []);
    const h = dlHooks();
    await downloadTrack("u", "T", b, undefined, {}, h);
    expect(h.toast.mock.calls[0][0]).toContain("zu gro");
    expect(b.innerHTML).toBe("DL");
    expect(b.title).toBe("Download fehlgeschlagen");
    expect(addDownloadRecord).not.toHaveBeenCalled();
    err.mockRestore();
  });
  it("http error and no storage room are reported", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(streamResponse([], {}, false, 404))));
    const h = dlHooks();
    await downloadTrack("u", "T", btn("u"), undefined, {}, h);
    expect(h.toast).toHaveBeenCalledWith("HTTP 404");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(streamResponse([[1]], { "content-length": "1" }))));
    const h2 = dlHooks({ ensureStorageBudget: vi.fn(() => Promise.resolve(false)) });
    await downloadTrack("u", "T", btn("u"), undefined, {}, h2);
    expect(h2.toast.mock.calls[0][0]).toContain("Offline-Speicher voll");
    err.mockRestore();
  });
  it("abort: silent, controller removed, no toast", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(true);
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(Object.assign(new Error("a"), { name: "AbortError" }))));
    const active: Record<string, { abort(): void }> = {};
    const h = dlHooks();
    await downloadTrack("u", "T", btn("u"), undefined, active, h);
    expect(active.u).toBeUndefined();
    expect(h.toast).not.toHaveBeenCalled();
  });
  it("no-op when DB not ready", async () => {
    vi.mocked(isDownloadDbReady).mockReturnValue(false);
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    await downloadTrack("u", "T", btn("u"), undefined, {}, dlHooks());
    expect(f).not.toHaveBeenCalled();
  });
});
describe("deleteTrackDownload", () => {
  it("resets button + refreshes only when deleted", async () => {
    const h = dlHooks();
    const b = btn("u", ["cached"]);
    vi.mocked(deleteDownloadByStreamUrl).mockResolvedValueOnce(false);
    await deleteTrackDownload("u", b, h);
    expect(h.refreshLibrary).not.toHaveBeenCalled();
    vi.mocked(deleteDownloadByStreamUrl).mockResolvedValueOnce(true);
    await deleteTrackDownload("u", b, h);
    expect(b.set.has("cached")).toBe(false);
    expect(b.innerHTML).toBe("DL");
    expect(h.refreshLibrary).toHaveBeenCalled();
    expect(h.updateButtons).toHaveBeenCalled();
  });
});
describe("checkIfMediaCached / playOfflineOrStream", () => {
  it("only ready downloads with blob count as cached", async () => {
    vi.mocked(getDownloadByStreamUrl).mockResolvedValueOnce({ id: 1, streamUrl: "u", status: "ready", blob: new Blob(["x"]) });
    expect(await checkIfMediaCached("u")).not.toBeNull();
    vi.mocked(getDownloadByStreamUrl).mockResolvedValueOnce({ id: 1, streamUrl: "u", status: "downloading", blob: new Blob(["x"]) });
    expect(await checkIfMediaCached("u")).toBeNull();
    vi.mocked(getDownloadByStreamUrl).mockResolvedValueOnce(null);
    expect(await checkIfMediaCached("u")).toBeNull();
  });
  it("offline blob url when cached, else stream; DB failure -> stream", async () => {
    vi.mocked(getDownloadByStreamUrl).mockResolvedValueOnce({ id: 1, streamUrl: "u", status: "ready", blob: new Blob(["x"]) });
    expect(await playOfflineOrStream("u")).toEqual({ url: "blob:x", offline: true, fallbackUrl: "u" });
    vi.mocked(getDownloadByStreamUrl).mockResolvedValueOnce(null);
    expect(await playOfflineOrStream("u")).toEqual({ url: "u", offline: false, fallbackUrl: "u" });
    vi.mocked(getDownloadByStreamUrl).mockRejectedValueOnce(new Error("db"));
    expect(await playOfflineOrStream("u")).toEqual({ url: "u", offline: false, fallbackUrl: "u" });
  });
});