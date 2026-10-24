import { describe, it, expect } from "vitest";
import { indexProgressPercent, indexingToastHtml, TRACK_TABLE_HEADER_HTML, viewToggleView } from "../src/chromeHtml";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");

describe("indexProgressPercent", () => {
  it("build_percent wins, then percent, else null", () => {
    expect(indexProgressPercent({ build_percent: 40, percent: 5 })).toBe(40);
    expect(indexProgressPercent({ percent: 5 })).toBe(5);
    expect(indexProgressPercent({ percent: "5" })).toBeNull();
    expect(indexProgressPercent(null)).toBeNull();
    expect(indexProgressPercent(3)).toBeNull();
  });
});

describe("indexingToastHtml", () => {
  it("default message, no bar", () => {
    const h = indexingToastHtml("", null, esc);
    expect(h).toContain("Indexing\u2026");
    expect(h).not.toContain("ht-index-progress");
  });
  it("bar clamped 2..100, escaped msg", () => {
    expect(indexingToastHtml("a<", { percent: 0 }, esc)).toContain("width:2%");
    expect(indexingToastHtml("x", { percent: 250 }, esc)).toContain("width:100%");
    expect(indexingToastHtml("a<", { percent: 50 }, esc)).toContain("a&lt;");
    expect(indexingToastHtml("x", { percent: -1 }, esc)).not.toContain("ht-index-progress");
  });
});

describe("table header / viewToggleView", () => {
  it("header has 9 columns", () => expect(TRACK_TABLE_HEADER_HTML.match(/<span/g)).toHaveLength(9));
  it("toggle view", () => {
    expect(viewToggleView(true, false)).toMatchObject({ useListIcon: true, locked: false });
    expect(viewToggleView(false, true)).toMatchObject({ useListIcon: false, locked: true });
    expect(viewToggleView(true, false).title).toContain("Detailansicht");
    expect(viewToggleView(false, false).title).toContain("Listenansicht");
  });
});

