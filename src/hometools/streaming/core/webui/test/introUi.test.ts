import { describe, it, expect, vi, afterEach } from "vitest";
import { initIntroUi, setCurrentIntro, updateSkipIntroBtn } from "../src/introUi";
import { installState, item } from "./helpers";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function setup(over: { enabled?: boolean; video?: boolean; relPath?: string } = {}) {
  const on: Record<string, (e?: unknown) => void> = {};
  const classes = new Set<string>();
  const label = { textContent: "" };
  const button = {
    hidden: true,
    classList: { toggle: (c: string, v: boolean) => (v ? classes.add(c) : classes.delete(c)) },
    querySelector: () => label,
    addEventListener: (e: string, f: (e?: unknown) => void) => (on[e] = f),
  };
  const player = { currentTime: 0, duration: 1000 };
  const toast = vi.fn();
  const fetchMock = vi.fn(() => Promise.resolve({}));
  vi.stubGlobal("fetch", fetchMock);
  const state = installState();
  initIntroUi({
    player: player as unknown as HTMLMediaElement,
    button: button as unknown as HTMLElement,
    enabled: over.enabled ?? true,
    isVideoMode: over.video ?? true,
    apiPath: "/api/video/intro",
    getProgressPath: () => over.relPath ?? "S/ep1.mp4",
    fmtTime: (s) => "t" + s,
    toast,
  });
  return { on, classes, label, button, player, toast, fetchMock, state };
}

describe("introUi", () => {
  it("shows skip button inside marker range and seeks on click", () => {
    const c = setup();
    setCurrentIntro(item("S/ep1.mp4", { intro_start: 0, intro_end: 60 }));
    c.player.currentTime = 10;
    updateSkipIntroBtn();
    expect(c.button.hidden).toBe(false);
    expect(c.label.textContent).toBe("Intro überspringen");
    c.on.click({ stopPropagation() {} });
    expect(c.player.currentTime).toBe(60);
    expect(c.toast).toHaveBeenCalledWith("Intro übersprungen");
  });

  it("hides button outside marker range", () => {
    const c = setup();
    setCurrentIntro(item("S/ep1.mp4", { intro_start: 0, intro_end: 60 }));
    c.player.currentTime = 10;
    updateSkipIntroBtn();
    c.player.currentTime = 90;
    updateSkipIntroBtn();
    expect(c.button.hidden).toBe(true);
  });

  it("set mode saves marker: patches items + POSTs", () => {
    const c = setup();
    const it1 = item("S/ep1.mp4", { season: 1, episode: 1 });
    c.state.allItems = [it1];
    c.state.filteredItems = [it1];
    setCurrentIntro(it1);
    c.player.currentTime = 42.04;
    updateSkipIntroBtn();
    expect(c.classes.has("set-mode")).toBe(true);
    c.on.click({ stopPropagation() {} });
    expect(it1.intro_end).toBe(42);
    expect(c.fetchMock).toHaveBeenCalledTimes(1);
    const body = JSON.parse((c.fetchMock.mock.calls[0] as unknown as [string, { body: string }])[1].body);
    expect(body).toEqual({ path: "S/ep1.mp4", start: 0, end: 42 });
    expect(c.button.hidden).toBe(true);
    expect(c.toast).toHaveBeenCalledWith("Intro-Ende gesetzt bei t42");
  });

  it("long-press in skip mode recalibrates end and swallows click", () => {
    vi.useFakeTimers();
    const c = setup();
    setCurrentIntro(item("S/ep1.mp4", { intro_start: 5, intro_end: 60 }));
    c.player.currentTime = 20;
    updateSkipIntroBtn();
    c.on.pointerdown();
    vi.advanceTimersByTime(700);
    expect(c.fetchMock).toHaveBeenCalledTimes(1);
    expect(c.toast).toHaveBeenCalledWith("Intro-Ende neu gesetzt bei t20");
    c.on.click({ stopPropagation() {} });
    expect(c.player.currentTime).toBe(20);
  });

  it("pointerup cancels long-press", () => {
    vi.useFakeTimers();
    const c = setup();
    setCurrentIntro(item("S/ep1.mp4", { intro_start: 5, intro_end: 60 }));
    c.player.currentTime = 20;
    updateSkipIntroBtn();
    c.on.pointerdown();
    c.on.pointerup();
    vi.advanceTimersByTime(700);
    expect(c.fetchMock).not.toHaveBeenCalled();
  });

  it("disabled: no listeners, no button changes", () => {
    const c = setup({ enabled: false });
    expect(c.on.click).toBeUndefined();
    setCurrentIntro(item("x", { intro_start: 0, intro_end: 60 }));
    c.player.currentTime = 10;
    updateSkipIntroBtn();
    expect(c.button.hidden).toBe(true);
  });

  it("no save without progress path", () => {
    const c = setup({ relPath: "" });
    setCurrentIntro(item("x", { season: 1 }));
    c.player.currentTime = 30;
    updateSkipIntroBtn();
    c.on.click({ stopPropagation() {} });
    expect(c.fetchMock).not.toHaveBeenCalled();
  });
});

