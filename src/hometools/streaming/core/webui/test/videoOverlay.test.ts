import { describe, it, expect, vi, afterEach } from "vitest";
import {
  initVideoOverlay,
  openVideoOverlay,
  closeVideoOverlay,
  enterFloatPlayer,
  exitFloatPlayer,
  showVidControls,
  syncMiniBar,
  isFloating,
  destroyVideoOverlay,
  type VideoOverlayEls,
} from "../src/videoOverlay";

afterEach(() => {
  destroyVideoOverlay();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function el(extra: Record<string, unknown> = {}) {
  const classes = new Set<string>();
  const handlers: Record<string, (e: unknown) => void> = {};
  return {
    hidden: false,
    textContent: "",
    innerHTML: "",
    src: "",
    style: {} as Record<string, string>,
    classes,
    handlers,
    classList: {
      add: (c: string) => classes.add(c),
      remove: (c: string) => classes.delete(c),
      contains: (c: string) => classes.has(c),
    },
    addEventListener: (e: string, f: (e: unknown) => void) => (handlers[e] = f),
    removeEventListener: vi.fn(),
    appendChild: vi.fn(),
    contains: () => false,
    ...extra,
  };
}

function setup(video = true) {
  const docHandlers: Record<string, (e: unknown) => void> = {};
  vi.stubGlobal("window", {
    innerHeight: 600,
    innerWidth: 800,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  });
  vi.stubGlobal("document", {
    fullscreenElement: null,
    addEventListener: (e: string, f: (e: unknown) => void) => (docHandlers[e] = f),
    removeEventListener: vi.fn(),
  });
  const overlay = el();
  overlay.classes.add("view-hidden");
  const miniBar = el();
  const videoWrap = el();
  const floatContainer = el();
  const floatWrap = el();
  const playerListeners: Record<string, () => void> = {};
  const player = el({
    paused: true,
    currentSrc: "x.mp4",
    parentNode: null,
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
  });
  (player as unknown as { addEventListener: unknown }).addEventListener = (e: string, f: () => void) =>
    (playerListeners[e] = f);
  const miniPlayBtn = el();
  const els = {
    player,
    isVideoMode: video,
    overlay,
    miniBar,
    miniTitle: el(),
    miniArtist: el(),
    miniThumb: el(),
    miniPlayBtn,
    miniExpandBtn: el(),
    overlayTitleText: el(),
    videoWrap,
    floatContainer,
    floatWrap,
    floatCloseBtn: el(),
    floatExpandBtn: el(),
    closeBtn: el(),
    icPlay: "PLAY",
    icPause: "PAUSE",
  };
  initVideoOverlay(els as unknown as VideoOverlayEls);
  return { els, docHandlers, playerListeners };
}

describe("videoOverlay", () => {
  it("open shows overlay, hides mini bar, sizes overlay, shows controls", () => {
    const { els } = setup();
    openVideoOverlay();
    expect(els.overlay.classes.has("view-hidden")).toBe(false);
    expect(els.miniBar.hidden).toBe(true);
    expect(els.overlay.style.height).toBe("600px");
    expect(els.overlay.classes.has("controls-hidden")).toBe(false);
    expect(els.videoWrap.appendChild).toHaveBeenCalledWith(els.player);
  });

  it("close hides overlay and shows mini bar when src loaded", () => {
    const { els } = setup();
    openVideoOverlay();
    closeVideoOverlay();
    expect(els.overlay.classes.has("view-hidden")).toBe(true);
    expect(els.miniBar.hidden).toBe(false);
  });

  it("controls auto-hide after 3s while playing", () => {
    vi.useFakeTimers();
    const { els } = setup();
    els.player.paused = false;
    showVidControls();
    vi.advanceTimersByTime(3100);
    expect(els.overlay.classes.has("controls-hidden")).toBe(true);
  });

  it("controls stay while paused", () => {
    vi.useFakeTimers();
    const { els } = setup();
    showVidControls();
    vi.advanceTimersByTime(5000);
    expect(els.overlay.classes.has("controls-hidden")).toBe(false);
  });

  it("enter/exit float moves player and toggles state", () => {
    const { els } = setup();
    enterFloatPlayer();
    expect(isFloating()).toBe(true);
    expect(els.floatWrap.appendChild).toHaveBeenCalledWith(els.player);
    expect(els.floatContainer.classes.has("active")).toBe(true);
    expect(els.floatContainer.style.bottom).toBe("80px");
    exitFloatPlayer();
    expect(isFloating()).toBe(false);
    expect(els.floatContainer.classes.has("active")).toBe(false);
    expect(els.overlay.classes.has("view-hidden")).toBe(false);
  });

  it("float close pauses and clears floating", () => {
    const { els } = setup();
    enterFloatPlayer();
    els.floatCloseBtn.handlers.click({ stopPropagation() {} });
    expect(els.player.pause).toHaveBeenCalled();
    expect(isFloating()).toBe(false);
  });

  it("Escape with overlay open floats; ignored in audio mode", () => {
    let c = setup();
    c.els.overlay.classes.delete("view-hidden");
    c.docHandlers.keydown({ key: "Escape" });
    expect(isFloating()).toBe(true);
    destroyVideoOverlay();
    c = setup(false);
    c.els.overlay.classes.delete("view-hidden");
    c.docHandlers.keydown({ key: "Escape" });
    expect(isFloating()).toBe(false);
  });

  it("syncMiniBar fills text/thumb", () => {
    const { els } = setup();
    syncMiniBar({ title: "T", artist: "A", thumbnail_url: "u.jpg" });
    expect(els.miniTitle.textContent).toBe("T");
    expect(els.miniArtist.textContent).toBe("A");
    expect(els.miniThumb.src).toBe("u.jpg");
    expect(els.overlayTitleText.textContent).toBe("T");
    syncMiniBar({ title: "T" });
    expect(els.miniThumb.style.display).toBe("none");
  });

  it("mini play button icon follows play/pause", () => {
    const { els, playerListeners } = setup();
    els.player.paused = false;
    playerListeners.play();
    expect(els.miniPlayBtn.innerHTML).toBe("PAUSE");
    els.player.paused = true;
    playerListeners.pause();
    expect(els.miniPlayBtn.innerHTML).toBe("PLAY");
  });
});



