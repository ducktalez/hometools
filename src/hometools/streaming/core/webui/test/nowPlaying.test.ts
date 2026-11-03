import { describe, it, expect, vi } from "vitest";
import { showNowPlaying } from "../src/nowPlaying";
import type { NowPlayingEls, NowPlayingHooks } from "../src/nowPlaying";

function els(tag = "AUDIO"): NowPlayingEls & { removed: string[] } {
  const removed: string[] = [];
  return {
    title: { textContent: "" },
    artist: { textContent: "" },
    thumb: { src: "", style: { display: "none" } },
    btnPlay: { innerHTML: "" },
    playerBar: { classList: { remove: (c: string) => removed.push(c) } },
    player: { tagName: tag, style: { display: "none" } },
    overlayTitle: { textContent: "" },
    removed,
  };
}
function hooks(over: Partial<NowPlayingHooks> = {}): NowPlayingHooks {
  return {
    icPause: "PAUSE",
    filePlaceholder: "PH",
    isVideoMode: false,
    openVideoOverlay: vi.fn(),
    syncMiniBar: vi.fn(),
    ...over,
  };
}

describe("showNowPlaying", () => {
  it("audio: title/artist/thumb/icon, bar shown, no overlay", () => {
    const e = els();
    const h = hooks();
    showNowPlaying({ title: "T", artist: "A", thumbnail_url: "/t", thumbnail_lg_url: "/tl" }, e, h);
    expect(e.title.textContent).toBe("T");
    expect(e.artist.textContent).toBe("A");
    expect(e.thumb.src).toBe("/tl");
    expect(e.thumb.style.display).toBe("");
    expect(e.btnPlay.innerHTML).toBe("PAUSE");
    expect(e.removed).toEqual(["view-hidden"]);
    expect(h.openVideoOverlay).not.toHaveBeenCalled();
    expect(e.player.style.display).toBe("none");
  });
  it("fallbacks: artist->path, thumb->placeholder, lg->thumb", () => {
    const e = els();
    showNowPlaying({ title: "T", relative_path: "a/b.mp3" }, e, hooks());
    expect(e.artist.textContent).toBe("a/b.mp3");
    expect(e.thumb.src).toBe("PH");
    showNowPlaying({ title: "T", thumbnail_url: "/t" }, e, hooks());
    expect(e.thumb.src).toBe("/t");
  });
  it("video mode: overlay + mini-bar + title; VIDEO shown", () => {
    const e = els("VIDEO");
    const h = hooks({ isVideoMode: true });
    const t = { title: "V" };
    showNowPlaying(t, e, h);
    expect(h.openVideoOverlay).toHaveBeenCalled();
    expect(h.syncMiniBar).toHaveBeenCalledWith(t);
    expect(e.overlayTitle!.textContent).toBe("V");
    expect(e.player.style.display).toBe("block");
  });
  it("video mode without overlay title element", () => {
    const e = els("VIDEO");
    e.overlayTitle = null;
    expect(() => showNowPlaying({ title: "V" }, e, hooks({ isVideoMode: true }))).not.toThrow();
  });
});

