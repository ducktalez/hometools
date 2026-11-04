import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { installState, item } from "./helpers";
import { initModeButtons, cycleShuffle, cycleRepeat, activateWeightedShuffle } from "../src/modeButtons";
import type { ModeButtonsHooks, ModeBtn } from "../src/modeButtons";

let store: Record<string, string>;
beforeEach(() => {
  store = {};
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => (store[k] = v),
  });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function btn(): ModeBtn & { classes: Set<string>; fire(e: string): void } {
  const classes = new Set<string>();
  const l: Record<string, (e: Event) => void> = {};
  return {
    classes,
    title: "",
    innerHTML: "",
    classList: { toggle: (c: string, on: boolean) => (on ? classes.add(c) : classes.delete(c)) },
    addEventListener: (t: string, f: (e: Event) => void) => (l[t] = f),
    fire: (e: string) => l[e]({ preventDefault() {} } as unknown as Event),
  };
}
function hooks(over: Partial<ModeButtonsHooks> = {}) {
  const bs = btn();
  const br = btn();
  const h: ModeButtonsHooks = {
    btnShuffle: bs,
    btnRepeat: br,
    shuffleEnabled: true,
    repeatEnabled: true,
    icRepeat: "R",
    icRepeatOne: "R1",
    showToast: vi.fn(),
    ...over,
  };
  return { h, bs, br };
}
const items = [item("a"), item("b"), item("c")];

describe("modeButtons", () => {
  it("cycleShuffle: off -> normal, persisted, button active", () => {
    const s = installState({ shuffleMode: false, filteredItems: items, currentIndex: 1 });
    const { h, bs } = hooks();
    cycleShuffle(h);
    expect(s.shuffleMode).toBe("normal");
    expect(store["ht-shuffle-mode"]).toBe("normal");
    expect(bs.classes.has("shuffle-active")).toBe(true);
    expect(s.shuffleQueue.length).toBeGreaterThan(0);
  });
  it("activateWeightedShuffle sets weighted + toast", () => {
    const s = installState({ shuffleMode: false, filteredItems: items, currentIndex: -1 });
    const { h } = hooks();
    activateWeightedShuffle(h);
    expect(s.shuffleMode).toBe("weighted");
    expect(store["ht-shuffle-mode"]).toBe("weighted");
    expect(h.showToast).toHaveBeenCalled();
  });
  it("cycleRepeat: off -> all -> one with icon", () => {
    const s = installState({ repeatMode: false });
    const { h, br } = hooks();
    cycleRepeat(h);
    expect(s.repeatMode).toBe("all");
    expect(br.innerHTML).toBe("R");
    cycleRepeat(h);
    expect(s.repeatMode).toBe("one");
    expect(br.innerHTML).toBe("R1");
    expect(store["ht-repeat-mode"]).toBe("one");
  });
  it("init restores saved modes", () => {
    store["ht-shuffle-mode"] = "weighted";
    store["ht-repeat-mode"] = "one";
    const s = installState({});
    const { h, bs, br } = hooks();
    initModeButtons(h);
    expect(s.shuffleMode).toBe("weighted");
    expect(s.repeatMode).toBe("one");
    expect(bs.classes.has("shuffle-weighted")).toBe(true);
    expect(br.classes.has("repeat-one")).toBe(true);
  });
  it("disabled features not restored", () => {
    store["ht-shuffle-mode"] = "normal";
    const s = installState({ shuffleMode: false });
    initModeButtons(hooks({ shuffleEnabled: false, repeatEnabled: false }).h);
    expect(s.shuffleMode).toBe(false);
  });
  it("click cycles; long-press (600ms) activates weighted and swallows click", () => {
    vi.useFakeTimers();
    const s = installState({ shuffleMode: false, filteredItems: items, currentIndex: 0 });
    const { h, bs } = hooks();
    initModeButtons(h);
    bs.fire("click");
    expect(s.shuffleMode).toBe("normal");
    bs.fire("mousedown");
    vi.advanceTimersByTime(600);
    expect(s.shuffleMode).toBe("weighted");
    bs.fire("click");
    expect(s.shuffleMode).toBe("weighted");
    bs.fire("mousedown");
    bs.fire("mouseup");
    vi.advanceTimersByTime(1000);
    expect(s.shuffleMode).toBe("weighted");
  });
});

