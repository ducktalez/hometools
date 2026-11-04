import { describe, it, expect, vi } from "vitest";
import { installState } from "./helpers";
import { renderBreadcrumb } from "../src/breadcrumb";
import type { BreadcrumbHooks } from "../src/breadcrumb";

function mk() {
  const cls = new Set<string>();
  let click: (() => void) | null = null;
  const link = { dataset: { path: "a/b" }, addEventListener: (_t: string, f: () => void) => (click = f) };
  const hooks = {
    breadcrumb: {
      classList: { add: (c: string) => cls.add(c), remove: (c: string) => cls.delete(c) },
      innerHTML: "",
      querySelectorAll: () => [link],
    },
    headerTitle: { style: { display: "x" } },
    escHtml: (s: unknown) => String(s),
    showFolderView: vi.fn(),
  };
  return { hooks, cls, click: () => click!() };
}

describe("renderBreadcrumb", () => {
  it("hides when no path", () => {
    installState({ currentPath: "" });
    const m = mk();
    m.cls.add("visible");
    renderBreadcrumb(m.hooks as unknown as BreadcrumbHooks);
    expect(m.cls.has("visible")).toBe(false);
    expect(m.hooks.headerTitle.style.display).toBe("");
  });
  it("shows path, hides title, link click navigates", () => {
    const s = installState({ currentPath: "a/b/c" });
    const m = mk();
    renderBreadcrumb(m.hooks as unknown as BreadcrumbHooks);
    expect(m.cls.has("visible")).toBe(true);
    expect(m.hooks.headerTitle.style.display).toBe("none");
    expect(m.hooks.breadcrumb.innerHTML).toContain('data-path="a/b"');
    m.click();
    expect(s.currentPath).toBe("a/b");
    expect(m.hooks.showFolderView).toHaveBeenCalled();
  });
});

