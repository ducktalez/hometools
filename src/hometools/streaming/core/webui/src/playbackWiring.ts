/**
 * Playback hook wiring. Replaces the hook-builder glue formerly in
 * transport (toggle/previous), bg-audio mirror, media session, crossfade.
 */

import { getState } from "./stateBridge";
import { getDom } from "./dom";
import type { PlaybackState } from "./playbackState";
import { playItem, type PlayItemTrack } from "./playItem";
import { refreshMetadata, type MetadataItem } from "./metadataRefresh";
import { togglePlay, handlePreviousTrack, type TransportHooks } from "./transport";
import { startBgMirror, bgAudioIsActive, stopBgSync } from "./bgAudio";
import { activeMedia, updateMediaSession } from "./mediaSession";
import { beginPlayback, type Playback } from "./playbackStart";
import { showNowPlaying, type NowPlayingItem } from "./nowPlaying";
import { startCrossfade, finishCrossfade, type CrossfadeHooks } from "./crossfade";
import { getProgressPath } from "./progress";
import { setCurrentIntro } from "./introUi";

export interface PlaybackCfg {
  apiPath: string;
  itemNoun: string;
  isVideoMode: boolean;
  isVideoPlayer: boolean;
  icPause: string;
  icPlay: string;
  filePlaceholder: string;
  autoResume: boolean;
  lyricsEnabled: boolean;
  crossfadeDuration: number;
}

export interface PlaybackDeps {
  revokeOfflineUrl(): void;
  generateWaveform(url: string, relPath: string): void;
  playOfflineOrStream(url: string): Promise<Playback>;
  openVideoOverlay(): void;
  syncMiniBar(t: NowPlayingItem): void;
  markActive(): void;
  renderPlayerRating(stars: number): void;
  updatePlayerBarActions(): void;
  isLyricsOpen(): boolean;
  openLyricsPanel(path: string, title: string | undefined): void;
  saveProgressNow(): void;
  clearProgressFor(path: string | null): void;
  saveLastPlayedLocal(relPath: string, pos: number): void;
  loadAndSeekProgress(relPath: string): void;
  loadSpriteData(relPath: string): void;
  routerUpdate(): void;
  applyFilter(): void;
  playFromQueue(i: number): void;
}

export function createPlaybackWiring(cfg: PlaybackCfg, deps: () => PlaybackDeps) {
  const player = (): HTMLMediaElement => getDom().player as unknown as HTMLMediaElement;

  const bgMirror = (): void =>
    startBgMirror({ player: player(), isVideoPlayer: cfg.isVideoPlayer, playNext: () => callPlayNext() });

  let callPlayNext: () => void = () => {};

  const media = (t: { title?: string; artist?: string }): void =>
    updateMediaSession(t, {
      player: player(),
      itemNoun: cfg.itemNoun,
      previousTrack: () => handlePreviousTrack(transportHooks()),
      nextTrack: () => callPlayNext(),
    });

  const transportHooks = (): TransportHooks => ({
    player: player(),
    btnPlay: getDom().btnPlay as unknown as { innerHTML: string },
    icPlay: cfg.icPlay,
    icPause: cfg.icPause,
    playTrack: (i: number) => playTrack(i),
    startBgMirror: bgMirror,
    stopBgSync,
    currentItemDuration: () => (getState() as unknown as PlaybackState | undefined)?.itemDuration ?? 0,
  });

  const xfadeHooks = (): CrossfadeHooks => {
    const d = deps();
    return {
      player: player(),
      durationSec: cfg.crossfadeDuration,
      flushOutgoingProgress: () => {
        d.saveProgressNow();
        d.clearProgressFor(getProgressPath());
      },
      playTrack: (i: number) => playTrack(i),
      playFromQueue: d.playFromQueue,
    };
  };

  const refresh = (t: MetadataItem): void => {
    const d = deps();
    const dom = getDom();
    void refreshMetadata(t, {
      apiPath: cfg.apiPath,
      setTitle: (s) => {
        if (dom.playerTitle) dom.playerTitle.textContent = s;
      },
      setArtist: (s) => {
        if (dom.playerArtist) dom.playerArtist.textContent = s;
      },
      renderPlayerRating: d.renderPlayerRating,
      updateMediaSession: media,
      applyFilter: d.applyFilter,
      markActive: d.markActive,
    });
  };

  const play = (t: PlayItemTrack, index?: number): void => {
    const d = deps();
    const dom = getDom();
    const s = getState();
    if (!s) return;
    playItem(t, index, {
      player: player(),
      setCurrentIndex: (i) => {
        s.currentIndex = i;
      },
      setCurrentStreamUrl: (u) => {
        s.currentStreamUrl = u;
      },
      setCurrentDuration: (sec) => {
        (s as unknown as PlaybackState).itemDuration = sec;
      },
      setCurrentIntro: setCurrentIntro as never,
      beginPlayback: (pb) =>
        beginPlayback(pb, t.relative_path ?? "", {
          player: player(),
          btnPlay: dom.btnPlay as unknown as { innerHTML: string },
          icPause: cfg.icPause,
          icPlay: cfg.icPlay,
          revokeOfflineUrl: d.revokeOfflineUrl,
          onStarted: bgMirror,
          generateWaveform: d.generateWaveform,
        }),
      playOfflineOrStream: d.playOfflineOrStream,
      showNowPlaying: (tr) =>
        showNowPlaying(
          tr,
          {
            title: dom.playerTitle,
            artist: dom.playerArtist,
            thumb: dom.playerThumb,
            btnPlay: dom.btnPlay,
            playerBar: dom.playerBar,
            player: dom.player,
            overlayTitle: dom.videoOverlayTitleText ?? null,
          } as never,
          {
            icPause: cfg.icPause,
            filePlaceholder: cfg.filePlaceholder,
            isVideoMode: cfg.isVideoMode,
            openVideoOverlay: d.openVideoOverlay,
            syncMiniBar: d.syncMiniBar,
          },
        ),
      markActive: d.markActive,
      updateMediaSession: media,
      renderPlayerRating: d.renderPlayerRating,
      updatePlayerBarActions: d.updatePlayerBarActions,
      refreshMetadata: (tr) => refresh(tr as MetadataItem),
      refreshLyricsIfOpen: (tr) => {
        if (cfg.lyricsEnabled && d.isLyricsOpen()) d.openLyricsPanel(tr.relative_path || "", tr.title);
      },
      saveProgressNow: d.saveProgressNow,
      saveLastPlayedLocal: d.saveLastPlayedLocal,
      autoResume: cfg.autoResume,
      loadAndSeekProgress: d.loadAndSeekProgress,
      loadSpriteData: d.loadSpriteData,
      routerUpdate: d.routerUpdate,
    });
  };

  const playTrack = (index: number): void => {
    const s = getState();
    if (!s || index < 0 || index >= s.filteredItems.length) return;
    play(s.filteredItems[index] as PlayItemTrack, index);
  };

  return {
    /** Late-bind playNextItem (defined by catalogWiring wrapper in app scope). */
    setPlayNext(fn: () => void): void {
      callPlayNext = fn;
    },
    playItem: play,
    playTrack,
    refreshMetadata: refresh,
    togglePlay: (): void => togglePlay(transportHooks()),
    handlePreviousTrack: (): void => handlePreviousTrack(transportHooks()),
    startBgMirror: bgMirror,
    bgAudioIsActive,
    stopBgSync,
    activeMedia: (): HTMLMediaElement => activeMedia(player()),
    updateMediaSession: media,
    startCrossfade: (): void => startCrossfade(xfadeHooks()),
    finishCrossfade: (): void => finishCrossfade(xfadeHooks()),
  };
}

export type PlaybackWiring = ReturnType<typeof createPlaybackWiring>;
