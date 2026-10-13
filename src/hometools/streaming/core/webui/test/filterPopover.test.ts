import { describe, it, expect } from "vitest";
import { filterPopoverBodyHtml, filterCombinedChipView, filterHiddenChipView } from "../src/filterPopover";
const icons = { starFilled: "[F]", starEmpty: "[E]" };
const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
describe("filterPopoverBodyHtml", () => {
  it("stars active up to rating; titles singular/plural", () => {
    const h = filterPopoverBodyHtml([], { rating: 2, fav: false, genre: "" }, icons, esc);
    expect(h).toContain('data-star="1" title="1+ Stern">[F]');
    expect(h).toContain('filter-popover-star active" data-star="2" title="2+ Sterne">[F]');
    expect(h).toContain('data-star="3" title="3+ Sterne">[E]');
  });
  it("no genre section without genres", () => {
    expect(filterPopoverBodyHtml([], { rating: 0, fav: false, genre: "" }, icons, esc)).not.toContain("genre-select");
  });
  it("genre select escapes + marks selected", () => {
    const h = filterPopoverBodyHtml(["A<b", "Rock"], { rating: 0, fav: false, genre: "Rock" }, icons, esc);
    expect(h).toContain('<option value="A&lt;b">A&lt;b</option>');
    expect(h).toContain('<option value="Rock" selected>Rock</option>');
  });
  it("fav checkbox checked", () => {
    expect(filterPopoverBodyHtml([], { rating: 0, fav: true, genre: "" }, icons, esc)).toContain('fav" checked>');
  });
});describe("filterCombinedChipView", () => {
  it("inactive", () => {
    const v = filterCombinedChipView({ rating: 0, fav: false, genre: "" }, "[I]");
    expect(v).toEqual({ html: "[I] Filtern", active: false, title: "Filtern (Bewertung, Favoriten, Genre)" });
  });
  it("counts active filters", () => {
    const v = filterCombinedChipView({ rating: 3, fav: true, genre: "" }, "[I]");
    expect(v.html).toBe("[I] Filtern (2)");
    expect(v.active).toBe(true);
    expect(v.title).toContain("2 Filter aktiv");
  });
});
describe("filterHiddenChipView", () => {
  const items = [{ rating: 1 }, { rating: 2 }, { rating: 0 }, {}];
  it("null when threshold off", () => {
    expect(filterHiddenChipView(items, 0, false, "[E]")).toBeNull();
  });
  it("counts rated below threshold only", () => {
    const v = filterHiddenChipView(items, 2, false, "[E]")!;
    expect(v.html).toBe("[E] Ausgeblendet (1/4)");
    expect(v.active).toBe(true);
    expect(v.title).toBe("Ausgeblendete Songs einblenden");
  });
  it("showHidden flips active/title", () => {
    const v = filterHiddenChipView(items, 3, true, "[E]")!;
    expect(v.active).toBe(false);
    expect(v.title).toContain("sichtbar");
  });
});