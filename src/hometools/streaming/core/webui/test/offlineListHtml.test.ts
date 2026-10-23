import { describe, it, expect } from "vitest";
import { offlineDownloadListHtml } from "../src/offlineDownloads";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
const fmt = (n: number) => n + "B";

describe("offlineDownloadListHtml", () => {
  it("empty", () => {
    expect(offlineDownloadListHtml([], esc, fmt, "PH")).toContain("empty-downloads");
  });
  it("ready item with fallbacks", () => {
    const h = offlineDownloadListHtml([{ streamUrl: "/s?a=<", status: "ready", size: 5, relativePath: "a/b" }], esc, fmt, "PH");
    expect(h).toContain('data-stream-url="/s?a=&lt;"');
    expect(h).toContain('src="PH"');
    expect(h).toContain("Unbenannter Download");
    expect(h).toContain('offline-download-sub">a/b<');
    expect(h).toContain("Offline bereit \u00b7 5B \u00b7 Unbekannt");
  });
  it("unknown status, artist wins", () => {
    const h = offlineDownloadListHtml([{ streamUrl: "u", artist: "X", relativePath: "r", thumbnailUrl: "/t" }], esc, fmt, "PH");
    expect(h).toContain("unbekannt");
    expect(h).toContain('sub">X<');
    expect(h).toContain('src="/t"');
  });
});

