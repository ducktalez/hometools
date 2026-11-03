/**
 * Now-playing UI update for `playItem`. Ported from
 * `player_js/_library_tools.py` (title/artist/thumb/play-icon/video overlay).
 */

export interface NowPlayingItem {
  title?: string;
  artist?: string;
  relative_path?: string;
  thumbnail_url?: string;
  thumbnail_lg_url?: string;
}

export interface NowPlayingEls {
  title: { textContent: string | null };
  artist: { textContent: string | null };
  thumb: { src: string; style: { display: string } };
  btnPlay: { innerHTML: string };
  playerBar: { classList: { remove(c: string): void } };
  player: { tagName: string; style: { display: string } };
  /** Video overlay title element (may be absent). */
  overlayTitle: { textContent: string | null } | null;
}

export interface NowPlayingHooks {
  icPause: string;
  filePlaceholder: string;
  isVideoMode: boolean;
  openVideoOverlay(): void;
  syncMiniBar(t: NowPlayingItem): void;
}

export function showNowPlaying(t: NowPlayingItem, els: NowPlayingEls, h: NowPlayingHooks): void {
  els.title.textContent = t.title ?? "";
  els.artist.textContent = t.artist || t.relative_path || "";
  els.thumb.src = t.thumbnail_url ? t.thumbnail_lg_url || t.thumbnail_url : h.filePlaceholder;
  els.thumb.style.display = "";
  els.btnPlay.innerHTML = h.icPause;
  els.playerBar.classList.remove("view-hidden");
  if (h.isVideoMode) {
    h.openVideoOverlay();
    h.syncMiniBar(t);
    if (els.overlayTitle) els.overlayTitle.textContent = t.title || "";
  }
  /* CSS sets #player { display:none } — override inline before playback. */
  if (els.player.tagName === "VIDEO") els.player.style.display = "block";
}

