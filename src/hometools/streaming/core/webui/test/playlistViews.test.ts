import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import {
  showUserPlaylistView,
  playUserPlaylist,
  openPlaylistModal,
  closePlaylistModal,
  renderPlaylistModalList,
} from "../src/playlistViews";

const hooks = (over: Record<string, unknown> = {}) => ({
  toast: vi.fn(),
  esc: (s: unknown) => String(s),
  enterTrackListView: vi.fn(),
  applyFilter: vi.fn(),
  playTrack: vi.fn(),
  savedFavorites: () => ({}) as Record<string, boolean>,
  sortFavoritesByOrder: (x: LegacyMediaItem[]) => x,
  loadFavoritesOrder: () => [] as string[],
  loadFavoritesOrderAsync: vi.fn(),
  resolvePlaylist: () => null as { pl: { name?: string }; resolved: LegacyMediaItem[] } | null,
  addToPlaylist: vi.fn(),
  ...over,
});
afterEach(() => vi.unstubAllGlobals());

describe("showUserPlaylistView", () => {
  it("__alltitles__: empty library toasts, else enters view", () => {
    const h = hooks();
    installState();
    showUserPlaylistView("__alltitles__", h);
    expect(h.toast).toHaveBeenCalledWith("Keine Titel in der Bibliothek vorhanden");
    const s = installState({ allItems: [item("a")], currentPath: "X" });
    showUserPlaylistView("__alltitles__", h);
    expect(s).toMatchObject({ currentPlaylistId: "__alltitles__", inPlaylist: true, currentPath: "" });
    expect(s.playlistItems).not.toBe(s.allItems);
    expect(h.enterTrackListView).toHaveBeenCalledWith({ title: "Titel" });
  });
  it("__favorites__: filters saved, re-sorts when server order differs", () => {
    const all = [item("a"), item("b")];
    const s = installState({ allItems: all });
    let cb: (o: string[]) => void = () => {};
    const h = hooks({
      savedFavorites: () => ({ b: true }),
      loadFavoritesOrder: () => ["x"],
      loadFavoritesOrderAsync: (f: (o: string[]) => void) => (cb = f),
    });
    showUserPlaylistView("__favorites__", h);
    expect(s.playlistItems.map((i) => i.relative_path)).toEqual(["b"]);
    cb(["y"]);
    expect(h.applyFilter).toHaveBeenCalledTimes(1);
    cb(["x"]); // same as local -> no re-sort
    expect(h.applyFilter).toHaveBeenCalledTimes(1);
    s.currentPlaylistId = "other";
    cb(["z"]); // view left -> ignored
    expect(h.applyFilter).toHaveBeenCalledTimes(1);
  });
  it("__favorites__ with none toasts", () => {
    installState({ allItems: [item("a")] });
    const h = hooks();
    showUserPlaylistView("__favorites__", h);
    expect(h.toast).toHaveBeenCalledWith("Keine Favoriten vorhanden");
    expect(h.enterTrackListView).not.toHaveBeenCalled();
  });
  it("user playlist: resolved or not-found toast", () => {
    const s = installState();
    const h = hooks({ resolvePlaylist: () => ({ pl: { name: "P" }, resolved: [item("a")] }) });
    showUserPlaylistView("p", h);
    expect(s.currentPlaylistId).toBe("p");
    expect(h.enterTrackListView).toHaveBeenCalledWith({ title: "P" });
    const h2 = hooks();
    showUserPlaylistView("q", h2);
    expect(h2.toast).toHaveBeenCalledWith("Keine Titel in dieser Playlist gefunden");
  });
});

describe("playUserPlaylist", () => {
  it("plays first track only if list changed and non-empty", () => {
    installState();
    const h = hooks({ resolvePlaylist: () => ({ pl: {}, resolved: [item("a")] }) });
    playUserPlaylist("p", h);
    expect(h.playTrack).toHaveBeenCalledWith(0);
    const h2 = hooks();
    playUserPlaylist("none", h2);
    expect(h2.playTrack).not.toHaveBeenCalled();
  });
});

describe("playlist modal", () => {
  function stubDom() {
    const backdrop = { hidden: true };
    const classes = new Set<string>();
    const listEl = { innerHTML: "", querySelectorAll: vi.fn(() => []) };
    vi.stubGlobal("document", {
      getElementById: (id: string) => (id === "playlist-modal-backdrop" ? backdrop : id === "playlist-modal-list" ? listEl : null),
      body: { classList: { add: (c: string) => classes.add(c), remove: (c: string) => classes.delete(c) } },
    });
    return { backdrop, classes, listEl };
  }
  it("open shows modal + stores path; close resets", () => {
    const s = installState({ userPlaylists: [{ id: "a", name: "A", items: [] }] });
    const { backdrop, classes, listEl } = stubDom();
    openPlaylistModal("x.mp3", hooks());
    expect(backdrop.hidden).toBe(false);
    expect(classes.has("modal-open")).toBe(true);
    expect(s.playlistAddPath).toBe("x.mp3");
    expect(listEl.innerHTML).toContain('data-id="a"');
    closePlaylistModal();
    expect(backdrop.hidden).toBe(true);
    expect(classes.has("modal-open")).toBe(false);
    expect(s.playlistAddPath).toBe("");
  });
  it("list click adds current path to clicked playlist", () => {
    installState({ playlistAddPath: "p.mp3" });
    const { listEl } = stubDom();
    let click: () => void = () => {};
    listEl.querySelectorAll = vi.fn(() => [
      { dataset: { id: "a" }, addEventListener: (_: string, f: () => void) => (click = f) },
    ]) as never;
    const h = hooks();
    renderPlaylistModalList(h);
    click();
    expect(h.addToPlaylist).toHaveBeenCalledWith("a", "p.mp3");
  });
});

