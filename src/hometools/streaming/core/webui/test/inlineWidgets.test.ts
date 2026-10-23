import { describe, it, expect } from "vitest";
import { inlineRatingHtml, moveQuickPicks, moveWidgetHtml } from "../src/inlineWidgets";

describe("inlineRatingHtml", () => {
  it("disabled -> empty", () => expect(inlineRatingHtml(3, 0, false, "F", "E")).toBe(""));
  it("rounds, fills, titles", () => {
    const h = inlineRatingHtml(2.6, 7, true, "F", "E");
    expect(h.match(/ active"/g)).toHaveLength(3);
    expect(h).toContain('title="1 Stern"');
    expect(h).toContain('title="2 Sterne"');
    expect(h).toContain(">F</button>");
    expect(h).toContain(">E</button>");
    expect(h).toContain('data-index="7"');
  });
  it("undefined rating -> none active", () => {
    expect(inlineRatingHtml(undefined, 0, true, "F", "E")).not.toContain(" active");
  });
});

describe("moveQuickPicks", () => {
  it("MRU first, topped up without dupes", () => {
    expect(moveQuickPicks(["b"], ["a", "b", "c", "d", "e"])).toEqual(["b", "a", "c", "d"]);
  });
  it("caps at 4 recent", () => {
    expect(moveQuickPicks(["1", "2", "3", "4", "5"], ["x"])).toEqual(["1", "2", "3", "4"]);
  });
  it("fewer folders than 4", () => {
    expect(moveQuickPicks([], ["a"])).toEqual(["a"]);
  });
});

describe("moveWidgetHtml", () => {
  const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
  it("current folder flagged + selected, trash button", () => {
    const h = moveWidgetHtml(2, "b", [], ["a", "b"], esc, "TR");
    expect(h).toContain('move-quick-btn is-current" data-target="b"');
    expect(h).toContain('<option value="b" selected>');
    expect(h).toContain("<option value=\"\" disabled>");
    expect(h).toContain(">TR</button>");
  });
  it("no current folder -> placeholder selected; escaped", () => {
    const h = moveWidgetHtml(0, "", [], ["<x"], esc, "TR");
    expect(h).toContain('disabled selected>Ordner w\u00e4hlen\u2026');
    expect(h).toContain("&lt;x");
  });
});

