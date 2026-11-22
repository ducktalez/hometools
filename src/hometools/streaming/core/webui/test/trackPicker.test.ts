import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { emptyManualPlaylistId, emptyPlaylistHtml, pickerMatches, isManualPlaylistView, reloadPlaylistView, ADD_BTN_ID } from "../src/trackPicker";

afterEach(() => vi.unstubAllGlobals());

describe("emptyManualPlaylistId", () => {
  const pls = [
    { id: "m", name: "M", items: [] },
    { id: "s", name: "S", smart: { rules: [] } },
  ];
  it("empty manual playlist in view -> id", () => {
    installState({ inPlaylist: true, currentPlaylistId: "m", playlistItems: [], userPlaylists: pls });
    expect(emptyManualPlaylistId()).toBe("m");
  });
  it("smart, virtual, non-empty or not in playlist -> ''", () => {
    installState({ inPlaylist: true, currentPlaylistId: "s", playlistItems: [], userPlaylists: pls });
    expect(emptyManualPlaylistId()).toBe("");
    installState({ inPlaylist: true, currentPlaylistId: "__favorites__", playlistItems: [], userPlaylists: pls });
    expect(emptyManualPlaylistId()).toBe("");
    installState({ inPlaylist: true, currentPlaylistId: "m", playlistItems: [item("a")], userPlaylists: pls });
    expect(emptyManualPlaylistId()).toBe("");
    installState({ inPlaylist: false, currentPlaylistId: "m", playlistItems: [], userPlaylists: pls });
    expect(emptyManualPlaylistId()).toBe("");
  });
});

describe("emptyPlaylistHtml", () => {
  it("contains the add button", () => {
    const html = emptyPlaylistHtml();
    expect(html).toContain('id="' + ADD_BTN_ID + '"');
    expect(html).toContain("btn-add-tracks");
  });
});

describe("pickerMatches", () => {
  const items = [
    { ...item("a/one.mp3"), title: "One", artist: "Zed" },
    { ...item("a/two.mp3"), title: "Two", artist: "Yan" },
  ] as CatalogItem[];
  it("filters by title/artist/path, case-insensitive", () => {
    expect(pickerMatches(items, "zed").shown).toHaveLength(1);
    expect(pickerMatches(items, "TWO").shown[0].title).toBe("Two");
    expect(pickerMatches(items, "a/").shown).toHaveLength(2);
  });
  it("caps results but reports total", () => {
    const r = pickerMatches(items, "", 1);
    expect(r.shown).toHaveLength(1);
    expect(r.total).toBe(2);
  });
});

describe("isManualPlaylistView", () => {
  const pls = [
    { id: "m", name: "M", items: [] },
    { id: "s", name: "S", smart: { rules: [] } },
  ];
  it("true only for manual user playlist in view", () => {
    installState({ inPlaylist: true, currentPlaylistId: "m", userPlaylists: pls });
    expect(isManualPlaylistView()).toBe(true);
    installState({ inPlaylist: true, currentPlaylistId: "s", userPlaylists: pls });
    expect(isManualPlaylistView()).toBe(false);
    installState({ inPlaylist: true, currentPlaylistId: "__folder__", userPlaylists: pls });
    expect(isManualPlaylistView()).toBe(false);
    installState({ inPlaylist: false, currentPlaylistId: "m", userPlaylists: pls });
    expect(isManualPlaylistView()).toBe(false);
  });
});

describe("reloadPlaylistView", () => {
  it("re-resolves and applies filter while playlist still shown", () => {
    const st = installState({ inPlaylist: true, currentPlaylistId: "m", playlistItems: [] });
    const apply = vi.fn();
    reloadPlaylistView("m", () => ({ resolved: [item("a")] }), apply, true);
    expect(st.playlistItems).toHaveLength(1);
    expect(apply).toHaveBeenCalledWith(true);
  });
  it("no-op after navigation away; empty when unresolvable", () => {
    const st = installState({ inPlaylist: true, currentPlaylistId: "other", playlistItems: [] });
    const apply = vi.fn();
    reloadPlaylistView("m", () => ({ resolved: [item("a")] }), apply);
    expect(apply).not.toHaveBeenCalled();
    st.currentPlaylistId = "m";
    reloadPlaylistView("m", () => null, apply);
    expect(st.playlistItems).toEqual([]);
    expect(apply).toHaveBeenCalledTimes(1);
  });
});
