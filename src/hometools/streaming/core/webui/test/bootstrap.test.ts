import { describe, it, expect, vi } from "vitest";
import { installState, removeState } from "./helpers";
import { bootstrapApp } from "../src/bootstrap";

function hooks(calls: string[]) {
  const rec = (n: string) => () => void calls.push(n);
  return {
    loadInitialCatalog: () => {
      calls.push("catalog");
      return Promise.resolve();
    },
    routerInit: rec("routerInit"),
    loadFavorites: rec("favorites"),
    loadUserPlaylists: () => {
      calls.push("playlists");
      return Promise.resolve();
    },
    routerRestore: rec("restore"),
    showFolderView: vi.fn(() => void calls.push("root")),
    startPlaylistSync: rec("sync"),
  };
}

describe("bootstrapApp", () => {
  it("runs steps in order and shows root view on clean state", async () => {
    installState();
    const calls: string[] = [];
    await bootstrapApp(hooks(calls));
    expect(calls).toEqual(["catalog", "routerInit", "favorites", "playlists", "restore", "root", "sync"]);
  });

  it("skips root view when router restored a folder or playlist", async () => {
    for (const over of [{ currentPath: "a" }, { inPlaylist: true }]) {
      installState(over);
      const calls: string[] = [];
      await bootstrapApp(hooks(calls));
      expect(calls).not.toContain("root");
      expect(calls[calls.length - 1]).toBe("sync");
    }
  });

  it("without htState: no root view, still syncs", async () => {
    removeState();
    const calls: string[] = [];
    await bootstrapApp(hooks(calls));
    expect(calls).not.toContain("root");
    expect(calls).toContain("sync");
  });
});

