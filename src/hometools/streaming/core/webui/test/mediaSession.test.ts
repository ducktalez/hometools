import { describe, it, expect, vi, afterEach } from "vitest";
import { updateMediaSession, activeMedia } from "../src/mediaSession";
import { wasPlaying, setWasPlaying } from "../src/bgPlayback";
import { getBgAudio } from "../src/bgAudio";

afterEach(() => {
  setWasPlaying(false);
  vi.unstubAllGlobals();
});

function setup() {
  const handlers: Record<string, (d?: unknown) => void> = {};
  vi.stubGlobal("navigator", {
    mediaSession: { metadata: null, setActionHandler: (n: string, f: () => void) => (handlers[n] = f) },
  });
  vi.stubGlobal("MediaMetadata", class { constructor(public init: Record<string, unknown>) {} });
  const player = { play: vi.fn(() => Promise.resolve()), pause: vi.fn(), currentTime: 0 };
  const hooks = {
    player: player as unknown as HTMLMediaElement,
    itemNoun: "video",
    previousTrack: vi.fn(),
    nextTrack: vi.fn(),
  };
  return { handlers, player, hooks };
}

describe("mediaSession", () => {
  it("sets metadata (album by noun)", () => {
    const { hooks } = setup();
    updateMediaSession({ title: "T", artist: "A" }, hooks);
    const init = (navigator.mediaSession.metadata as unknown as { init: Record<string, unknown> }).init;
    expect(init.title).toBe("T");
    expect(init.album).toBe("hometools video");
    updateMediaSession({ title: "T" }, { ...hooks, itemNoun: "audio" });
    expect((navigator.mediaSession.metadata as unknown as { init: Record<string, unknown> }).init.album).toBe(
      "hometools audio"
    );
  });
  it("play/pause toggle wasPlaying; next/prev forward; seekto sets time", () => {
    const { handlers, player, hooks } = setup();
    updateMediaSession({ title: "T" }, hooks);
    handlers.play();
    expect(player.play).toHaveBeenCalled();
    expect(wasPlaying()).toBe(true);
    handlers.pause();
    expect(player.pause).toHaveBeenCalled();
    expect(wasPlaying()).toBe(false);
    handlers.nexttrack();
    handlers.previoustrack();
    expect(hooks.nextTrack).toHaveBeenCalled();
    expect(hooks.previousTrack).toHaveBeenCalled();
    handlers.seekto({ seekTime: 33 });
    expect(player.currentTime).toBe(33);
  });
  it("no mediaSession -> no-op; activeMedia defaults to player", () => {
    vi.stubGlobal("navigator", {});
    const p = {} as HTMLMediaElement;
    expect(() => updateMediaSession({ title: "x" }, { player: p, itemNoun: "audio", previousTrack() {}, nextTrack() {} })).not.toThrow();
    expect(getBgAudio() === null || getBgAudio() !== undefined).toBe(true);
    expect(activeMedia(p)).toBe(p);
  });
});

