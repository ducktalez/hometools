import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { findResumeLocal, findResumeRecent } from "../src/resume";

const items = [item("a", { title: "A" }), item("b", { title: "" }), item("c", { title: "C" })];

describe("findResumeLocal", () => {
  it("hit with position + title", () => {
    expect(findResumeLocal(items, { path: "c", position_seconds: 12 }, -1)).toEqual({ idx: 2, pos: 12, label: "C" });
  });
  it("label falls back to path", () => {
    expect(findResumeLocal(items, { path: "b" }, -1)).toEqual({ idx: 1, pos: 0, label: "b" });
  });
  it("null when selected, unknown, or empty", () => {
    expect(findResumeLocal(items, { path: "a" }, 0)).toBeNull();
    expect(findResumeLocal(items, { path: "zz" }, -1)).toBeNull();
    expect(findResumeLocal(items, null, -1)).toBeNull();
  });
});

describe("findResumeRecent", () => {
  it("first entry in list with pos >= 5", () => {
    const e = [
      { relative_path: "zz", position_seconds: 50 },
      { relative_path: "a", position_seconds: 2 },
      { relative_path: "c", position_seconds: 30 },
    ];
    expect(findResumeRecent(items, e, -1)).toEqual({ idx: 2, pos: 30, label: "C" });
  });
  it("null when none qualify or already selected", () => {
    expect(findResumeRecent(items, [{ relative_path: "a", position_seconds: 1 }], -1)).toBeNull();
    expect(findResumeRecent(items, [{ relative_path: "a", position_seconds: 9 }], 1)).toBeNull();
    expect(findResumeRecent(items, [], -1)).toBeNull();
  });
});

