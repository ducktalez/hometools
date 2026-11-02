import { describe, it, expect, vi, afterEach } from "vitest";
import { initPip, isPipActive, requestPip, exitPip } from "../src/pip";

afterEach(() => vi.unstubAllGlobals());

function setup(opts: { touch?: boolean; ios?: boolean; supported?: boolean } = {}) {
  const listeners: Record<string, () => void> = {};
  const classes = new Set<string>();
  const button = {
    hidden: true,
    classList: {
      toggle: (c: string, on: boolean) => (on ? classes.add(c) : classes.delete(c)),
    },
    addEventListener: (e: string, f: () => void) => (listeners["btn:" + e] = f),
  };
  const player = {
    requestPictureInPicture: vi.fn(() => Promise.resolve()),
    setAttribute: vi.fn(),
    play: vi.fn(() => Promise.resolve()),
    addEventListener: (e: string, f: () => void) => (listeners[e] = f),
  };
  const doc = {
    pictureInPictureEnabled: opts.supported ?? true,
    pictureInPictureElement: {},
    hidden: false,
    exitPictureInPicture: vi.fn(() => Promise.resolve()),
  };
  vi.stubGlobal("document", doc);
  vi.stubGlobal("navigator", { maxTouchPoints: opts.touch ? 5 : 0 });
  vi.stubGlobal("window", { matchMedia: () => ({ matches: !!opts.touch }) });
  let was = true;
  initPip({
    player: player as unknown as HTMLVideoElement,
    button: button as unknown as HTMLElement,
    isVideoPlayer: true,
    isIOS: !!opts.ios,
    wasPlaying: () => was,
  });
  return { listeners, classes, button, player, doc };
}

describe("pip", () => {
  it("shows button on desktop when supported", () => {
    const { button, player } = setup();
    expect(button.hidden).toBe(false);
    expect(player.setAttribute).toHaveBeenCalledWith("autopictureinpicture", "");
  });
  it("hides button on touch devices", () => {
    expect(setup({ touch: true }).button.hidden).toBe(true);
  });
  it("hides button when unsupported", () => {
    expect(setup({ supported: false }).button.hidden).toBe(true);
  });
  it("request sets active + class, exit clears", async () => {
    const { classes, doc } = setup();
    await requestPip();
    expect(isPipActive()).toBe(true);
    expect(classes.has("active")).toBe(true);
    exitPip();
    expect(doc.exitPictureInPicture).toHaveBeenCalled();
    expect(isPipActive()).toBe(false);
    expect(classes.has("active")).toBe(false);
  });
  it("leave event resumes inline when wasPlaying", () => {
    const { listeners, player } = setup();
    listeners["enterpictureinpicture"]();
    expect(isPipActive()).toBe(true);
    listeners["leavepictureinpicture"]();
    expect(isPipActive()).toBe(false);
    expect(player.play).toHaveBeenCalled();
  });
});

