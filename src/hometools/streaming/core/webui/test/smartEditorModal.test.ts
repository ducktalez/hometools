import { describe, it, expect } from "vitest";
import { smartEditorModalHtml, playlistModalListHtml } from "../src/smartEditorModal";
import type { SmartEditorState } from "../src/smartPlaylist";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
const st = (o: Partial<SmartEditorState> = {}): SmartEditorState => ({
  id: null, name: "N<", match: "all", rules: [], limit: "", ...o,
});

describe("smartEditorModalHtml", () => {
  it("shell: ids, escaped name, match radio, no rules", () => {
    const h = smartEditorModalHtml(st(), [], esc, "SM");
    for (const id of ["smart-editor-backdrop", "smart-editor-close", "smart-editor-name", "smart-editor-rules",
      "smart-editor-add-rule", "smart-editor-limit", "smart-editor-cancel", "smart-editor-save"]) {
      expect(h).toContain('id="' + id + '"');
    }
    expect(h).toContain("SM Intelligente Playlist");
    expect(h).toContain('value="N&lt;"');
    expect(h).toContain('value="all" checked');
    expect(h).not.toContain('value="any" checked');
    expect(h).toContain("Schlie\u00dfen");
  });
  it("match any + limit + rule rows rendered", () => {
    const h = smartEditorModalHtml(
      st({ match: "any", limit: 5, rules: [{ field: "rating", op: "gte", value: 3 } as never] }),
      [], esc, "SM"
    );
    expect(h).toContain('value="any" checked');
    expect(h).toContain('id="smart-editor-limit" value="5"');
    expect(h).toContain("<select");
  });
});

describe("playlistModalListHtml", () => {
  it("empty", () => expect(playlistModalListHtml([], esc)).toContain("Noch keine Playlists"));
  it("items with counts", () => {
    const h = playlistModalListHtml([{ id: "a<", name: "A", items: ["x", "y"] } as never, { id: "b", name: "B" } as never], esc);
    expect(h).toContain('data-id="a&lt;"');
    expect(h).toContain("2 Titel");
    expect(h).toContain("0 Titel");
  });
});

