import { describe, it, expect, beforeEach } from "vitest";
import { toolFlags, anyToolActive, isToolsPanelOpen, _resetToolsPanelForTest } from "../src/toolsPanel";

beforeEach(() => _resetToolsPanelForTest());

describe("anyToolActive", () => {
  it("false without tool mode, even when sub-tools are set", () => {
    toolFlags().inlineRatings = true;
    expect(anyToolActive()).toBe(false);
  });
  it("true only when active AND a layout-relevant tool is on", () => {
    const f = toolFlags();
    f.active = true;
    expect(anyToolActive()).toBe(false);
    f.bpmCalc = true; /* not layout-relevant */
    expect(anyToolActive()).toBe(false);
    f.fileMover = true;
    expect(anyToolActive()).toBe(true);
  });
});

describe("toolFlags", () => {
  it("defaults to empty without localStorage (node env)", () => {
    expect(toolFlags()).toEqual({});
  });
});

describe("isToolsPanelOpen", () => {
  it("false when the panel element is missing", () => {
    (globalThis as unknown as { document: object }).document = { getElementById: () => null };
    expect(isToolsPanelOpen()).toBe(false);
  });
  it("reflects the hidden attribute", () => {
    let hidden = true;
    (globalThis as unknown as { document: object }).document = {
      getElementById: () => ({ hasAttribute: () => hidden }),
    };
    expect(isToolsPanelOpen()).toBe(false);
    hidden = false;
    expect(isToolsPanelOpen()).toBe(true);
  });
});

