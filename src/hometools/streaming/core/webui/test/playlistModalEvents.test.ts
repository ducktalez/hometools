import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import { initPlaylistModalEvents } from "../src/playlistModalEvents";

afterEach(() => vi.unstubAllGlobals());

type L = (e: unknown) => void;
function stubDom() {
  const mk = () => {
    const h: Record<string, L> = {};
    return { h, addEventListener: (ev: string, f: L) => (h[ev] = f), click: vi.fn(), value: "", hidden: false };
  };
  const els: Record<string, ReturnType<typeof mk>> = {
    "playlist-modal-close-btn": mk(),
    "playlist-modal-backdrop": mk(),
    "playlist-modal-new-btn": mk(),
    "playlist-modal-new-name": mk(),
  };
  const doc = mk();
  vi.stubGlobal("document", { getElementById: (id: string) => els[id] || null, addEventListener: doc.addEventListener });
  return { els, doc };
}

describe("initPlaylistModalEvents", () => {
  it("disabled -> no wiring", () => {
    const { els } = stubDom();
    initPlaylistModalEvents({ enabled: false, closeModal: vi.fn(), createAndAdd: vi.fn() });
    expect(Object.keys(els["playlist-modal-close-btn"].h)).toEqual([]);
  });

  it("wires close/backdrop/new/Enter/Escape; installs once", () => {
    installState({ playlistAddPath: "a/b.mp4" });
    const { els, doc } = stubDom();
    const closeModal = vi.fn();
    const createAndAdd = vi.fn();
    initPlaylistModalEvents({ enabled: true, closeModal, createAndAdd });
    initPlaylistModalEvents({ enabled: true, closeModal, createAndAdd });

    els["playlist-modal-close-btn"].h.click({});
    expect(closeModal).toHaveBeenCalledTimes(1);

    const bd = els["playlist-modal-backdrop"];
    bd.h.click({ target: {} });
    expect(closeModal).toHaveBeenCalledTimes(1);
    bd.h.click({ target: bd });
    expect(closeModal).toHaveBeenCalledTimes(2);

    const inp = els["playlist-modal-new-name"];
    inp.value = "   ";
    els["playlist-modal-new-btn"].h.click({});
    expect(createAndAdd).not.toHaveBeenCalled();
    inp.value = " Mix ";
    els["playlist-modal-new-btn"].h.click({});
    expect(createAndAdd).toHaveBeenCalledWith("Mix", "a/b.mp4");
    expect(inp.value).toBe("");

    inp.h.keydown({ key: "Enter" });
    expect(els["playlist-modal-new-btn"].click).toHaveBeenCalledTimes(1);

    doc.h.keydown({ key: "Escape" });
    expect(closeModal).toHaveBeenCalledTimes(3);
    bd.hidden = true;
    doc.h.keydown({ key: "Escape" });
    expect(closeModal).toHaveBeenCalledTimes(3);
  });
});

