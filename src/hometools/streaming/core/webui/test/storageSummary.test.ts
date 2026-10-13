import { describe, it, expect } from "vitest";
import { storageSummaryView, type OfflineStorageInfo } from "../src/offlineDownloads";
const fmt = (n: number) => n + "B";
const base: OfflineStorageInfo = {
  downloads: [],
  appUsage: 0,
  softLimit: 100,
  browserUsage: null,
  browserQuota: null,
  persistent: null,
};
describe("storageSummaryView", () => {
  it("empty", () => {
    const v = storageSummaryView(base, fmt);
    expect(v.summary).toBe("Noch keine Offline-Downloads.");
    expect(v.detail).toBe("App-Budget 0B / 100B");
    expect(v.pill).toBe("Downloaded (0)");
    expect(v.hasDownloads).toBe(false);
    expect(v.warn).toBe(false);
  });
  it("plural, browser + persistence parts", () => {
    const v = storageSummaryView(
      { ...base, downloads: [{}, {}] as never, appUsage: 10, browserUsage: 5, browserQuota: 50, persistent: true },
      fmt,
    );
    expect(v.summary).toContain("2 Offline-Downloads");
    expect(v.detail).toBe("App-Budget 10B / 100B \u00b7 Browser 5B / 50B \u00b7 Persistent aktiv");
  });
  it("singular + non persistent", () => {
    const v = storageSummaryView({ ...base, downloads: [{}] as never, persistent: false }, fmt);
    expect(v.summary).toContain("1 Offline-Download ");
    expect(v.detail).toContain("Nicht persistent");
  });
  it("warn at 80% app or browser quota", () => {
    expect(storageSummaryView({ ...base, appUsage: 80 }, fmt).warn).toBe(true);
    expect(storageSummaryView({ ...base, browserUsage: 40, browserQuota: 50 }, fmt).warn).toBe(true);
  });
});
