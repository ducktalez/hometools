import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { installState } from "./helpers";
import {
  deleteUserPlaylist,
  renameUserPlaylist,
  addToPlaylist,
  createAndAddToPlaylist,
  type PlaylistLike,
} from "../src/playlistActions";

const flush = () => new Promise((r) => setTimeout(r, 0));

function hooks() {
  return { apiPath: "/pl", toast: vi.fn(), refreshRoot: vi.fn(), closeModal: vi.fn() };
}
function mockFetch(resp: unknown, ok = true) {
  const f = vi.fn(() => Promise.resolve({ ok, json: () => Promise.resolve(resp) }));
  vi.stubGlobal("fetch", f);
  return f;
}
const pl = (id: string, name = id, items: string[] = []): PlaylistLike => ({ id, name, items });

beforeEach(() => {
  vi.stubGlobal("confirm", vi.fn(() => true));
});
afterEach(() => vi.unstubAllGlobals());

describe("deleteUserPlaylist", () => {
  it("optimistic remove, then server list + revision", async () => {
    const s = installState({ userPlaylists: [pl("a"), pl("b")] });
    const h = hooks();
    mockFetch({ items: [pl("b")], revision: 7 });
    deleteUserPlaylist("a", h);
    expect((s.userPlaylists as PlaylistLike[]).map((p) => p.id)).toEqual(["b"]);
    await flush();
    expect(s.playlistRevision).toBe(7);
    expect(h.toast).toHaveBeenCalledWith("Playlist gelöscht");
  });
  it("declined confirm does nothing", () => {
    const s = installState({ userPlaylists: [pl("a")] });
    vi.stubGlobal("confirm", vi.fn(() => false));
    const f = mockFetch({});
    deleteUserPlaylist("a", hooks());
    expect(s.userPlaylists.length).toBe(1);
    expect(f).not.toHaveBeenCalled();
  });
  it("failure rolls back", async () => {
    const s = installState({ userPlaylists: [pl("a")] });
    const h = hooks();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    deleteUserPlaylist("a", h);
    await flush();
    expect((s.userPlaylists as PlaylistLike[]).map((p) => p.id)).toEqual(["a"]);
    expect(h.toast).toHaveBeenCalledWith("Fehler beim Löschen — rückgängig");
  });
});

describe("renameUserPlaylist", () => {
  it("optimistic rename; failure reverts", async () => {
    installState({ userPlaylists: [pl("a", "Old")] });
    vi.stubGlobal("prompt", vi.fn(() => " New "));
    const h = hooks();
    mockFetch({}, false);
    const target = (globalThis as unknown as { window: { htState: { userPlaylists: PlaylistLike[] } } }).window
      .htState.userPlaylists[0];
    renameUserPlaylist("a", h);
    expect(target.name).toBe("New");
    await flush();
    expect(target.name).toBe("Old");
    expect(h.toast).toHaveBeenCalledWith("Fehler beim Umbenennen");
  });
  it("same/empty name is a no-op", () => {
    installState({ userPlaylists: [pl("a", "Old")] });
    vi.stubGlobal("prompt", vi.fn(() => "Old"));
    const f = mockFetch({});
    renameUserPlaylist("a", hooks());
    expect(f).not.toHaveBeenCalled();
  });
});

describe("addToPlaylist / createAndAdd", () => {
  it("adds locally, closes modal, replaces with server copy", async () => {
    const s = installState({ userPlaylists: [pl("a")] });
    const h = hooks();
    mockFetch({ playlist: pl("a", "A", ["x", "srv"]) });
    addToPlaylist("a", "x", h);
    expect((s.userPlaylists as PlaylistLike[])[0].items).toEqual(["x"]);
    expect(h.closeModal).toHaveBeenCalled();
    await flush();
    expect((s.userPlaylists as PlaylistLike[])[0].items).toEqual(["x", "srv"]);
  });
  it("add failure restores snapshot", async () => {
    const s = installState({ userPlaylists: [pl("a")] });
    const h = hooks();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    addToPlaylist("a", "x", h);
    await flush();
    expect((s.userPlaylists as PlaylistLike[])[0].items).toEqual([]);
    expect(h.toast).toHaveBeenLastCalledWith("Fehler beim Hinzufügen — rückgängig");
  });
  it("create unshifts then adds", async () => {
    const s = installState({ userPlaylists: [] });
    const h = hooks();
    const f = vi.fn((url: string, init?: { method?: string }) =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(init?.method === "POST" && url === "/pl" ? { playlist: pl("n", "N") } : { playlist: pl("n", "N", ["p"]) }),
      }),
    );
    vi.stubGlobal("fetch", f);
    createAndAddToPlaylist("N", "p", h);
    await flush();
    await flush();
    expect((s.userPlaylists as PlaylistLike[])[0].id).toBe("n");
    expect(f).toHaveBeenCalledTimes(2);
  });
  it("create failure toasts", async () => {
    installState();
    const h = hooks();
    mockFetch({}, false);
    createAndAddToPlaylist("N", "p", h);
    await flush();
    expect(h.toast).toHaveBeenCalledWith("Fehler beim Erstellen");
  });
});

