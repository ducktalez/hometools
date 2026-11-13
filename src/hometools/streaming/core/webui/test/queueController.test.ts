import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { initQueueController, QUEUE_HEIGHT_KEY } from "../src/queueController";

type Item = { relative_path: string; title: string };
let state: { userQueue: Item[]; filteredItems: Item[] };

beforeEach(() => {
  state = { userQueue: [], filteredItems: [] };
  vi.stubGlobal("window", { htState: state, addEventListener: vi.fn() });
  vi.stubGlobal("localStorage", { getItem: vi.fn(() => null), setItem: vi.fn() });
  vi.stubGlobal("document", {
    getElementById: () => null,
    querySelectorAll: () => [],
    querySelector: () => null,
  });
});
afterEach(() => vi.unstubAllGlobals());

function ctl() {
  const toast = vi.fn();
  const playItem = vi.fn();
  const c = initQueueController({
    itemNoun: "audio",
    filePlaceholder: "",
    icRemove: "",
    esc: (s) => String(s),
    toast,
    playItem,
    lyricsOpen: () => false,
    closeLyrics: vi.fn(),
  });
  return { c, toast, playItem };
}

describe("queueController", () => {
  it("add, duplicate, remove, clear", () => {
    const { c, toast } = ctl();
    c.add({ relative_path: "a.mp3", title: "A" } as never);
    expect(state.userQueue).toHaveLength(1);
    c.add({ relative_path: "a.mp3", title: "A" } as never);
    expect(toast).toHaveBeenCalledWith("Bereits in der Warteschlange");
    c.remove(0);
    expect(state.userQueue).toHaveLength(0);
    c.add({ relative_path: "b.mp3", title: "B" } as never);
    c.clear();
    expect(state.userQueue).toHaveLength(0);
  });
  it("playFrom dequeues and plays", () => {
    const { c, playItem } = ctl();
    c.add({ relative_path: "a.mp3", title: "A" } as never);
    c.playFrom(0);
    expect(state.userQueue).toHaveLength(0);
    expect(playItem).toHaveBeenCalledTimes(1);
  });
  it("open flag toggles; missing DOM safe", () => {
    const { c } = ctl();
    expect(c.isOpen()).toBe(false);
    c.open(); // no panel in DOM -> stays closed
    expect(c.isOpen()).toBe(false);
    c.close();
    expect(c.isOpen()).toBe(false);
  });
  it("restores persisted height key const", () => {
    expect(QUEUE_HEIGHT_KEY).toBe("hometools_queue_height");
  });
});

