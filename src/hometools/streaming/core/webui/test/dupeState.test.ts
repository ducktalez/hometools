import { describe, it, expect, beforeEach } from "vitest";
import { ensureDupeIndex, currentDupeIndex, dupeCount, invalidateDupeIndex } from "../src/dupeState";

const items = [
  { relative_path: "a/x.mp3", title: "Song", artist: "Art", duration: 100 },
  { relative_path: "b/x.mp3", title: "Song", artist: "Art", duration: 100 },
  { relative_path: "c/y.mp3", title: "Other", artist: "Art", duration: 50 },
] as never;

beforeEach(() => invalidateDupeIndex());

describe("dupeState", () => {
  it("is null until built", () => {
    expect(currentDupeIndex()).toBeNull();
  });
  it("builds once and caches", () => {
    const a = ensureDupeIndex(items);
    expect(ensureDupeIndex([] as never)).toBe(a);
    expect(currentDupeIndex()).toBe(a);
  });
  it("counts groups", () => {
    expect(dupeCount(items)).toBe(1);
  });
  it("invalidate resets", () => {
    ensureDupeIndex(items);
    invalidateDupeIndex();
    expect(currentDupeIndex()).toBeNull();
  });
});

