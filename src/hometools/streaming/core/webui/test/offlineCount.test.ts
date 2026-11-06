import { describe, it, expect, vi, afterEach } from "vitest";
vi.mock("../src/offlineDb", () => ({ getAllDownloads: vi.fn() }));
import { getAllDownloads } from "../src/offlineDb";
import { updateOfflineFolderCount } from "../src/offlineCount";
afterEach(() => vi.unstubAllGlobals());
describe("updateOfflineFolderCount", () => {
  it("counts only ready downloads into badge + pill", async () => {
    vi.mocked(getAllDownloads).mockResolvedValue([
      { id: 1, streamUrl: "a", status: "ready" },
      { id: 2, streamUrl: "b", status: "downloading" },
      { id: 3, streamUrl: "c", status: "ready" },
    ]);
    const el = { textContent: "" };
    vi.stubGlobal("document", { getElementById: () => el });
    const toggle = vi.fn();
    const pill = { textContent: "", classList: { toggle } };
    await updateOfflineFolderCount(pill);
    expect(el.textContent).toBe("2");
    expect(pill.textContent).toBe("Downloaded (2)");
    expect(toggle).toHaveBeenCalledWith("has-downloads", true);
  });
  it("zero ready: has-downloads off; null pill + missing badge tolerated", async () => {
    vi.mocked(getAllDownloads).mockResolvedValue([]);
    vi.stubGlobal("document", { getElementById: () => null });
    const toggle = vi.fn();
    await updateOfflineFolderCount({ textContent: "", classList: { toggle } });
    expect(toggle).toHaveBeenCalledWith("has-downloads", false);
    await expect(updateOfflineFolderCount(null)).resolves.toBeUndefined();
  });
  it("never rejects when the DB read fails", async () => {
    vi.mocked(getAllDownloads).mockRejectedValue(new Error("db"));
    await expect(updateOfflineFolderCount(null)).resolves.toBeUndefined();
  });
});