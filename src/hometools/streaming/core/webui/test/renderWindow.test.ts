import { describe, it, expect } from "vitest";
import { batchEnd, displayIndexOf, renderTargetFor, jumpTarget } from "../src/renderWindow";

describe("batchEnd", () => {
  it("clamps to total", () => {
    expect(batchEnd(0, 50, 120)).toBe(50);
    expect(batchEnd(100, 50, 120)).toBe(120);
  });
  it("<= offset when exhausted", () => expect(batchEnd(120, 50, 120)).toBeLessThanOrEqual(120));
});

describe("displayIndexOf / renderTargetFor", () => {
  const map = [5, 6, 7, 9];
  it("lookup", () => {
    expect(displayIndexOf(map, 7)).toBe(2);
    expect(displayIndexOf(map, 8)).toBe(-1);
  });
  it("target only when beyond rendered offset", () => {
    expect(renderTargetFor(map, 9, 2, 4)).toBe(3);
    expect(renderTargetFor(map, 5, 2, 4)).toBe(-1); // already rendered
    expect(renderTargetFor(map, 8, 2, 4)).toBe(-1); // unknown
    expect(renderTargetFor(map, -1, 0, 4)).toBe(-1);
    expect(renderTargetFor([], 0, 0, 0)).toBe(-1);
  });
});

describe("jumpTarget", () => {
  it("same view", () => expect(jumpTarget({ relative_path: "a/b/c.mp3" }, true, "a/b")).toEqual({ folder: "a/b", sameView: true }));
  it("other view / root file", () => {
    expect(jumpTarget({ relative_path: "a/b/c.mp3" }, false, "a/b").sameView).toBe(false);
    expect(jumpTarget({ relative_path: "c.mp3" }, true, "x")).toEqual({ folder: "", sameView: false });
    expect(jumpTarget({}, true, "")).toEqual({ folder: "", sameView: true });
  });
});

