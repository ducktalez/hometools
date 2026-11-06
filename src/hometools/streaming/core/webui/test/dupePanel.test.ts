import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { collectDupeItems, dupeSubtitle, playDuplicates } from "../src/dupePanel";

describe("dupePanel helpers", () => {
  it("subtitle pluralises", () => {
    expect(dupeSubtitle(1, 2)).toBe("1 Duplikat-Gruppe (2 Dateien)");
    expect(dupeSubtitle(2, 4)).toBe("2 Duplikat-Gruppen (4 Dateien)");
  });
  it("collects group by group, skipping missing", () => {
    const all = [{ relative_path: "a" }, { relative_path: "b" }, { relative_path: "c" }];
    const out = collectDupeItems({ k1: [2, 0], k2: [1, 9] }, all);
    expect(out.map((i) => i.relative_path)).toEqual(["c", "a", "b"]);
  });
});

describe("playDuplicates", () => {
  const hooks = () => ({
    toast: vi.fn(),
    closePanel: vi.fn(),
    destroyPlaylistDragDrop: vi.fn(),
    enterTrackListView: vi.fn(),
    rebuildShuffleQueue: vi.fn(),
  });
  it("no duplicates -> toast only", () => {
    installState();
    const h = hooks();
    playDuplicates({}, h);
    expect(h.toast).toHaveBeenCalledWith("Keine Duplikate gefunden");
    expect(h.enterTrackListView).not.toHaveBeenCalled();
  });
  it("sets virtual playlist state and enters view", () => {
    const s = installState({ allItems: [item("a"), item("b")], currentPath: "x", shuffleMode: "" });
    const h = hooks();
    playDuplicates({ k: [0, 1] }, h);
    expect(h.closePanel).toHaveBeenCalled();
    expect(h.destroyPlaylistDragDrop).toHaveBeenCalled();
    expect(s.inPlaylist).toBe(true);
    expect(s.currentPlaylistId).toBe("__duplicates__");
    expect(s.currentPath).toBe("");
    expect(s.playlistItems.map((i) => i.relative_path)).toEqual(["a", "b"]);
    expect(h.enterTrackListView).toHaveBeenCalledWith({
      title: "Duplikate (1 Gruppen)",
      playAllDisabled: true,
      collapseFilterBar: true,
      resetIndex: true,
    });
    expect(h.rebuildShuffleQueue).not.toHaveBeenCalled();
  });
  it("rebuilds shuffle queue when shuffle active", () => {
    installState({ allItems: [item("a"), item("b")], shuffleMode: "normal" });
    const h = hooks();
    playDuplicates({ k: [0, 1] }, h);
    expect(h.rebuildShuffleQueue).toHaveBeenCalledWith(0);
  });
  it("group indices all missing -> nothing happens", () => {
    installState({ allItems: [] });
    const h = hooks();
    playDuplicates({ k: [5] }, h);
    expect(h.closePanel).not.toHaveBeenCalled();
  });
});
