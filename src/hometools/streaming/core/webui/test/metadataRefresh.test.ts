import { describe, it, expect, vi, afterEach } from "vitest";
import { refreshMetadata, metadataUrl } from "../src/metadataRefresh";
import { setProgressPath } from "../src/progress";

afterEach(() => vi.unstubAllGlobals());

function hooks() {
  return {
    apiPath: "/api/audio/items",
    setTitle: vi.fn(),
    setArtist: vi.fn(),
    renderPlayerRating: vi.fn(),
    updateMediaSession: vi.fn(),
    applyFilter: vi.fn(),
    markActive: vi.fn(),
  };
}
const ok = (meta: unknown) => vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(meta) }));

describe("metadataUrl", () => {
  it("swaps last segment, encodes path", () => {
    expect(metadataUrl("/api/audio/items", "a b/c.mp3")).toBe("/api/audio/metadata?path=a%20b%2Fc.mp3");
  });
});

describe("refreshMetadata", () => {
  it("patches title/artist/rating and refreshes UI", async () => {
    setProgressPath("a.mp3");
    vi.stubGlobal("fetch", ok({ title: "T2", artist: "A2", rating: 4 }));
    const t = { relative_path: "a.mp3", title: "T", artist: "A", rating: 0 };
    const h = hooks();
    await refreshMetadata(t, h);
    expect(t).toMatchObject({ title: "T2", artist: "A2", rating: 4 });
    expect(h.setTitle).toHaveBeenCalledWith("T2");
    expect(h.setArtist).toHaveBeenCalledWith("A2");
    expect(h.renderPlayerRating).toHaveBeenCalledWith(4);
    expect(h.updateMediaSession).toHaveBeenCalledWith(t);
    expect(h.applyFilter).toHaveBeenCalled();
    expect(h.markActive).toHaveBeenCalled();
  });
  it("rating only: no title/list refresh", async () => {
    setProgressPath("a.mp3");
    vi.stubGlobal("fetch", ok({ title: "T", rating: 3 }));
    const h = hooks();
    await refreshMetadata({ relative_path: "a.mp3", title: "T" }, h);
    expect(h.renderPlayerRating).toHaveBeenCalledWith(3);
    expect(h.applyFilter).not.toHaveBeenCalled();
  });
  it("drops stale response when another track is playing", async () => {
    setProgressPath("other.mp3");
    vi.stubGlobal("fetch", ok({ title: "X", rating: 5 }));
    const t = { relative_path: "a.mp3", title: "T" };
    const h = hooks();
    await refreshMetadata(t, h);
    expect(t.title).toBe("T");
    expect(h.setTitle).not.toHaveBeenCalled();
    expect(h.renderPlayerRating).not.toHaveBeenCalled();
  });
  it("never throws on http error / network failure / sync throw", async () => {
    const h = hooks();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false })));
    await refreshMetadata({ relative_path: "a" }, h);
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("net"))));
    await refreshMetadata({ relative_path: "a" }, h);
    vi.stubGlobal("fetch", () => {
      throw new Error("x");
    });
    await refreshMetadata({ relative_path: "a" }, h);
    expect(h.setTitle).not.toHaveBeenCalled();
  });
});

