import { describe, it, expect, vi, afterEach } from "vitest";
import { isTrackViewVisible, applyTrackViewMode, toggleTrackViewMode } from "../src/trackViewMode";
import type { TrackViewModeHooks } from "../src/trackViewMode";
import { applyFolderViewMode } from "../src/trackViewMode";

afterEach(() => vi.unstubAllGlobals());

function setup(mode: string, video = false, visible = true) {
  const store: Record<string, string> = {};
  vi.stubGlobal("localStorage", { setItem: (k: string, v: string) => (store[k] = v) });
  let hdr: { id: string; className: string; innerHTML: string; remove(): void } | null = null;
  const inserted = vi.fn();
  vi.stubGlobal("document", {
    getElementById: () => hdr,
    createElement: () => {
      hdr = { id: "", className: "", innerHTML: "", remove: () => (hdr = null) };
      return hdr;
    },
  });
  const tl = new Set<string>();
  const tv = new Set<string>();
  if (!visible) tv.add("view-hidden");
  const vt = new Set<string>();
  let m = mode;
  const h = {
    trackList: {
      classList: { toggle: (c: string, on: boolean) => (on ? tl.add(c) : tl.delete(c)) },
      parentNode: { insertBefore: inserted },
    },
    trackView: { classList: { contains: (c: string) => tv.has(c) } },
    viewToggle: {
      innerHTML: "",
      title: "",
      classList: { toggle: (c: string, on: boolean) => (on ? vt.add(c) : vt.delete(c)) },
    },
    isVideoMode: video,
    tableHeaderHtml: "<hdr>",
    icList: "LIST",
    icTable: "TABLE",
    getMode: () => m,
    setMode: (x: string) => (m = x),
    rerender: vi.fn(),
  } as unknown as TrackViewModeHooks;
  return { h, tl, store, inserted, mode: () => m };
}

function fv(toolActive: boolean, viewMode: string) {
  const g = new Set<string>();
  const t = new Set<string>();
  const toggle = { innerHTML: "", title: "", classList: { add: (c: string) => t.add(c), remove: (c: string) => t.delete(c) } };
  applyFolderViewMode({
    folderGrid: { classList: { add: (c: string) => g.add(c), remove: (c: string) => g.delete(c) } } as unknown as HTMLElement,
    viewToggle: toggle as unknown as HTMLElement,
    icList: "LIST",
    icGrid: "GRID",
    toolActive,
    viewMode,
  });
  return { g, t, toggle };
}

describe("trackViewMode", () => {
  it("visibility", () => {
    expect(isTrackViewVisible(null)).toBe(false);
    expect(isTrackViewVisible({ classList: { contains: () => true } } as unknown as HTMLElement)).toBe(false);
    expect(isTrackViewVisible({ classList: { contains: () => false } } as unknown as HTMLElement)).toBe(true);
  });
  it("apply table mode adds class + header", () => {
    const t = setup("table");
    applyTrackViewMode(t.h);
    expect(t.tl.has("table-mode")).toBe(true);
    expect(t.inserted).toHaveBeenCalled();
  });
  it("video never table", () => {
    const t = setup("table", true);
    applyTrackViewMode(t.h);
    expect(t.tl.has("table-mode")).toBe(false);
  });
  it("toggle flips, persists, rerenders", () => {
    const t = setup("rows");
    toggleTrackViewMode(t.h);
    expect(t.mode()).toBe("table");
    expect(t.store["ht-track-view-mode"]).toBe("table");
    expect(t.h.rerender).toHaveBeenCalled();
  });
});

describe("applyFolderViewMode", () => {
  it("tools lock list + filenames", () => {
    const r = fv(true, "grid");
    expect(r.g.has("list-mode") && r.g.has("filenames-mode")).toBe(true);
    expect(r.t.has("view-toggle-locked")).toBe(true);
    expect(r.toggle.innerHTML).toBe("LIST");
  });
  it("list mode shows grid icon", () => {
    const r = fv(false, "list");
    expect(r.g.has("list-mode")).toBe(true);
    expect(r.g.has("filenames-mode")).toBe(false);
    expect(r.toggle.innerHTML).toBe("GRID");
  });
  it("grid mode clears list-mode", () => {
    const r = fv(false, "grid");
    expect(r.g.size).toBe(0);
    expect(r.toggle.innerHTML).toBe("LIST");
  });
});
