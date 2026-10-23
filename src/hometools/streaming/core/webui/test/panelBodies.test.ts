import { describe, it, expect } from "vitest";
import { dupePanelBodyHtml, queuePanelHtml, ctxMenuHtml } from "../src/panelBodies";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
const o = { escHtml: esc, filePlaceholder: "PH", icDuplicate: "DUP", icTrash: "TR" };
const mk = (p: Record<string, unknown>) => ({ relative_path: "x", title: "T", ...p }) as never;

describe("dupePanelBodyHtml", () => {
  it("empty -> message", () => {
    expect(dupePanelBodyHtml([], {}, null, o)).toContain("Keine Duplikate gefunden.");
  });
  it("group with meta, safe vs warn, folder fallback", () => {
    const items = [
      mk({ relative_path: "a/b.mp3", title: "A<", duration: 61, file_size: 1048576, bitrate: 192 }),
      mk({ relative_path: "c.mp3", title: "" }),
    ];
    const h = dupePanelBodyHtml(items, { k: [0, 1] }, { "a/b.mp3": true }, o);
    expect(h).toContain("(2x)");
    expect(h).toContain("<span>A&lt;</span>");
    expect(h).toContain("dupe-trash-btn--safe");
    expect(h).toContain("dupe-trash-btn--warn");
    expect(h).toContain('dupe-group-item-path">a<');
    expect(h).toContain('dupe-group-item-path">c.mp3<');
    expect(h).toContain("192\u00a0kbps");
    expect(h).toContain("dupe-group-item-meta");
    expect(h.match(/dupe-group-item-meta/g)).toHaveLength(1);
  });
  it("missing index skipped; header falls back to key", () => {
    const h = dupePanelBodyHtml([], { key1: [5] }, null, o);
    expect(h).toContain("<span>key1</span>");
    expect(h).not.toContain("dupe-group-item\"");
  });
});

describe("queuePanelHtml", () => {
  it("empty", () => expect(queuePanelHtml([], esc, "PH", "RM")).toContain("queue-empty"));
  it("items", () => {
    const h = queuePanelHtml([mk({ title: "<t", artist: "" , relative_path: "r"}), mk({ thumbnail_url: "/t", artist: "Ar" })], esc, "PH", "RM");
    expect(h).toContain('data-queue-index="1"');
    expect(h).toContain('src="PH"');
    expect(h).toContain('src="/t"');
    expect(h).toContain("&lt;t");
    expect(h).toContain('queue-item-artist">r<');
    expect(h).toContain(">RM</button>");
  });
});

describe("ctxMenuHtml", () => {
  it("renders items, danger class, escapes, indexes", () => {
    const h = ctxMenuHtml([{ label: "A<", icon: "I" }, { label: "B", danger: true }], esc);
    expect(h).toContain('<button class="ht-ctx-item" data-idx="0">I A&lt;</button>');
    expect(h).toContain('ht-ctx-item ht-ctx-item--danger" data-idx="1"> B');
  });
  it("empty", () => expect(ctxMenuHtml([], esc)).toBe(""));
});