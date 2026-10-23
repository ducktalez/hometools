import { describe, it, expect } from "vitest";
import { recentCardsHtml, recentPlayContext } from "../src/recentlyPlayed";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
const mk = (p: string) => ({ relative_path: p }) as never;

describe("recentCardsHtml", () => {
  it("placeholder styling + no progress bar <=2%", () => {
    const h = recentCardsHtml([{ relative_path: "a/b.mp4", progress_pct: 2 }], esc, "PH");
    expect(h).toContain('src="PH"');
    expect(h).toContain("object-fit:contain");
    expect(h).not.toContain("recent-progress-bar");
    expect(h).toContain('data-pos="0"');
    expect(h).toContain('<div class="recent-title">a/b.mp4</div>');
  });
  it("real thumb, clamped progress, escaped title", () => {
    const h = recentCardsHtml(
      [{ relative_path: "x.mp4", thumbnail_url: "/t", progress_pct: 150, title: "<T>", position_seconds: 42, artist: "A" }],
      esc,
      "PH"
    );
    expect(h).toContain('src="/t"');
    expect(h).not.toContain("object-fit");
    expect(h).toContain("width:100%");
    expect(h).toContain("&lt;T>");
    expect(h).toContain('data-pos="42"');
    expect(h).toContain('<div class="recent-sub">A</div>');
  });
});

describe("recentPlayContext", () => {
  const all = [mk("s/e1.mp4"), mk("s/e2.mp4"), mk("s/sub/e3.mp4"), mk("root.mp4")];
  it("null if unknown", () => expect(recentPlayContext("nope", all)).toBeNull());
  it("folder siblings only direct children", () => {
    const c = recentPlayContext("s/e1.mp4", all)!;
    expect(c.folder).toBe("s");
    expect(c.folderItems.map((i) => i.relative_path)).toEqual(["s/e1.mp4", "s/e2.mp4"]);
  });
  it("root level", () => {
    const c = recentPlayContext("root.mp4", all)!;
    expect(c.folder).toBe("");
    expect(c.folderItems.map((i) => i.relative_path)).toEqual(["root.mp4"]);
  });
  it("nested leaf folder", () => {
    expect(recentPlayContext("s/sub/e3.mp4", all)!.folderItems).toHaveLength(1);
  });
});

