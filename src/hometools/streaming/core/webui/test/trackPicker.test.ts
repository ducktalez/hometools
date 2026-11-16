import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { emptyManualPlaylistId, emptyPlaylistHtml, pickerMatches, ADD_BTN_ID } from "../src/trackPicker";

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
  ] as LegacyMediaItem[];
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

