import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import { swipeTarget, isBackSwipe, initSwipeGestures } from "../src/swipe";

afterEach(() => vi.unstubAllGlobals());

const el = (over: Record<string, unknown>, parent: unknown = null) => ({
  tagName: "DIV",
  classList: { contains: () => false },
  parentElement: parent,
  ...over,
});

describe("swipeTarget", () => {
  it("allows plain element", () => expect(swipeTarget(el({}) as never)).toBe(true));
  it("blocks range input and canvas", () => {
    expect(swipeTarget(el({ tagName: "INPUT", type: "range" }) as never)).toBe(false);
    expect(swipeTarget(el({ tagName: "CANVAS" }) as never)).toBe(false);
  });
  it("blocks via ancestor panel class", () => {
    const panel = el({ classList: { contains: (c: string) => c === "queue-panel" } });
    expect(swipeTarget(el({}, panel) as never)).toBe(false);
  });
});

describe("isBackSwipe", () => {
  it("accepts quick, flat, long right swipe", () => expect(isBackSwipe(80, 10, 200)).toBe(true));
  it("rejects left, slow, short, steep", () => {
    expect(isBackSwipe(-80, 0, 100)).toBe(false);
    expect(isBackSwipe(80, 0, 500)).toBe(false);
    expect(isBackSwipe(30, 0, 100)).toBe(false);
    expect(isBackSwipe(80, 90, 100)).toBe(false);
  });
});

describe("initSwipeGestures", () => {
  it("goBack only when in playlist/folder; installs once", () => {
    const l: Record<string, (e: unknown) => void> = {};
    const add = vi.fn((ev: string, f: (e: unknown) => void) => (l[ev] = f));
    vi.stubGlobal("document", { addEventListener: add });
    const s = installState({ currentPath: "a" });
    const goBack = vi.fn();
    initSwipeGestures({ goBack });
    initSwipeGestures({ goBack });
    expect(add).toHaveBeenCalledTimes(2);
    const swipe = () => {
      l.touchstart({ target: el({}), touches: [{ clientX: 0, clientY: 0 }] });
      l.touchend({ changedTouches: [{ clientX: 100, clientY: 0 }] });
    };
    swipe();
    expect(goBack).toHaveBeenCalledTimes(1);
    s.currentPath = "";
    swipe();
    expect(goBack).toHaveBeenCalledTimes(1);
    s.inPlaylist = true;
    swipe();
    expect(goBack).toHaveBeenCalledTimes(2);
  });
});

