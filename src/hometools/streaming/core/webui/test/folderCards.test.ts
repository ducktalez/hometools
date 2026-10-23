import { describe, it, expect } from "vitest";
import { folderCardHtml, fileCardHtml, type FolderCardOpts } from "../src/folderCards";
import type { FolderEntry } from "../src/folderContents";

const o: FolderCardOpts = {
  escHtml: (s) => String(s).replace(/</g, "&lt;"),
  viewMode: "grid",
  showOrigNames: false,
  isVideo: false,
  itemNoun: "track",
  defaultLang: "de",
  audiobookDirs: ["Hoerbuch"],
  langNames: { de: "Deutsch", en: "English" },
  folderPlaceholder: "FP",
  filePlaceholder: "XP",
  icStar: "*",
  icFolderPlay: ">",
  compositeFlagHtml: (l, s) => (l ? "[" + l + (s ? "+" + s : "") + "]" : ""),
  langBadgesHtml: (ls) => ls.map((l) => "<" + l + ">").join(""),
};
const f = (p: Partial<FolderEntry> = {}): FolderEntry => ({
  name: "A", displayName: "A", isFavorite: false, count: 1, thumbnail_url: "", thumbnail_lg_url: "",
  languages: [], variants: null, ...p,
});

describe("folderCardHtml", () => {
  it("singular/plural noun + placeholder", () => {
    expect(folderCardHtml(f(), o)).toContain("1 track</div>");
    expect(folderCardHtml(f({ count: 3 }), o)).toContain("3 tracks</div>");
    expect(folderCardHtml(f(), o)).toContain('src="FP"');
  });
  it("thumb choice by view mode", () => {
    const e = f({ thumbnail_url: "s", thumbnail_lg_url: "l" });
    expect(folderCardHtml(e, o)).toContain('src="l"');
    expect(folderCardHtml(e, { ...o, viewMode: "list" })).toContain('src="s"');
  });
  it("favorite, audiobook classes + badges", () => {
    const h = folderCardHtml(f({ name: "Hoerbuch X", isFavorite: true, languages: ["de"] }), o);
    expect(h).toContain("fav-folder audiobook-folder");
    expect(h).toContain("fav-badge");
    expect(h).toContain("A <de>");
  });
  it("showOrigNames hides badges, uses raw name", () => {
    const h = folderCardHtml(f({ name: "#A", displayName: "A", isFavorite: true, languages: ["de"] }), { ...o, showOrigNames: true });
    expect(h).not.toContain("fav-badge");
    expect(h).toContain(">#A<");
    expect(h).not.toContain("<de>");
  });
  it("video corner flag, default lang fallback, no inline badge", () => {
    const h = folderCardHtml(f({ languages: [] }), { ...o, isVideo: true });
    expect(h).toContain('folder-lang-corner">[de]');
    expect(h).not.toContain("<de>");
  });
  it("variants: sorted, default lang first, buttons + data attr", () => {
    const v = [
      { name: "x-en", lang: "en", subLang: "", count: 2 },
      { name: "x-de", lang: "de", subLang: "en", count: 3 },
    ];
    const h = folderCardHtml(f({ variants: v, count: 5 }), o);
    expect(h).toContain("multi-lang-folder");
    expect(h).toContain("data-variants=");
    expect(h.indexOf('data-variant-name="x-de"')).toBeLessThan(h.indexOf('data-variant-name="x-en"'));
    expect(h).toContain("Deutsch + English Sub (3)");
    expect(h).not.toContain("folder-lang-corner");
  });
});

describe("fileCardHtml", () => {
  it("rating bar + idx + escaped", () => {
    const h = fileCardHtml({ title: "<T>", artist: "Ar", rating: 5 } as never, 4, o);
    expect(h).toContain('data-file-idx="4"');
    expect(h).toContain("width:100%");
    expect(h).toContain("&lt;T>");
    expect(h).toContain('src="XP"');
  });
  it("no rating", () => {
    expect(fileCardHtml({ title: "t", rating: 0 } as never, 0, o)).not.toContain("rating-bar");
  });
});



