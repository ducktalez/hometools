import { describe, it, expect } from "vitest";
import { trackRowHtml, trackRowsHtml, searchFolderRowHtml, searchResultRowHtml, type TrackRowCtx } from "../src/trackRows";

const ctx = (p: Partial<TrackRowCtx> = {}): TrackRowCtx => ({
  escHtml: (s) => String(s).replace(/</g, "&lt;"),
  fmtTime: (n) => "T" + n,
  showOrig: false,
  currentIndex: -1,
  bpmCalcEnabled: false,
  trackViewMode: "list",
  isVideoMode: false,
  metadataEditEnabled: true,
  playlistsEnabled: true,
  itemNoun: "track",
  bpmMin: 60,
  bpmMax: 200,
  dupePaths: null,
  dupeSafety: null,
  filePlaceholder: "PH",
  ic: { folderPlay: "P", trash: "TR", dl: "DL", pin: "PIN", edit: "ED", playlist: "PL", queue: "Q", dots: "D" },
  renderBpmPill: (bpm) => "<bpm:" + bpm + ">",
  renderInlineRating: () => "<rating>",
  renderMoveWidget: () => "<move>",
  ...p,
});
const item = (o: Record<string, unknown> = {}) =>
  ({ relative_path: "a/b.mp4", title: "T<", stream_url: "/s", duration: 61, ...o }) as never;

describe("trackRowHtml", () => {
  it("missing episode", () => {
    const h = trackRowHtml(item({ _missing: true, season: 1, episode: 2 }), 0, ctx());
    expect(h).toContain("missing-episode");
    expect(h).toContain("S01E02");
    expect(h).toContain("Folge fehlt");
  });
  it("debug filtered", () => {
    const h = trackRowHtml(item({ _debugReason: "why", rating: 5 }), 0, ctx());
    expect(h).toContain("debug-filtered");
    expect(h).toContain("why");
    expect(h).toContain("width:100%");
  });
  it("normal row: numbering, escaping, buttons, flags", () => {
    const h = trackRowHtml(item({ bpm: 120 }), 3, ctx({ currentIndex: 3 }));
    expect(h).toContain('track-item active" data-index="3"');
    expect(h).toContain('num-text">4<');
    expect(h).toContain("T&lt;");
    expect(h).toContain("T61");
    expect(h).toContain("<bpm:120>");
    expect(h).toContain("track-edit-btn");
    expect(h).toContain("track-playlist-btn");
    expect(h).toContain("<rating><move></li>");
    expect(h).toContain('data-media-type="track"');
  });
  it("series label, optional buttons off, video no bpm", () => {
    const h = trackRowHtml(item({ season: 2, episode: 5 }), 0, ctx({ metadataEditEnabled: false, playlistsEnabled: false, isVideoMode: true }));
    expect(h).toContain("S02E05");
    expect(h).not.toContain("track-edit-btn");
    expect(h).not.toContain("track-playlist-btn");
    expect(h).not.toContain("track-bpm-cell");
  });
  it("dupe badge safe vs warn", () => {
    const base = { dupePaths: new Set(["a/b.mp4"]) };
    expect(trackRowHtml(item(), 0, ctx({ ...base, dupeSafety: { "a/b.mp4": true } }))).toContain("track-delete-btn--safe");
    expect(trackRowHtml(item(), 0, ctx({ ...base, dupeSafety: {} }))).toContain("track-delete-btn--warn");
  });
  it("table editable only when tools active", () => {
    const h = trackRowHtml(item(), 0, ctx({ trackViewMode: "table", showOrig: true }));
    expect(h).toContain('contenteditable="true"');
    expect(h).toContain('data-field="title"');
    expect(trackRowHtml(item(), 0, ctx({ trackViewMode: "table" }))).not.toContain("contenteditable");
  });
  it("convert badge for non-native ext", () => {
    expect(trackRowHtml(item({ relative_path: "x.avi" }), 0, ctx())).toContain("convert-badge");
  });
});

describe("trackRowsHtml", () => {
  it("uses realIdxMap and range", () => {
    const items = [item({ relative_path: "1.mp4" }), item({ relative_path: "2.mp4" }), item({ relative_path: "3.mp4" })];
    const h = trackRowsHtml(items, [10, 11, 12], 1, 3, ctx());
    expect(h).not.toContain('data-index="10"');
    expect(h).toContain('data-index="11"');
    expect(h).toContain('data-index="12"');
  });
});

describe("search rows", () => {
  const esc = (s: unknown) => String(s);
  it("folder row with parent dir", () => {
    const h = searchFolderRowHtml({ path: "a/b", name: "b", count: 3 }, esc, "PH", "P");
    expect(h).toContain("(3)");
    expect(h).toContain('search-result-folder">a<');
    expect(searchFolderRowHtml({ path: "b", name: "b", count: 1 }, esc, "PH", "P")).not.toContain("search-result-folder");
  });
  it("result row", () => {
    const h = searchResultRowHtml({ relative_path: "x/y.mp3", title: "", rating: 5 } as never, 1, esc, "PH");
    expect(h).toContain('track-number">2<');
    expect(h).toContain("x/y.mp3");
    expect(h).toContain("rating-bar");
    expect(h).toContain('search-result-folder">x<');
  });
});

