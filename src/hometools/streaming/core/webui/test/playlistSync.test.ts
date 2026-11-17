import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { installState } from "./helpers";
import {
  loadUserPlaylists,
  snapshotPlaylists,
  restorePlaylists,
  startPlaylistSync,
  stopPlaylistSync,
  bindPlaylistSync,
} from "../src/playlistSync";

describe("bindPlaylistSync", () => {
  async function run(over: { inPlaylist: boolean; currentPath: string }) {
    installState({ ...over, playlistRevision: 1 });
    mockFetch({ "/pl/version": { revision: 2 }, "/pl": { items: [], revision: 2 } });
    const show = vi.fn();
    bindPlaylistSync(opts, show).start();
    await vi.advanceTimersByTimeAsync(1000);
    return show;
  }
  it("re-renders on root folder view", async () => {
    expect(await run({ inPlaylist: false, currentPath: "" })).toHaveBeenCalledTimes(1);
  });
  it("skips re-render inside a folder or playlist", async () => {
    expect(await run({ inPlaylist: false, currentPath: "a" })).not.toHaveBeenCalled();
    stopPlaylistSync();
    expect(await run({ inPlaylist: true, currentPath: "" })).not.toHaveBeenCalled();
  });
});

const opts = { enabled: true, apiPath: "/pl", versionPath: "/pl/version", intervalMs: 1000 };

function mockFetch(map: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => Promise.resolve({ json: () => Promise.resolve(map[url]) })),
  );
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("document", {
    hidden: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  });
});
afterEach(() => {
  stopPlaylistSync();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("playlistSync", () => {
  it("load writes items + revision into htState", async () => {
    const s = installState();
    mockFetch({ "/pl": { items: [{ id: "a" }], revision: 4 } });
    expect(await loadUserPlaylists(opts)).toEqual([{ id: "a" }]);
    expect(s.userPlaylists).toEqual([{ id: "a" }]);
    expect(s.playlistRevision).toBe(4);
  });
  it("load: disabled -> [] without fetch; failure -> []", async () => {
    installState();
    mockFetch({});
    expect(await loadUserPlaylists({ ...opts, enabled: false })).toEqual([]);
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("x"))));
    expect(await loadUserPlaylists(opts)).toEqual([]);
  });
  it("snapshot is a deep copy; restore reassigns", () => {
    const s = installState({ userPlaylists: [{ id: "a", items: [1] }] });
    const snap = snapshotPlaylists() as { items: number[] }[];
    (s.userPlaylists[0] as { items: number[] }).items.push(2);
    expect(snap[0].items).toEqual([1]);
    restorePlaylists(snap);
    expect(s.userPlaylists).toBe(snap);
  });
  it("poll: newer revision triggers reload + callback", async () => {
    installState({ playlistRevision: 1 });
    mockFetch({ "/pl/version": { revision: 2 }, "/pl": { items: [], revision: 2 } });
    const cb = vi.fn();
    startPlaylistSync({ ...opts, onRemoteUpdate: cb });
    await vi.advanceTimersByTimeAsync(1100);
    expect(cb).toHaveBeenCalledTimes(1);
  });
  it("poll: same revision does nothing", async () => {
    installState({ playlistRevision: 2 });
    mockFetch({ "/pl/version": { revision: 2 } });
    const cb = vi.fn();
    startPlaylistSync({ ...opts, onRemoteUpdate: cb });
    await vi.advanceTimersByTimeAsync(1100);
    expect(cb).not.toHaveBeenCalled();
  });
  it("stop cancels polling and detaches listener", async () => {
    installState();
    mockFetch({ "/pl/version": { revision: 9 } });
    startPlaylistSync(opts);
    stopPlaylistSync();
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch).not.toHaveBeenCalled();
    expect(document.removeEventListener).toHaveBeenCalled();
  });
});

