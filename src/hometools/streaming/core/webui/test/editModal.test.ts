import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { submitEditModal } from "../src/editModal";
import type { EditModalHooks } from "../src/editModal";
afterEach(() => vi.unstubAllGlobals());
function hooks(): EditModalHooks {
  return {
    metadataEditEnabled: true,
    ratingWriteEnabled: false,
    metadataEditPath: "/api/audio/metadata/edit",
    ratingApiPath: "/api/audio/rating",
    icStarFilled: "F",
    icStarEmpty: "E",
    toast: vi.fn(),
    applyFilter: vi.fn(),
    renderPlayerRating: vi.fn(),
    rebuildShuffleQueue: vi.fn(),
    setPlayerText: vi.fn(),
  };
}
function fakeDom(values: Record<string, string>) {
  const attrs: string[] = [];
  vi.stubGlobal("document", {
    getElementById: (id: string) => {
      if (id === "edit-modal-backdrop") return { setAttribute: (k: string) => attrs.push(k) };
      if (id === "edit-modal-save-btn") return { disabled: false };
      return id in values ? { value: values[id] } : null;
    },
    body: { classList: { remove: vi.fn(), add: vi.fn() } },
  });
}
describe("submitEditModal", () => {
  it("updates items, closes modal, updates player text for current track", async () => {
    const a = item("a.mp3", { title: "old" });
    const s = installState({ allItems: [a], filteredItems: [a], currentIndex: 0 });
    fakeDom({
      "edit-modal-path": "a.mp3",
      "edit-modal-idx": "0",
      "edit-modal-title-input": " New ",
      "edit-modal-artist-input": "Art",
      "edit-modal-album-input": "",
    });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })));
    const h = hooks();
    submitEditModal(h);
    await new Promise((r) => setTimeout(r, 0));
    expect(s.allItems[0].title).toBe("New");
    expect(s.filteredItems[0].artist).toBe("Art");
    expect(h.applyFilter).toHaveBeenCalled();
    expect(h.setPlayerText).toHaveBeenCalledWith("New", "Art");
    expect(h.toast).toHaveBeenCalledWith("Gespeichert \u2713");
  });
  it("toasts on server error and keeps items", async () => {
    const a = item("a.mp3", { title: "old" });
    const s = installState({ allItems: [a], filteredItems: [a], currentIndex: 0 });
    fakeDom({ "edit-modal-path": "a.mp3", "edit-modal-idx": "0", "edit-modal-title-input": "x" });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: false }) })));
    const h = hooks();
    submitEditModal(h);
    await new Promise((r) => setTimeout(r, 0));
    expect(s.allItems[0].title).toBe("old");
    expect(h.toast).toHaveBeenCalledWith("Fehler beim Speichern");
  });
});
