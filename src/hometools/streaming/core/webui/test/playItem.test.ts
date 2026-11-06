import { describe, it, expect, vi, beforeEach } from "vitest";
import { installState } from "./helpers";
import { playItem } from "../src/playItem";
import type { PlayItemHooks } from "../src/playItem";
import { getProgressPath } from "../src/progress";

function mk(over: Partial<PlayItemHooks> = {}) {
  const calls: string[] = [];
  const rec =
    (name: string, ret?: unknown) =>
    (..._a: unknown[]) => {
      calls.push(name);
      return ret as never;
    };
  const h = {
    player: { volume: 0.3 },
    setCurrentIndex: vi.fn(rec("idx")),
    setCurrentStreamUrl: vi.fn(rec("url")),
    setCurrentDuration: vi.fn(rec("dur")),
    setCurrentIntro: vi.fn(rec("intro")),
    beginPlayback: vi.fn(rec("begin")),
    playOfflineOrStream: vi.fn((u: string) => Promise.resolve({ url: u, offline: false, fallbackUrl: u })),
    showNowPlaying: vi.fn(rec("now")),
    markActive: vi.fn(rec("mark")),
    updateMediaSession: vi.fn(rec("session")),
    renderPlayerRating: vi.fn(rec("rating")),
    updatePlayerBarActions: vi.fn(rec("actions")),
    refreshMetadata: vi.fn(rec("meta")),
    refreshLyricsIfOpen: vi.fn(rec("lyrics")),
    saveProgressNow: vi.fn(rec("save")),
    saveLastPlayedLocal: vi.fn(rec("local")),
    autoResume: true,
    loadAndSeekProgress: vi.fn(rec("seek")),
    loadSpriteData: vi.fn(rec("sprite")),
    routerUpdate: vi.fn(rec("router")),
    ...over,
  } as PlayItemHooks & { calls?: string[] };
  return { h, calls };
}
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("playItem", () => {
  beforeEach(() => installState());
  it("sets state, resets volume, tracks progress path", async () => {
    const { h } = mk();
    const t = { relative_path: "a.mp3", stream_url: "/s/a", duration: 120, rating: 4 };
    playItem(t, 3, h);
    expect(h.setCurrentIndex).toHaveBeenCalledWith(3);
    expect(h.setCurrentStreamUrl).toHaveBeenCalledWith("/s/a");
    expect(h.setCurrentDuration).toHaveBeenCalledWith(120);
    expect(h.setCurrentIntro).toHaveBeenCalledWith(t);
    expect(h.player.volume).toBe(1);
    expect(getProgressPath()).toBe("a.mp3");
    expect(h.saveLastPlayedLocal).toHaveBeenCalledWith("a.mp3", 0);
    expect(h.loadAndSeekProgress).toHaveBeenCalledWith("a.mp3");
    expect(h.renderPlayerRating).toHaveBeenCalledWith(4);
    expect(h.loadSpriteData).toHaveBeenCalledWith("a.mp3");
    expect(h.routerUpdate).toHaveBeenCalled();
    await flush();
    expect(h.beginPlayback).toHaveBeenCalledWith({ url: "/s/a", offline: false, fallbackUrl: "/s/a" });
  });
  it("non-number index -> -1; no auto resume when disabled; defaults for missing fields", () => {
    const { h } = mk({ autoResume: false });
    playItem({}, undefined, h);
    expect(h.setCurrentIndex).toHaveBeenCalledWith(-1);
    expect(h.setCurrentStreamUrl).toHaveBeenCalledWith("");
    expect(h.setCurrentDuration).toHaveBeenCalledWith(0);
    expect(h.renderPlayerRating).toHaveBeenCalledWith(0);
    expect(h.loadAndSeekProgress).not.toHaveBeenCalled();
  });
  it("flushes outgoing progress before switching path", () => {
    let pathAtSave = "?";
    const { h } = mk({
      saveProgressNow: vi.fn(() => {
        pathAtSave = getProgressPath();
      }),
    });
    playItem({ relative_path: "old" }, 0, h);
    playItem({ relative_path: "new" }, 1, h);
    expect(pathAtSave).toBe("old");
    expect(getProgressPath()).toBe("new");
  });
  it("falls back to plain stream when offline resolution rejects or throws", async () => {
    const { h } = mk({ playOfflineOrStream: vi.fn(() => Promise.reject(new Error("x"))) });
    playItem({ relative_path: "a", stream_url: "/s" }, 0, h);
    await flush();
    expect(h.beginPlayback).toHaveBeenCalledWith({ url: "/s", offline: false, fallbackUrl: "/s" });
    const m2 = mk({
      playOfflineOrStream: vi.fn(() => {
        throw new Error("sync");
      }),
    });
    playItem({ relative_path: "a", stream_url: "/s" }, 0, m2.h);
    await flush();
    expect(m2.h.beginPlayback).toHaveBeenCalledTimes(1);
  });
});

