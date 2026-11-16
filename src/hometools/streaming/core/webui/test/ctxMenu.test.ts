import { describe, it, expect, vi, afterEach } from "vitest";
import { revealInExplorer, trackCtxMenuItems } from "../src/ctxMenu";

describe("trackCtxMenuItems", () => {
  const base = { icFolderOpen: "F", icTrash: "T", reveal: vi.fn(), removeFromPlaylist: vi.fn() };
  it("only reveal outside manual playlists", () => {
    const items = trackCtxMenuItems({ ...base, isManualPlaylist: false });
    expect(items.map((i) => i.label)).toEqual(["Im Explorer anzeigen"]);
  });
  it("adds danger remove in manual playlists", () => {
    const items = trackCtxMenuItems({ ...base, isManualPlaylist: true });
    expect(items).toHaveLength(2);
    expect(items[1].danger).toBe(true);
    items[1].onClick!();
    expect(base.removeFromPlaylist).toHaveBeenCalled();
  });
});

afterEach(() => vi.unstubAllGlobals());

function stubFetch(res: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(() => (res instanceof Error ? Promise.reject(res) : Promise.resolve(res))));
}

describe("revealInExplorer", () => {
  it("posts path and toasts opened", async () => {
    stubFetch({ ok: true, json: () => Promise.resolve({ revealed: true }) });
    const toast = vi.fn();
    await revealInExplorer("a/b.mp3", { apiPath: "/api/reveal", toast });
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/reveal");
    expect(JSON.parse(call[1].body)).toEqual({ path: "a/b.mp3" });
    expect(toast).toHaveBeenCalledWith("Explorer ge\u00f6ffnet");
  });
  it("toasts path when not revealed", async () => {
    stubFetch({ ok: true, json: () => Promise.resolve({ revealed: false, path: "/x" }) });
    const toast = vi.fn();
    await revealInExplorer("a", { apiPath: "/r", toast });
    expect(toast).toHaveBeenCalledWith("Pfad: /x");
  });
  it("toasts not found on HTTP error", async () => {
    stubFetch({ ok: false });
    const toast = vi.fn();
    await revealInExplorer("a", { apiPath: "/r", toast });
    expect(toast).toHaveBeenCalledWith("Pfad nicht gefunden");
  });
  it("toasts error on network failure", async () => {
    stubFetch(new Error("down"));
    const toast = vi.fn();
    await revealInExplorer("a", { apiPath: "/r", toast });
    expect(toast).toHaveBeenCalledWith("Fehler beim Anzeigen");
  });
});

