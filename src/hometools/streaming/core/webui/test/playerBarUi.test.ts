import { describe, it, expect, vi, afterEach } from "vitest";
import { initPlayerRatingEvents, initBarFullscreen } from "../src/playerBarUi";

afterEach(() => vi.unstubAllGlobals());

function node() {
  const handlers: Record<string, (e: unknown) => void> = {};
  const classes = new Set<string>();
  return {
    handlers,
    classes,
    hidden: true,
    dataset: {} as Record<string, string>,
    classList: {
      toggle: (c: string, on: boolean) => (on ? classes.add(c) : classes.delete(c)),
      remove: (c: string) => classes.delete(c),
    },
    addEventListener: (t: string, f: (e: unknown) => void) => (handlers[t] = f),
    querySelectorAll: () => [] as unknown[],
  };
}

describe("playerBarUi rating", () => {
  function setup(write: boolean, current: number) {
    const el = node();
    vi.stubGlobal("document", { getElementById: () => el });
    const setRating = vi.fn();
    initPlayerRatingEvents({ writeEnabled: write, currentRating: () => current, setRating });
    const click = (star: string) =>
      el.handlers.click({ target: { closest: () => ({ dataset: { star } }) } });
    return { click, setRating };
  }
  it("click sets stars", () => {
    const { click, setRating } = setup(true, 2);
    click("4");
    expect(setRating).toHaveBeenCalledWith(4);
  });
  it("click on current star clears", () => {
    const { click, setRating } = setup(true, 3);
    click("3");
    expect(setRating).toHaveBeenCalledWith(0);
  });
  it("ignored when write disabled", () => {
    const { click, setRating } = setup(false, 0);
    click("5");
    expect(setRating).not.toHaveBeenCalled();
  });
});

describe("playerBarUi fullscreen", () => {
  it("shows button for video when supported and requests fullscreen", () => {
    const btn = node();
    vi.stubGlobal("document", { getElementById: () => btn, fullscreenEnabled: true });
    const player = { requestFullscreen: vi.fn(() => Promise.resolve()) };
    initBarFullscreen(player as unknown as HTMLMediaElement, true);
    expect(btn.hidden).toBe(false);
    btn.handlers.click({});
    expect(player.requestFullscreen).toHaveBeenCalled();
  });
  it("stays hidden for audio", () => {
    const btn = node();
    vi.stubGlobal("document", { getElementById: () => btn, fullscreenEnabled: true });
    initBarFullscreen({} as HTMLMediaElement, false);
    expect(btn.hidden).toBe(true);
  });
});

