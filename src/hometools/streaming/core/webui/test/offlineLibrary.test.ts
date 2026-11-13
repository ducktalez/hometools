import { describe, it, expect } from "vitest";
import { downloadToItem, readyItems, usageLabel } from "../src/offlineLibrary";

describe("offlineLibrary helpers", () => {
  it("downloadToItem fills defaults", () => {
    const it = downloadToItem({ streamUrl: "/s/a.mp3" }, "audio");
    expect(it.title).toBe("Offline-Download");
    expect(it.relative_path).toBe("/s/a.mp3");
    expect(it.media_type).toBe("audio");
    expect(it.rating).toBe(0);
  });
  it("downloadToItem keeps metadata", () => {
    const it = downloadToItem(
      { streamUrl: "/s", title: "T", artist: "A", relativePath: "x/T.mp3", thumbnailUrl: "/t", mediaType: "video" },
      "audio"
    );
    expect(it).toMatchObject({ title: "T", artist: "A", relative_path: "x/T.mp3", thumbnail_url: "/t", media_type: "video" });
  });
  it("readyItems filters non-ready and sorts by title", () => {
    const { ready, items } = readyItems(
      [
        { streamUrl: "/b", title: "b", status: "ready", timestamp: 1 },
        { streamUrl: "/a", title: "a", status: "ready", timestamp: 2 },
        { streamUrl: "/c", title: "c", status: "pending" },
      ],
      "title",
      "audio"
    );
    expect(ready).toHaveLength(2);
    expect(items.map((i) => i.title)).toEqual(["a", "b"]);
  });
  it("usageLabel pluralizes", () => {
    const f = (n: number) => n + "B";
    expect(usageLabel(1, 5, f)).toBe("1 download \u00b7 5B");
    expect(usageLabel(2, 5, f)).toBe("2 downloads \u00b7 5B");
  });
});

