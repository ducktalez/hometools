import { describe, it, expect } from "vitest";
import { collectDupeItems, dupeSubtitle } from "../src/dupePanel";

describe("dupePanel helpers", () => {
  it("subtitle pluralises", () => {
    expect(dupeSubtitle(1, 2)).toBe("1 Duplikat-Gruppe (2 Dateien)");
    expect(dupeSubtitle(2, 4)).toBe("2 Duplikat-Gruppen (4 Dateien)");
  });
  it("collects group by group, skipping missing", () => {
    const all = [{ relative_path: "a" }, { relative_path: "b" }, { relative_path: "c" }];
    const out = collectDupeItems({ k1: [2, 0], k2: [1, 9] }, all);
    expect(out.map((i) => i.relative_path)).toEqual(["c", "a", "b"]);
  });
});

