import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { initLyricsPanel, lyricsBodyHtml } from "../src/lyricsPanel";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");

class FakeEl {
  title = "";
  innerHTML = "";
  classes = new Set<string>();
  listeners: Record<string, Array<() => void>> = {};
  classList = {
    add: (c: string) => this.classes.add(c),
    remove: (c: string) => this.classes.delete(c),
    toggle: (c: string, on: boolean) => (on ? this.classes.add(c) : this.classes.delete(c)),
  };
  addEventListener(ev: string, fn: () => void) {
    (this.listeners[ev] ||= []).push(fn);
  }
  click() {
    (this.listeners["click"] || []).forEach((f) => f());
  }
}

describe("lyricsBodyHtml", () => {
  it("text escaped", () => expect(lyricsBodyHtml("a<b", "T", esc)).toBe('<div class="lyrics-text">a&lt;b</div>'));
  it("empty uses title or default", () => {
    expect(lyricsBodyHtml("", "T<", esc)).toContain("T&lt;");
    expect(lyricsBodyHtml("", undefined, esc)).toContain("diesen Titel");
  });
});

describe("initLyricsPanel", () => {
  let els: Record<string, FakeEl>;
  const flush = () => new Promise((r) => setTimeout(r, 0));
  beforeEach(() => {
    els = { "btn-lyrics": new FakeEl(), "lyrics-panel": new FakeEl(), "lyrics-body": new FakeEl(), "lyrics-close-btn": new FakeEl() };
    vi.stubGlobal("document", { getElementById: (id: string) => els[id] || null });
  });
  afterEach(() => vi.unstubAllGlobals());

  const mk = (enabled = true, track: { relative_path: string; title?: string } | null = { relative_path: "a.mp3", title: "A" }) =>
    initLyricsPanel({ enabled, apiPath: "/api/lyrics", escHtml: esc, getCurrentTrack: () => track });

  it("disabled -> no-op", () => {
    const p = mk(false);
    p.open("a.mp3", "A");
    expect(p.isOpen()).toBe(false);
    expect(els["lyrics-panel"].classes.has("visible")).toBe(false);
  });

  it("open fetches, renders, caches (no 2nd fetch)", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ lyrics: "la<la" }) });
    vi.stubGlobal("fetch", f);
    const p = mk();
    p.open("a.mp3", "A");
    expect(p.isOpen()).toBe(true);
    expect(els["lyrics-body"].innerHTML).toContain("Lade Songtext");
    expect(els["btn-lyrics"].title).toContain("schlie");
    await flush();
    expect(els["lyrics-body"].innerHTML).toContain("la&lt;la");
    expect(els["btn-lyrics"].classes.has("has-lyrics")).toBe(true);
    expect(f.mock.calls[0][0]).toBe("/api/lyrics?path=a.mp3");
    p.close();
    p.open("a.mp3", "A");
    expect(f).toHaveBeenCalledTimes(1);
    expect(els["lyrics-body"].innerHTML).toContain("la&lt;la");
  });

  it("empty lyrics -> hint, has-lyrics removed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ lyrics: "" }) }));
    const p = mk();
    els["btn-lyrics"].classes.add("has-lyrics");
    p.open("b.mp3", "B");
    await flush();
    expect(els["lyrics-body"].innerHTML).toContain("lyrics-empty");
    expect(els["btn-lyrics"].classes.has("has-lyrics")).toBe(false);
  });

  it("fetch failure -> error message; close before response -> no render", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("x")));
    const p = mk();
    p.open("c.mp3");
    await flush();
    expect(els["lyrics-body"].innerHTML).toContain("konnte nicht geladen");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ lyrics: "zz" }) }));
    p.open("d.mp3");
    p.close();
    const before = els["lyrics-body"].innerHTML;
    await flush();
    expect(els["lyrics-body"].innerHTML).toBe(before);
  });

  it("button toggles; uses current track; close btn closes", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ lyrics: "x" }) }));
    const p = mk();
    els["btn-lyrics"].click();
    expect(p.isOpen()).toBe(true);
    els["btn-lyrics"].click();
    expect(p.isOpen()).toBe(false);
    expect(els["btn-lyrics"].title).toBe("Songtext anzeigen");
    els["btn-lyrics"].click();
    els["lyrics-close-btn"].click();
    expect(p.isOpen()).toBe(false);
    await flush();
  });

  it("button without current track does nothing", () => {
    const p = mk(true, null);
    els["btn-lyrics"].click();
    expect(p.isOpen()).toBe(false);
  });
});

