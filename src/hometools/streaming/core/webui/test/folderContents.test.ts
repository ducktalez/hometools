import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { contentsAt } from "../src/folderContents";

const names = (c: ReturnType<typeof contentsAt>) => c.folders.map((f) => f.name);

describe("contentsAt", () => {
  it("splits direct sub-folders vs loose files; ignores NAS system folders", () => {
    const all = [
      item("Music/a.mp3"),
      item("Music/Rock/x.mp3", { thumbnail_url: "/t/x" }),
      item("Music/Rock/Sub/y.mp3"),
      item("Music/@eaDir/junk.mp3"),
      item("Music/#recycle/old.mp3"),
    ];
    const c = contentsAt("Music", all, {});
    expect(names(c)).toEqual(["Rock"]);
    expect(c.folders[0]).toMatchObject({ count: 2, thumbnail_url: "/t/x", variants: null });
    expect(c.files.map((f) => f.relative_path)).toEqual(["Music/a.mp3"]);
  });

  it("root level: empty path", () => {
    const c = contentsAt("", [item("A/x"), item("loose")], {});
    expect(names(c)).toEqual(["A"]);
    expect(c.files).toHaveLength(1);
  });

  it("favorites (#) first, then alphabetical; displayName cleaned", () => {
    const c = contentsAt("", [item("b/x"), item("#zfav/x"), item("a/x")], {});
    expect(names(c)).toEqual(["#zfav", "a", "b"]);
    expect(c.folders[0].isFavorite).toBe(true);
    expect(c.folders[0].displayName).not.toMatch(/^#/);
  });

  it("aggregates item languages + subtitle language", () => {
    const c = contentsAt("", [item("S/e1", { language: "en", subtitle_language: "de" }), item("S/e2", { language: "ja" })], {});
    expect(c.folders[0].languages).toEqual(["en", "ja"]);
    expect(c.folders[0].subLang).toBe("de");
  });

  it("langGroups merges folders into one entry with variants", () => {
    const all = [item("Show DE/e1"), item("Show DE/e2"), item("Show EN/e1", { thumbnail_url: "/t/en" })];
    const groups = { "Show DE": "Show", "Show EN": "Show" };
    const c = contentsAt("", all, groups);
    expect(c.folders).toHaveLength(1);
    const f = c.folders[0];
    expect(f.count).toBe(3);
    expect(f.variants?.map((v) => v.name).sort()).toEqual(["Show DE", "Show EN"]);
    expect(f.thumbnail_url).toBe("/t/en"); // primary has none -> group[1] fallback
  });

  it("no merge without shared key", () => {
    const c = contentsAt("", [item("A/x"), item("B/x")], {});
    expect(c.folders.every((f) => f.variants === null)).toBe(true);
  });
});

