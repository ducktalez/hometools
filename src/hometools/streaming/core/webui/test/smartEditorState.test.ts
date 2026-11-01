import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { installState } from "./helpers";
import { openSmartPlaylistEditor, collectFromDom, getEditorState } from "../src/smartEditor";

const hooks = () => ({
  apiPath: "/smart",
  esc: (s: unknown) => String(s),
  icon: "<i/>",
  toast: vi.fn(),
  showFolderView: vi.fn(),
});

function stubDocument() {
  const insert = vi.fn();
  vi.stubGlobal("document", {
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    body: { insertAdjacentHTML: insert },
  });
  return insert;
}

beforeEach(() => installState({ userPlaylists: [] }));
afterEach(() => vi.unstubAllGlobals());

describe("smartEditor state", () => {
  it("new editor: default state + modal inserted", () => {
    const insert = stubDocument();
    openSmartPlaylistEditor(null, hooks());
    expect(getEditorState()).toMatchObject({ id: null, name: "", match: "all", limit: "" });
    expect(getEditorState()!.rules).toEqual([{ field: "rating", op: "gte", value: 4 }]);
    expect(insert).toHaveBeenCalledWith("beforeend", expect.stringContaining("smart-editor-backdrop"));
  });
  it("edit: deep-clones rules from existing playlist", () => {
    stubDocument();
    const pl = { id: "p", name: "P", smart: { match: "any" as const, rules: [{ field: "rating", op: "gte", value: 3 }], limit: 10 } };
    openSmartPlaylistEditor(pl, hooks());
    const st = getEditorState()!;
    expect(st).toMatchObject({ id: "p", name: "P", match: "any", limit: 10 });
    expect(st.rules).toEqual(pl.smart.rules);
    expect(st.rules).not.toBe(pl.smart.rules);
  });
  it("collectFromDom reads name/limit/match and typed rule values", () => {
    stubDocument();
    openSmartPlaylistEditor(null, hooks());
    const inputs: Record<string, { value: string }> = {
      ".smart-rule-field": { value: "rating" },
      ".smart-rule-op": { value: "gte" },
      ".smart-rule-value": { value: "5" },
    };
    const row = { dataset: { idx: "0" }, querySelector: (s: string) => inputs[s], querySelectorAll: () => [] };
    const doc = {
      getElementById: (id: string) =>
        id === "smart-editor-name" ? { value: "  Mix " } : id === "smart-editor-limit" ? { value: "25" } : null,
      querySelector: () => ({ value: "any" }),
      querySelectorAll: () => [row],
    } as unknown as Document;
    collectFromDom(doc);
    expect(getEditorState()).toMatchObject({ name: "Mix", limit: 25, match: "any" });
    expect(getEditorState()!.rules[0]).toEqual({ field: "rating", op: "gte", value: 5 });
  });
});

