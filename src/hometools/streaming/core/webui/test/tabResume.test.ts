import { describe, it, expect, vi, afterEach } from "vitest";
import { onTabVisibilityChange } from "../src/tabResume";

afterEach(() => vi.unstubAllGlobals());

function player(paused: boolean) {
  return { paused, play: vi.fn(() => Promise.resolve()) };
}
function hooks(p: ReturnType<typeof player>) {
  return { player: p as unknown as HTMLMediaElement };
}

describe("tabResume", () => {
  it("resumes when hidden while playing, then visible + paused", () => {
    const p = player(false);
    vi.stubGlobal("document", { hidden: true });
    onTabVisibilityChange(hooks(p));
    p.paused = true;
    vi.stubGlobal("document", { hidden: false });
    onTabVisibilityChange(hooks(p));
    expect(p.play).toHaveBeenCalledTimes(1);
  });
  it("no resume when paused before hide", () => {
    const p = player(true);
    vi.stubGlobal("document", { hidden: true });
    onTabVisibilityChange(hooks(p));
    vi.stubGlobal("document", { hidden: false });
    onTabVisibilityChange(hooks(p));
    expect(p.play).not.toHaveBeenCalled();
  });
  it("no resume when still playing on visible", () => {
    const p = player(false);
    vi.stubGlobal("document", { hidden: true });
    onTabVisibilityChange(hooks(p));
    vi.stubGlobal("document", { hidden: false });
    onTabVisibilityChange(hooks(p));
    expect(p.play).not.toHaveBeenCalled();
  });
});

