import { describe, it, expect } from "vitest";
import { LANG_NAME_MAP } from "../src/langNames";

describe("langNames", () => {
  it("maps codes to native names", () => {
    expect(LANG_NAME_MAP.de).toBe("Deutsch");
    expect(LANG_NAME_MAP.fr).toBe("Français");
    expect(LANG_NAME_MAP.ja).toBe("日本語");
    expect(Object.keys(LANG_NAME_MAP)).toHaveLength(10);
  });
});

