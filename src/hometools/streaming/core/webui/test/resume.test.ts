import { describe, it, expect, vi, afterEach } from "vitest";
import { item, installState } from "./helpers";
import { findResumeLocal, findResumeRecent, restoreLastEpisode } from "../src/resume";

const items = [item("a", { title: "A" }), item("b", { title: "" }), item("c", { title: "C" })];

describe("findResumeLocal", () => {
  it("hit with position + title", () => {
    expect(findResumeLocal(items, { path: "c", position_seconds: 12 }, -1)).toEqual({ idx: 2, pos: 12, label: "C" });
  });
  it("label falls back to path", () => {
    expect(findResumeLocal(items, { path: "b" }, -1)).toEqual({ idx: 1, pos: 0, label: "b" });
  });
  it("null when selected, unknown, or empty", () => {
    expect(findResumeLocal(items, { path: "a" }, 0)).toBeNull();
    expect(findResumeLocal(items, { path: "zz" }, -1)).toBeNull();
    expect(findResumeLocal(items, null, -1)).toBeNull();
  });
});

describe("findResumeRecent", () => {
  it("first entry in list with pos >= 5", () => {
    const e = [
      { relative_path: "zz", position_seconds: 50 },
      { relative_path: "a", position_seconds: 2 },
      { relative_path: "c", position_seconds: 30 },
    ];
    expect(findResumeRecent(items, e, -1)).toEqual({ idx: 2, pos: 30, label: "C" });
  });
  it("null when none qualify or already selected", () => {
    expect(findResumeRecent(items, [{ relative_path: "a", position_seconds: 1 }], -1)).toBeNull();
    expect(findResumeRecent(items, [{ relative_path: "a", position_seconds: 9 }], 1)).toBeNull();
    expect(findResumeRecent(items, [], -1)).toBeNull();
  });
});
describe("restoreLastEpisode", () => {
  afterEach(() => vi.unstubAllGlobals());
  const hooks = (over = {}) => ({
    loadLastPlayedLocal: vi.fn(() => null as { path?: string; position_seconds?: number } | null),
    recentEnabled: true,
    recentApiPath: "/api/recent",
    selectResume: vi.fn(),
    toast: vi.fn(),
    fmtTime: (s: number) => "t" + s,
    ...over,
  });
  const flush = () => new Promise((r) => setTimeout(r, 0));
  it("local hit with position: selects + toast with time", () => {
    installState({ filteredItems: items, currentIndex: -1 });
    const h = hooks({ loadLastPlayedLocal: vi.fn(() => ({ path: "c", position_seconds: 90 })) });
    restoreLastEpisode(h);
    expect(h.selectResume).toHaveBeenCalledWith(2);
    expect(h.toast).toHaveBeenCalledWith("Weiter bei: C (t90)", 5000);
  });
  it("local hit with tiny position: no time suffix; no fetch", () => {
    installState({ filteredItems: items, currentIndex: -1 });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    const h = hooks({ loadLastPlayedLocal: vi.fn(() => ({ path: "a", position_seconds: 1 })) });
    restoreLastEpisode(h);
    expect(h.toast).toHaveBeenCalledWith("Weiter bei: A", 5000);
    expect(f).not.toHaveBeenCalled();
  });
  it("falls back to server recent API", async () => {
    installState({ filteredItems: items, currentIndex: -1 });
    const f = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ relative_path: "a", position_seconds: 60 }] }) }));
    vi.stubGlobal("fetch", f);
    const h = hooks();
    restoreLastEpisode(h);
    await flush();
    expect(f).toHaveBeenCalledWith("/api/recent?limit=100");
    expect(h.selectResume).toHaveBeenCalledWith(0);
    expect(h.toast).toHaveBeenCalledWith("Weiter bei: A (t60)", 5000);
  });
  it("recent disabled / http error / network error: silent", async () => {
    installState({ filteredItems: items, currentIndex: -1 });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    restoreLastEpisode(hooks({ recentEnabled: false }));
    expect(f).not.toHaveBeenCalled();
    const h = hooks();
    vi.stubGlobal("fetch", () => Promise.resolve({ ok: false }));
    restoreLastEpisode(h);
    vi.stubGlobal("fetch", () => Promise.reject(new Error("x")));
    restoreLastEpisode(h);
    vi.stubGlobal("fetch", () => {
      throw new Error("sync");
    });
    expect(() => restoreLastEpisode(h)).not.toThrow();
    await flush();
    expect(h.selectResume).not.toHaveBeenCalled();
  });
  it("already selected item: nothing happens", () => {
    installState({ filteredItems: items, currentIndex: 1 });
    const h = hooks({ loadLastPlayedLocal: vi.fn(() => ({ path: "a" })), recentEnabled: false });
    restoreLastEpisode(h);
    expect(h.selectResume).not.toHaveBeenCalled();
  });
});