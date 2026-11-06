import { describe, it, expect, vi } from "vitest";
import { installState } from "./helpers";
import { goBack, closeOfflineLibrary } from "../src/backNav";

const hooks = (folders = 0) => ({
  exitGlobalSearch: vi.fn(),
  showFolderView: vi.fn(),
  contentsAt: vi.fn(() => ({ folders: new Array(folders).fill({}) })),
});

describe("goBack", () => {
  it("exits global search first", () => {
    const s = installState({ globalSearchActive: true, currentPath: "a/b" });
    const h = hooks();
    goBack(h);
    expect(h.exitGlobalSearch).toHaveBeenCalled();
    expect(h.showFolderView).not.toHaveBeenCalled();
    expect(s.currentPath).toBe("a/b");
  });
  it("leaves offline view to root", () => {
    const s = installState({ currentPath: "__offline__" });
    const h = hooks();
    goBack(h);
    expect(s.currentPath).toBe("");
    expect(h.showFolderView).toHaveBeenCalledTimes(1);
  });
  it("playlist view with subfolders: just show folder view, path unchanged", () => {
    const s = installState({ inPlaylist: true, currentPath: "a/b" });
    const h = hooks(2);
    goBack(h);
    expect(s.currentPath).toBe("a/b");
    expect(h.showFolderView).toHaveBeenCalledTimes(1);
  });
  it("playlist view without subfolders / normal view: go to parent", () => {
    const s = installState({ inPlaylist: true, currentPath: "a/b" });
    goBack(hooks(0));
    expect(s.currentPath).toBe("a");
    const s2 = installState({ inPlaylist: false, currentPath: "a" });
    const h2 = hooks(5);
    goBack(h2);
    expect(s2.currentPath).toBe("");
    expect(h2.contentsAt).not.toHaveBeenCalled();
  });
});

describe("closeOfflineLibrary", () => {
  it("only acts in offline view", () => {
    const s = installState({ currentPath: "x" });
    const h = hooks();
    closeOfflineLibrary(h);
    expect(h.showFolderView).not.toHaveBeenCalled();
    s.currentPath = "__offline__";
    closeOfflineLibrary(h);
    expect(s.currentPath).toBe("");
    expect(h.showFolderView).toHaveBeenCalledTimes(1);
  });
});

