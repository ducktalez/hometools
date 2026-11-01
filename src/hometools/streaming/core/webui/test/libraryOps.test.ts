import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { removeGoneTrack, moveFileToFolder, indexAfterDelete } from "../src/libraryOps";
import type { LibraryOpsHooks } from "../src/libraryOps";

afterEach(() => vi.unstubAllGlobals());

function hooks(over: Partial<LibraryOpsHooks> = {}): LibraryOpsHooks {
  return {
    deleteApiPath: "/del",
    moveApiPath: "/mv",
    toast: vi.fn(),
    invalidateCaches: vi.fn(),
    saveCatalogCache: vi.fn(),
    applyFilter: vi.fn(),
    showFolderView: vi.fn(),
    playTrack: vi.fn(),
    itemsUnder: vi.fn(() => []),
    progressRelPath: vi.fn(() => ""),
    showPausedIcon: vi.fn(),
    reopenDupePanel: vi.fn(),
    ...over,
  };
}

describe("indexAfterDelete", () => {
  it("shifts when deleted row is before current", () => expect(indexAfterDelete(3, 1, 5)).toBe(2));
  it("clamps when deleting last current", () => expect(indexAfterDelete(4, 4, 5)).toBe(3));
  it("keeps otherwise", () => expect(indexAfterDelete(1, 3, 5)).toBe(1));
});

describe("removeGoneTrack", () => {
  it("removes from all/playlist, advances when it was playing", () => {
    const a = item("x/a.mp3");
    const b = item("x/b.mp3");
    const s = installState({ allItems: [a, b], playlistItems: [a, b], filteredItems: [b], inPlaylist: true, currentIndex: 0 });
    const h = hooks({ progressRelPath: () => "x/a.mp3" });
    removeGoneTrack("x/a.mp3", h);
    expect(s.allItems).toEqual([b]);
    expect(s.playlistItems).toEqual([b]);
    expect(h.invalidateCaches).toHaveBeenCalled();
    expect(h.showPausedIcon).toHaveBeenCalled();
    expect(h.applyFilter).toHaveBeenCalled();
    expect(h.playTrack).toHaveBeenCalledWith(0);
  });
  it("not in playlist view -> folder view", () => {
    installState({ allItems: [item("a.mp3")], inPlaylist: false });
    const h = hooks();
    removeGoneTrack("a.mp3", h);
    expect(h.showFolderView).toHaveBeenCalled();
  });
});

describe("moveFileToFolder", () => {
  it("same folder -> toast only, no fetch", () => {
    installState({ filteredItems: [item("A/x.mp3")] });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    const h = hooks();
    moveFileToFolder(0, "A", h);
    expect(h.toast).toHaveBeenCalledWith("Datei ist bereits in diesem Ordner");
    expect(f).not.toHaveBeenCalled();
  });
  it("success updates allItems path + stream_url + artist", async () => {
    const t = item("A/x.mp3", { stream_url: "/s?p=" + encodeURIComponent("A/x.mp3") } as never);
    const s = installState({ allItems: [t], filteredItems: [t] });
    (globalThis as unknown as { window: Record<string, unknown> }).window._locallyDeletedPaths = {};
    vi.stubGlobal("localStorage", { getItem: () => null, setItem: () => {} });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, new_path: "B/x.mp3" }) }))
    );
    const h = hooks();
    moveFileToFolder(0, "B", h);
    await new Promise((r) => setTimeout(r, 0));
    expect(s.allItems[0].relative_path).toBe("B/x.mp3");
    expect(String(s.allItems[0].stream_url)).toContain(encodeURIComponent("B/x.mp3"));
    expect(s.allItems[0].artist).toBe("B");
    expect(h.toast).toHaveBeenCalledWith("Verschoben nach B");
  });
});

