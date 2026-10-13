import { describe, it, expect } from "vitest";
import { item } from "./helpers";
import { findItemByStreamUrl } from "../src/catalogQuery";
import { progressApiBase, buildProgressPayload } from "../src/progress";

describe("findItemByStreamUrl", () => {
  const a = item("a.mp3", { stream_url: "/s/a" });
  const b = item("b.mp3", { stream_url: "/s/b" });

  it("prefers filteredItems with index", () => {
    expect(findItemByStreamUrl("/s/b", [a, b], [b])).toEqual({ item: b, index: 1 });
  });
  it("falls back to allItems with index -1", () => {
    expect(findItemByStreamUrl("/s/b", [a], [a, b])).toEqual({ item: b, index: -1 });
  });
  it("null when missing", () => {
    expect(findItemByStreamUrl("/s/x", [a], [a, b])).toBeNull();
  });
});

describe("progress", () => {
  it("progressApiBase swaps last segment", () => {
    expect(progressApiBase("/api/video/items")).toBe("/api/video/progress");
  });
  it("payload null for empty path / non-finite / edges", () => {
    expect(buildProgressPayload("", 50, 100)).toBeNull();
    expect(buildProgressPayload("a", NaN, 100)).toBeNull();
    expect(buildProgressPayload("a", 3, 100)).toBeNull();
    expect(buildProgressPayload("a", 97, 100)).toBeNull();
  });
  it("payload JSON in range", () => {
    expect(JSON.parse(buildProgressPayload("a", 50, 100) as string)).toEqual({
      relative_path: "a",
      position_seconds: 50,
      duration: 100,
    });
  });
});

