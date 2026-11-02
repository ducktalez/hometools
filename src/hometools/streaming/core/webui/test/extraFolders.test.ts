import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import {
  loadExtraFolders,
  addExtraFolder,
  removeExtraFolder,
  addExtraFolderPlaceholders,
  markExtraFolderCards,
  extraFolderAliases,
  _setExtraFolderAliases,
} from "../src/extraFolders";
import type { ExtraFolderHooks } from "../src/extraFolders";
import type { FolderEntry } from "../src/folderContents";

afterEach(() => {
  vi.unstubAllGlobals();
  _setExtraFolderAliases([]);
});

function hooks(over: Partial<ExtraFolderHooks> = {}): ExtraFolderHooks {
  return { apiBase: "/api/video", isVideo: true, toast: vi.fn(), refreshCatalog: vi.fn(), showFolderView: vi.fn(), ...over };
}
const res = (ok: boolean, body: unknown, status = ok ? 200 : 422) =>
  Promise.resolve({ ok, status, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) });
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("loadExtraFolders", () => {
  it("stores aliases, re-renders root when changed", async () => {
    installState({ allItems: [{ relative_path: "a/b.mp4" } as LegacyMediaItem] });
    vi.stubGlobal("fetch", vi.fn(() => res(true, { items: [{ alias: "xham" }] })));
    const h = hooks();
    await loadExtraFolders(h);
    expect(extraFolderAliases()).toEqual(["xham"]);
    expect(h.showFolderView).toHaveBeenCalled();
  });
  it("cb variant: no re-render, cb called", async () => {
    installState();
    vi.stubGlobal("fetch", vi.fn(() => res(true, { items: [{ alias: "y" }] })));
    const h = hooks();
    const cb = vi.fn();
    await loadExtraFolders(h, cb);
    expect(cb).toHaveBeenCalled();
    expect(h.showFolderView).not.toHaveBeenCalled();
  });
  it("non-video: no fetch", async () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    await loadExtraFolders(hooks({ isVideo: false }));
    expect(f).not.toHaveBeenCalled();
  });
  it("network error calls cb", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    const cb = vi.fn();
    await loadExtraFolders(hooks(), cb);
    expect(cb).toHaveBeenCalled();
  });
});

describe("addExtraFolder", () => {
  it("POSTs path, toasts, reloads catalog", async () => {
    installState();
    vi.stubGlobal("prompt", () => " C:\\x ");
    const f = vi.fn((url: string, init?: { method?: string }) =>
      init && init.method === "POST" ? res(true, { ok: true, folder: { alias: "x" } }) : res(true, { items: [{ alias: "x" }] })
    );
    vi.stubGlobal("fetch", f);
    const h = hooks();
    addExtraFolder(h);
    await flush();
    await flush();
    expect(JSON.parse((f.mock.calls[0][1] as { body: string }).body)).toEqual({ path: "C:\\x" });
    expect(h.toast).toHaveBeenCalledWith(expect.stringContaining('"x"'));
    expect(h.refreshCatalog).toHaveBeenCalled();
  });
  it("shows server detail on failure", async () => {
    vi.stubGlobal("prompt", () => "/nope");
    vi.stubGlobal("fetch", vi.fn(() => res(false, { detail: "Ordner ungültig" })));
    const h = hooks();
    addExtraFolder(h);
    await flush();
    expect(h.toast).toHaveBeenCalledWith("Ordner ungültig");
    expect(h.refreshCatalog).not.toHaveBeenCalled();
  });
  it("404 hints server restart", async () => {
    vi.stubGlobal("prompt", () => "/p");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 404, text: () => Promise.resolve("<html>") })));
    const h = hooks();
    addExtraFolder(h);
    await flush();
    expect(h.toast).toHaveBeenCalledWith(expect.stringContaining("neu starten"));
  });
  it("cancelled prompt does nothing", () => {
    const f = vi.fn();
    vi.stubGlobal("prompt", () => null);
    vi.stubGlobal("fetch", f);
    addExtraFolder(hooks());
    expect(f).not.toHaveBeenCalled();
  });
});

describe("removeExtraFolder", () => {
  it("DELETEs picked alias, leaves removed folder view", async () => {
    const s = installState({ currentPath: "x/sub" });
    vi.stubGlobal("prompt", () => "x");
    const f = vi.fn((url: string, init?: { method?: string }) =>
      init && init.method === "DELETE" ? res(true, { ok: true }) : res(true, { items: [{ alias: "x" }] })
    );
    vi.stubGlobal("fetch", f);
    const h = hooks();
    removeExtraFolder(h);
    await flush();
    await flush();
    await flush();
    expect(f.mock.calls.some((c) => String(c[0]).includes("?alias=x"))).toBe(true);
    expect(s.currentPath).toBe("");
    expect(h.refreshCatalog).toHaveBeenCalled();
  });
  it("empty list -> toast only", async () => {
    vi.stubGlobal("fetch", vi.fn(() => res(true, { items: [] })));
    const h = hooks();
    removeExtraFolder(h);
    await flush();
    expect(h.toast).toHaveBeenCalledWith("Keine hinzugefügten Ordner");
  });
});

describe("placeholders + badge", () => {
  it("adds only missing aliases", () => {
    const existing = { name: "a", displayName: "a", isFavorite: false, count: 2, thumbnail_url: "", thumbnail_lg_url: "", languages: [], variants: null } as FolderEntry;
    const out = addExtraFolderPlaceholders([existing], ["a", "b"]);
    expect(out.map((f) => f.name)).toEqual(["a", "b"]);
    expect(out[1].count).toBe(0);
  });
  it("marks matching cards once", () => {
    const mk = (name: string) => {
      const classes = new Set<string>();
      const kids: unknown[] = [];
      return { dataset: { folder: name }, classList: { add: (c: string) => classes.add(c), contains: (c: string) => classes.has(c) }, appendChild: (k: unknown) => kids.push(k), kids };
    };
    const cards = [mk("x"), mk("other")];
    vi.stubGlobal("document", { createElement: () => ({ className: "", title: "", innerHTML: "" }) });
    const grid = { querySelectorAll: () => cards } as unknown as ParentNode;
    markExtraFolderCards(grid, ["x"]);
    markExtraFolderCards(grid, ["x"]);
    expect(cards[0].kids.length).toBe(1);
    expect(cards[1].kids.length).toBe(0);
  });
});

