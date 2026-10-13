import { describe, it, expect } from "vitest";
import {
  nextShuffleMode,
  nextRepeatMode,
  shuffleBtnView,
  repeatBtnView,
  playerRatingStars,
  ratingBarWidthPct,
  editModalRatingStars,
  toggleEditRating,
  favoriteBtnView,
} from "../src/playerControls";
describe("mode cycles", () => {
  it("shuffle off>normal>weighted>off", () => {
    expect(nextShuffleMode(false)).toBe("normal");
    expect(nextShuffleMode("")).toBe("normal");
    expect(nextShuffleMode("normal")).toBe("weighted");
    expect(nextShuffleMode("weighted")).toBe(false);
  });
  it("repeat off>all>one>off", () => {
    expect(nextRepeatMode(false)).toBe("all");
    expect(nextRepeatMode("all")).toBe("one");
    expect(nextRepeatMode("one")).toBe(false);
  });
});
describe("button views", () => {
  it("shuffle", () => {
    expect(shuffleBtnView(false)).toMatchObject({ active: false, variant: false, title: "Shuffle aktivieren" });
    expect(shuffleBtnView("normal")).toMatchObject({ active: true, variant: false });
    expect(shuffleBtnView("weighted")).toMatchObject({ active: true, variant: true });
    expect(shuffleBtnView("weighted").title).toContain("gewichtet");
  });
  it("repeat", () => {
    expect(repeatBtnView(false).title).toBe("Wiederholen aktivieren");
    expect(repeatBtnView("all")).toMatchObject({ active: true, variant: false });
    expect(repeatBtnView("one")).toMatchObject({ active: true, variant: true });
  });
});
describe("rating", () => {
  it("stars: rounded, active up to rating, clear-hint on current", () => {
    const s = playerRatingStars(3.4);
    expect(s.map((x) => x.active)).toEqual([true, true, true, false, false]);
    expect(s[2].title).toContain("entfernen");
    expect(s[0].title).toBe("1 Stern");
    expect(s[1].title).toBe("2 Sterne");
  });
  it("stars: none for 0/null (no clear hint)", () => {
    expect(playerRatingStars(null).every((x) => !x.active && !x.title.includes("entfernen"))).toBe(true);
  });
  it("bar width", () => {
    expect(ratingBarWidthPct(0)).toBe(0);
    expect(ratingBarWidthPct(null)).toBe(0);
    expect(ratingBarWidthPct(2.5)).toBe(50);
  });
});describe("edit modal + favorites", () => {
  it("editModalRatingStars: rounded + plain titles", () => {
    const r = editModalRatingStars(2.6);
    expect(r.rounded).toBe(3);
    expect(r.stars.map((s) => s.active)).toEqual([true, true, true, false, false]);
    expect(r.stars[0].title).toBe("1 Stern");
    expect(r.stars[2].title).toBe("3 Sterne");
    expect(editModalRatingStars(null).rounded).toBe(0);
  });
  it("toggleEditRating clears on same star", () => {
    expect(toggleEditRating(3, 3)).toBe(0);
    expect(toggleEditRating(4, 3)).toBe(4);
  });
  it("favoriteBtnView", () => {
    expect(favoriteBtnView(true)).toEqual({ pinned: true, title: "Favorit entfernen" });
    expect(favoriteBtnView(false)).toEqual({ pinned: false, title: "Favorit" });
  });
});