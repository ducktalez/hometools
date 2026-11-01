import { describe, it, expect, vi, afterEach } from "vitest";
import { installState, item } from "./helpers";
import { saveInlineTableEdit, normalizeCellText } from "../src/inlineEdit";

afterEach(() => vi.unstubAllGlobals());

function cell(over: Record<string, string> = {}, text = "  New   title ") {
  return { dataset: { field: "title", relativePath: "a.mp3", ...over } as Record<string, string | undefined>, textContent: text };
}
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("normalizeCellText", () => {
  it("collapses whitespace", () => expect(normalizeCellText("  a \n b  ")).toBe("a b"));
  it("null -> empty", () => expect(normalizeCellText(null)).toBe(""));
});

describe("saveInlineTableEdit", () => {
  const h = () => ({ editPath: "/edit", toast: vi.fn() });

  it("cancel / unchanged reverts to old value without fetch", () => {
    const t = item("a.mp3", { title: "Old" });
    installState({ filteredItems: [t] });
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    const c = cell({ cancelled: "1" });
    saveInlineTableEdit(c as never, h());
    expect(c.textContent).toBe("Old");
    expect(c.dataset.cancelled).toBeUndefined();
    const c2 = cell({}, "Old");
    saveInlineTableEdit(c2 as never, h());
    expect(f).not.toHaveBeenCalled();
  });

  it("empty value reverts and toasts", () => {
    installState({ filteredItems: [item("a.mp3", { title: "Old" })] });
    const hh = h();
    const c = cell({}, "   ");
    saveInlineTableEdit(c as never, hh);
    expect(c.textContent).toBe("Old");
    expect(hh.toast).toHaveBeenCalledWith("Feld darf nicht leer sein");
  });

  it("success: posts payload, updates item + cell", async () => {
    const t = item("a.mp3", { title: "Old" }) as unknown as Record<string, unknown>;
    installState({ filteredItems: [t as never] });
    const f = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }));
    vi.stubGlobal("fetch", f);
    const hh = h();
    const c = cell();
    saveInlineTableEdit(c as never, hh);
    await flush();
    expect(JSON.parse((f.mock.calls[0] as unknown as [string, { body: string }])[1].body)).toEqual({ path: "a.mp3", title: "New title" });
    expect(t.title).toBe("New title");
    expect(c.textContent).toBe("New title");
    expect(hh.toast).toHaveBeenCalledWith("Gespeichert");
  });

  it("server error reverts", async () => {
    installState({ filteredItems: [item("a.mp3", { title: "Old" })] });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false })));
    const hh = h();
    const c = cell();
    saveInlineTableEdit(c as never, hh);
    await flush();
    expect(c.textContent).toBe("Old");
    expect(hh.toast).toHaveBeenCalledWith("Fehler beim Speichern");
  });
});

