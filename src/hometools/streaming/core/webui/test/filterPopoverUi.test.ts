import { describe, it, expect, vi, afterEach } from "vitest";
import { toggleFilterPopover, closeFilterPopover, isFilterPopoverOpen, renderFilterPopoverBody } from "../src/filterPopoverUi";
import type { FilterPopoverHooks } from "../src/filterPopoverUi";

afterEach(() => {
  closeFilterPopover();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

type L = (e?: unknown) => void;

function stubDom() {
  let pop: Record<string, unknown> | null = null;
  const doc: Record<string, L> = {};
  const wired: Record<string, Record<string, L>> = {};
  const mkEl = (id: string) => {
    const handlers: Record<string, L> = {};
    wired[id] = handlers;
    return { addEventListener: (ev: string, f: L) => (handlers[ev] = f), dataset: {}, value: "", checked: false };
  };
  const els: Record<string, ReturnType<typeof mkEl>> = {};
  const popEl = {
    id: "",
    className: "",
    innerHTML: "",
    offsetHeight: 100,
    style: {} as Record<string, string>,
    contains: () => false,
    remove: () => {
      pop = null;
    },
    querySelectorAll: (sel: string) => (sel === ".filter-popover-star" ? [stars] : []),
    querySelector: (sel: string) => {
      const id = sel.replace("#", "");
      return (els[id] = els[id] || mkEl(id));
    },
  };
  const stars = { ...mkEl("star"), dataset: { star: "3" } };
  vi.stubGlobal("window", { innerWidth: 1000, innerHeight: 800 });
  vi.stubGlobal("localStorage", { setItem: vi.fn() });
  vi.stubGlobal("document", {
    getElementById: (id: string) => (id === "ht-filter-popover" ? pop : null),
    createElement: () => popEl,
    body: {
      appendChild: (el: unknown) => {
        pop = el as Record<string, unknown>;
      },
    },
    addEventListener: (ev: string, f: L) => (doc[ev] = f),
    removeEventListener: (ev: string) => delete doc[ev],
  });
  return { doc, wired, stars, els, popEl };
}

function hooks(over: Partial<FilterPopoverHooks> = {}): FilterPopoverHooks {
  let f = { rating: 0, fav: false, genre: "" };
  return {
    genres: () => ["Rock"],
    getFilter: () => f,
    setFilter: (p) => (f = { ...f, ...p }),
    icons: { starFilled: "*", starEmpty: "o" },
    esc: (s) => String(s),
    onChange: vi.fn(),
    ...over,
  };
}

const btn = () => ({ getBoundingClientRect: () => ({ right: 900, bottom: 50, top: 10 }), contains: () => false }) as unknown as HTMLElement;

describe("filter popover lifecycle", () => {
  it("toggle opens, positions, second toggle closes", () => {
    vi.useFakeTimers();
    const d = stubDom();
    const h = hooks();
    expect(isFilterPopoverOpen()).toBe(false);
    toggleFilterPopover(btn(), h);
    expect(isFilterPopoverOpen()).toBe(true);
    expect(d.popEl.style.right).toBe("100px");
    expect(d.popEl.style.top).toBe("56px"); // below the button (enough space)
    vi.runAllTimers();
    expect(Object.keys(d.doc).sort()).toEqual(["click", "keydown"]);
    toggleFilterPopover(btn(), h);
    expect(isFilterPopoverOpen()).toBe(false);
    expect(Object.keys(d.doc)).toEqual([]);
  });

  it("Escape closes", () => {
    vi.useFakeTimers();
    const d = stubDom();
    toggleFilterPopover(btn(), hooks());
    vi.runAllTimers();
    d.doc.keydown({ key: "Escape" });
    expect(isFilterPopoverOpen()).toBe(false);
  });

  it("star click toggles rating, persists, notifies; same star resets to 0", () => {
    vi.useFakeTimers();
    const d = stubDom();
    const h = hooks();
    toggleFilterPopover(btn(), h);
    d.wired.star.click();
    expect(h.getFilter().rating).toBe(3);
    expect(h.onChange).toHaveBeenCalledTimes(1);
    d.wired.star.click();
    expect(h.getFilter().rating).toBe(0);
  });

  it("render on closed popover is a no-op", () => {
    stubDom();
    renderFilterPopoverBody(hooks());
    expect(isFilterPopoverOpen()).toBe(false);
  });
});

