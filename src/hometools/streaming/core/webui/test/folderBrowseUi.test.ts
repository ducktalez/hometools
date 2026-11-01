import { describe, it, expect, vi, afterEach } from "vitest";
import { installState } from "./helpers";
import { langPickerInnerHtml, playlistCtxMenuItems, initGlobalSearch, hideGlobalSearch } from "../src/folderBrowseUi";

afterEach(() => vi.unstubAllGlobals());

const lh = () => ({
  esc: (s: unknown) => String(s).replace(/</g, "&lt;"),
  itemNoun: "video",
  langToFlag: { de: "<svg-de/>" },
  langNames: { de: "Deutsch" },
  cleanFolderName: (s: string) => "clean:" + s,
  playAllIn: vi.fn(),
  navigateInto: vi.fn(),
});

describe("langPickerInnerHtml", () => {
  it("heading depends on mode; flag/label/plural", () => {
    const v = [
      { name: "Show (de)", lang: "de", count: 2 },
      { name: "Show <x>", lang: "xx", count: 1 },
    ];
    const play = langPickerInnerHtml(v, true, lh());
    expect(play).toContain("Sprache zum Abspielen wählen");
    expect(play).toContain('<span class="lang-picker-flag"><svg-de/></span>');
    expect(play).toContain(">Deutsch<");
    expect(play).toContain("2 videos");
    expect(play).toContain("1 video<");
    expect(play).toContain(">clean:Show &lt;x><"); // unknown lang -> cleaned folder name, escaped
    expect(langPickerInnerHtml(v, false, lh())).toContain("Sprachversion wählen");
  });
});

describe("playlistCtxMenuItems", () => {
  const h = () => ({ refresh: vi.fn(), editRules: vi.fn(), rename: vi.fn(), remove: vi.fn(), icEdit: "E", icTrash: "T" });
  it("regular playlist: rename + delete only", () => {
    const items = playlistCtxMenuItems({ id: "a" }, h());
    expect(items.map((i) => i.label)).toEqual(["Umbenennen", "Löschen"]);
    expect(items[1].danger).toBe(true);
  });
  it("smart playlist: refresh + edit rules first; handlers get ids", () => {
    const hh = h();
    const pl = { id: "s", smart: { rules: [] } };
    const items = playlistCtxMenuItems(pl, hh);
    expect(items.map((i) => i.label)).toEqual(["Aktualisieren", "Regeln bearbeiten", "Umbenennen", "Löschen"]);
    items.forEach((i) => i.onClick());
    expect(hh.refresh).toHaveBeenCalledWith("s");
    expect(hh.editRules).toHaveBeenCalledWith(pl);
    expect(hh.rename).toHaveBeenCalledWith("s");
    expect(hh.remove).toHaveBeenCalledWith("s");
  });
});

describe("global search wiring", () => {
  function stubInput() {
    const handlers: Record<string, (e?: unknown) => void> = {};
    const cls = new Set<string>(["view-hidden"]);
    const inp = {
      value: "",
      classList: { remove: (c: string) => cls.delete(c), add: (c: string) => cls.add(c) },
      addEventListener: (ev: string, f: (e?: unknown) => void) => (handlers[ev] = f),
      blur: vi.fn(),
    };
    vi.stubGlobal("document", { getElementById: () => inp });
    return { inp, handlers, cls };
  }
  it("shows box, debounces input, Escape exits", () => {
    vi.useFakeTimers();
    const s = installState({ globalSearchActive: true });
    const { inp, handlers, cls } = stubInput();
    const h = { globalSearch: vi.fn(), exitGlobalSearch: vi.fn() };
    initGlobalSearch(h);
    expect(cls.has("view-hidden")).toBe(false);
    inp.value = " abc ";
    handlers.input();
    handlers.input();
    vi.advanceTimersByTime(250);
    expect(h.globalSearch).toHaveBeenCalledTimes(1);
    expect(h.globalSearch).toHaveBeenCalledWith("abc");
    inp.value = "";
    handlers.input();
    expect(h.exitGlobalSearch).toHaveBeenCalledTimes(1);
    inp.value = "zzz";
    handlers.keydown({ key: "Escape" });
    expect(inp.value).toBe("");
    expect(h.exitGlobalSearch).toHaveBeenCalledTimes(2);
    s.globalSearchActive = false;
    handlers.keydown({ key: "Escape" });
    expect(h.exitGlobalSearch).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
  it("hide clears + hides", () => {
    const { inp, cls } = stubInput();
    inp.value = "x";
    hideGlobalSearch();
    expect(inp.value).toBe("");
    expect(cls.has("view-hidden")).toBe(true);
  });
});

