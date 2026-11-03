import { describe, it, expect, vi, afterEach } from "vitest";
import {
  setProgressPath,
  getProgressPath,
  cancelProgressTimer,
  saveProgressNow,
  saveProgressDebounced,
  clearProgressFor,
  loadAndSeekProgress,
} from "../src/progress";
import type { ProgressHooks } from "../src/progress";
afterEach(() => {
  cancelProgressTimer();
  setProgressPath("");
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
function hooks(pos = 50, dur = 600): ProgressHooks & { listeners: Record<string, () => void> } {
  const listeners: Record<string, () => void> = {};
  return {
    player: {
      currentTime: pos,
      duration: dur,
      addEventListener: (e: string, f: () => void) => (listeners[e] = f),
    } as unknown as HTMLMediaElement,
    apiPath: "/api/video/items",
    saveLastPlayedLocal: vi.fn(),
    showToast: vi.fn(),
    fmtTime: (s: number) => "t" + s,
    listeners,
  };
}
describe("progress path state", () => {
  it("get/set", () => {
    setProgressPath("a.mp4");
    expect(getProgressPath()).toBe("a.mp4");
    setProgressPath("");
    expect(getProgressPath()).toBe("");
  });
});
describe("saveProgressNow", () => {
  it("no path -> nothing", () => {
    const h = hooks();
    saveProgressNow(h);
    expect(h.saveLastPlayedLocal).not.toHaveBeenCalled();
  });
  it("saves local + beacon", () => {
    const beacon = vi.fn(() => true);
    vi.stubGlobal("navigator", { sendBeacon: beacon });
    vi.stubGlobal("Blob", class {});
    setProgressPath("a.mp4");
    const h = hooks();
    saveProgressNow(h);
    expect(h.saveLastPlayedLocal).toHaveBeenCalledWith("a.mp4", 50);
    expect(beacon).toHaveBeenCalledWith("/api/video/progress", expect.anything());
  });
  it("falls back to fetch when beacon refuses", () => {
    const f = vi.fn(() => Promise.resolve({}));
    vi.stubGlobal("fetch", f);
    vi.stubGlobal("navigator", { sendBeacon: () => false });
    vi.stubGlobal("Blob", class {});
    setProgressPath("a.mp4");
    saveProgressNow(hooks());
    expect(f).toHaveBeenCalled();
  });
  it("first 5s: local only", () => {
    const f = vi.fn(() => Promise.resolve({}));
    vi.stubGlobal("fetch", f);
    vi.stubGlobal("navigator", {});
    setProgressPath("a.mp4");
    const h = hooks(2, 600);
    saveProgressNow(h);
    expect(h.saveLastPlayedLocal).toHaveBeenCalled();
    expect(f).not.toHaveBeenCalled();
  });
  it("debounced fires after 5s, cancel stops it", () => {
    vi.useFakeTimers();
    vi.stubGlobal("navigator", {});
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({})));
    setProgressPath("a.mp4");
    const h = hooks();
    saveProgressDebounced(h);
    vi.advanceTimersByTime(4999);
    expect(h.saveLastPlayedLocal).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(h.saveLastPlayedLocal).toHaveBeenCalledTimes(1);
    saveProgressDebounced(h);
    cancelProgressTimer();
    vi.advanceTimersByTime(10000);
    expect(h.saveLastPlayedLocal).toHaveBeenCalledTimes(1);
  });
});
describe("clearProgressFor / loadAndSeekProgress", () => {
  it("clear posts zeros; empty rp no-op", () => {
    const f = vi.fn(() => Promise.resolve({}));
    vi.stubGlobal("fetch", f);
    clearProgressFor("", hooks());
    expect(f).not.toHaveBeenCalled();
    clearProgressFor("a.mp4", hooks());
    const body = JSON.parse((f.mock.calls[0] as unknown as [string, { body: string }])[1].body);
    expect(body).toEqual({ relative_path: "a.mp4", position_seconds: 0, duration: 0 });
  });
  it("seeks when duration known", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ position_seconds: 120 }] }) }))
    );
    const h = hooks(0, 600);
    loadAndSeekProgress("a.mp4", h);
    await new Promise((r) => setTimeout(r, 0));
    expect(h.player.currentTime).toBe(120);
    expect(h.showToast).toHaveBeenCalledWith("Fortfahren bei t120", 3000);
  });
  it("waits for loadedmetadata when duration unknown; ignores <5s", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ position_seconds: 60 }] }) }))
    );
    const h = hooks(0, NaN);
    loadAndSeekProgress("a.mp4", h);
    await new Promise((r) => setTimeout(r, 0));
    expect(h.listeners.loadedmetadata).toBeTypeOf("function");
    (h.player as unknown as { duration: number }).duration = 300;
    h.listeners.loadedmetadata();
    expect(h.player.currentTime).toBe(60);
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ position_seconds: 3 }] }) }))
    );
    const h2 = hooks(0, 600);
    loadAndSeekProgress("b.mp4", h2);
    await new Promise((r) => setTimeout(r, 0));
    expect(h2.player.currentTime).toBe(0);
  });
});
