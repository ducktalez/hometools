import { describe, it, expect, vi } from "vitest";
import { folderGridAction, initFolderGridEvents } from "../src/folderGridEvents";

const target = (hit: string | null) =>
  ({ closest: (sel: string) => (sel === hit ? {} : null) }) as unknown as Element;

describe("folderGridAction", () => {
  it("maps selectors", () => {
    expect(folderGridAction(target(".refresh-catalog-card"))).toBe("refresh");
    expect(folderGridAction(target("#add-folder-card"))).toBe("add");
    expect(folderGridAction(target("#remove-folder-card"))).toBe("remove");
    expect(folderGridAction(target(null))).toBeNull();
    expect(folderGridAction(null)).toBeNull();
  });
});

describe("initFolderGridEvents", () => {
  it("dispatches click to matching action", () => {
    let handler: (e: Event) => void = () => {};
    const grid = { addEventListener: (_t: string, h: (e: Event) => void) => (handler = h) } as unknown as HTMLElement;
    const o = { folderGrid: grid, refreshCatalog: vi.fn(), addExtraFolder: vi.fn(), removeExtraFolder: vi.fn() };
    initFolderGridEvents(o);
    handler({ target: target("#add-folder-card") } as unknown as Event);
    expect(o.addExtraFolder).toHaveBeenCalledTimes(1);
    expect(o.refreshCatalog).not.toHaveBeenCalled();
  });
  it("no-op without grid", () => {
    expect(() =>
      initFolderGridEvents({ folderGrid: null, refreshCatalog: vi.fn(), addExtraFolder: vi.fn(), removeExtraFolder: vi.fn() }),
    ).not.toThrow();
  });
});

