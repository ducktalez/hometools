import { describe, it, expect } from "vitest";
import { collectDom } from "../src/dom";

describe("collectDom", () => {
  it("maps ids and selectors, missing -> null", () => {
    const doc = {
      getElementById: (id: string) => (id === "player" ? ({ id } as HTMLElement) : null),
      querySelector: (sel: string) => (sel === ".filter-bar" ? ({ sel } as unknown as HTMLElement) : null),
    };
    const d = collectDom(doc);
    expect((d.player as unknown as { id: string }).id).toBe("player");
    expect(d.btnPlay).toBeNull();
    expect(d.filterBar).not.toBeNull();
    expect(d.playerBar).toBeNull();
  });
  it("uses the ids legacy relied on", () => {
    const asked: string[] = [];
    collectDom({ getElementById: (i) => (asked.push(i), null), querySelector: () => null });
    expect(asked).toContain("header-logo");
    expect(asked).toContain("track-list");
    expect(asked).toContain("downloaded-pill");
  });
});
