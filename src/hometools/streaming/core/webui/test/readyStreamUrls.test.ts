import { describe, it, expect } from "vitest";
import { readyStreamUrls } from "../src/offlineDownloads";

describe("readyStreamUrls", () => {
  it("keeps only ready entries with streamUrl", () => {
    const r = readyStreamUrls([
      { streamUrl: "/a", status: "ready" },
      { streamUrl: "/b", status: "downloading" },
      { status: "ready" },
      { streamUrl: "", status: "ready" },
    ]);
    expect(r).toEqual({ "/a": true });
  });
  it("tolerates empty/undefined", () => {
    expect(readyStreamUrls([])).toEqual({});
    expect(readyStreamUrls(undefined as never)).toEqual({});
  });
});

