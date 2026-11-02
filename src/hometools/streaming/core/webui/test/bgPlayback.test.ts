import { describe, it, expect, vi, afterEach } from "vitest";
import { onVisibilityChange, setWasPlaying, wasPlaying } from "../src/bgPlayback";
import { startBgMirror, stopBgSync, getBgAudio } from "../src/bgAudio";

afterEach(() => {
  stopBgSync();
  setWasPlaying(false);
  vi.unstubAllGlobals();
});

function fakeAudio() {
  return {
    style: {},
    src: "",
    currentTime: 0,
    muted: true,
    paused: false,
    play: vi.fn(() => Promise.resolve()),
    addEventListener: vi.fn(),
  };
}
function player() {
  return { src: "/v", currentTime: 5, paused: false, play: vi.fn(() => Promise.resolve()) };
}
function stubDoc(hidden: boolean) {
  const doc = { hidden, createElement: fakeAudio, body: { appendChild: vi.fn() }, pictureInPictureElement: null };
  vi.stubGlobal("document", doc);
  vi.stubGlobal("navigator", { mediaSession: { playbackState: "none" } });
  return doc;
}
function hooks(p: ReturnType<typeof player>, isIOS = true) {
  return { player: p as unknown as HTMLVideoElement, isVideoPlayer: true, isIOS };
}

describe("bgPlayback", () => {
  it("flag get/set", () => {
    setWasPlaying(true);
    expect(wasPlaying()).toBe(true);
    setWasPlaying(false);
    expect(wasPlaying()).toBe(false);
  });
  it("hidden on iOS: unmute bg audio at video position, signal playing", () => {
    stubDoc(false);
    const p = player();
    startBgMirror({ player: p as unknown as HTMLMediaElement, isVideoPlayer: true, playNext: vi.fn() });
    const doc = stubDoc(true);
    void doc;
    setWasPlaying(true);
    const bg = getBgAudio()!;
    p.currentTime = 42;
    onVisibilityChange(hooks(p));
    expect(bg.muted).toBe(false);
    expect(bg.currentTime).toBe(42);
    expect(navigator.mediaSession.playbackState).toBe("playing");
  });
  it("visible again: video resumes at bg position, bg muted", () => {
    stubDoc(false);
    const bg = getBgAudio()!;
    bg.muted = false;
    bg.currentTime = 99;
    const p = player();
    setWasPlaying(true);
    onVisibilityChange(hooks(p));
    expect(p.currentTime).toBe(99);
    expect(p.play).toHaveBeenCalled();
    expect(bg.muted).toBe(true);
  });
  it("ignored when not wasPlaying or not video", () => {
    stubDoc(false);
    const p = player();
    p.paused = true;
    onVisibilityChange(hooks(p));
    expect(p.play).not.toHaveBeenCalled();
    setWasPlaying(true);
    onVisibilityChange({ ...hooks(p), isVideoPlayer: false });
    expect(p.play).not.toHaveBeenCalled();
  });
});

