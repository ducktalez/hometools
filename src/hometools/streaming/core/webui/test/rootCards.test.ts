import { describe, it, expect } from "vitest";
import { toolsRowHtml, favoritesCardHtml, playlistCardHtml, type ToolsRowOpts } from "../src/rootCards";

const base: ToolsRowOpts = {
  isRoot: true, playlistsEnabled: true, offlineEnabled: true, isVideo: false, allItemsCount: 5,
  icSmartPlaylist: "SM", icPlaylist: "PL", icDl: "DL", icRefresh: "RF",
};

describe("toolsRowHtml", () => {
  it("audio root: all buttons in order", () => {
    const h = toolsRowHtml(base);
    const ids = ["playlist-new-card", "smart-playlist-new-card", "all-titles-card", "offline-folder-card", "refresh-catalog-card"];
    const pos = ids.map((i) => h.indexOf('id="' + i + '"'));
    expect(pos.every((p) => p >= 0)).toBe(true);
    expect([...pos].sort((a, b) => a - b)).toEqual(pos);
    expect(h).toContain('tools-row-count">5<');
  });
  it("video: no playlist tools", () => {
    const h = toolsRowHtml({ ...base, isVideo: true });
    expect(h).not.toContain("playlist-new-card");
    expect(h).toContain("offline-folder-card");
  });
  it("count hidden at 0; not root -> empty", () => {
    expect(toolsRowHtml({ ...base, allItemsCount: 0 })).not.toContain('tools-row-count">0<span');
    expect(toolsRowHtml({ ...base, isRoot: false })).toBe("");
  });
  it("root, nothing enabled -> only refresh", () => {
    const h = toolsRowHtml({ ...base, playlistsEnabled: false, offlineEnabled: false });
    expect(h).toContain("refresh-catalog-card");
    expect(h).not.toContain("offline-folder-card");
  });
});

describe("favoritesCardHtml", () => {
  it("0 -> empty", () => expect(favoritesCardHtml(0, "S", "P")).toBe(""));
  it("count", () => expect(favoritesCardHtml(3, "S", "P")).toContain("3 Titel"));
});

describe("playlistCardHtml", () => {
  const o = { escHtml: (s: unknown) => String(s).replace(/</g, "&lt;"), icPlaylist: "PL", icSmartPlaylist: "SM", icFolderPlay: "FP", icDots: "D" };
  it("normal", () => {
    const h = playlistCardHtml({ id: "i<", name: "N" }, 2, o);
    expect(h).toContain('data-playlist-id="i&lt;"');
    expect(h).not.toContain("smart-playlist-card");
    expect(h).toContain("2 Titel");
  });
  it("smart", () => {
    const h = playlistCardHtml({ id: "i", name: "N", smart: { rules: [] } }, 0, o);
    expect(h).toContain("smart-playlist-card");
    expect(h).toContain("smart-pl-badge");
  });
});

