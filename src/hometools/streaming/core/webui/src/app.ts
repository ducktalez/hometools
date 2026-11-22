import { applyLocalMutations, clearCatalogCache, loadCatalogCache, loadLastPlayedLocal, saveCatalogCache, saveLastPlayedLocal } from "./catalogCache";
import { readConfig } from "./config";
import { initBackgroundPlayback, wasPlaying } from "./bgPlayback";
import { bootstrapApp } from "./bootstrap";
import { cleanFolderName, renderBreadcrumb as renderBreadcrumbImpl } from "./breadcrumb";
import { loadInitialCatalog as loadInitialCatalogImpl } from "./catalogFetch";
import { itemsUnder as itemsUnderImpl } from "./catalogQuery";
import { createCatalogWiring } from "./catalogWiring";
import { TRACK_TABLE_HEADER_HTML } from "./chromeHtml";
import { getDom } from "./dom";
import { currentDupeIndex } from "./dupeState";
import { invalidateFolderCache } from "./folderCache";
import { contentsAt as contentsAtImpl } from "./folderContents";
import { initFolderGridEvents } from "./folderGridEvents";
import { createFolderWiring } from "./folderWiring";
import { escHtml, fmtTime, formatBytes } from "./format";
import { hideIndexingToast as hideIndexingToastImpl, showIndexingToast as showIndexingToastImpl } from "./indexingToast";
import { initIntroUi, updateSkipIntroBtn } from "./introUi";
import { compositeFlagHtml as compositeFlagHtmlImpl, langBadgesHtml as langBadgesHtmlImpl } from "./langDetect";
import { LANG_NAME_MAP } from "./langNames";
import { createLibraryWiring } from "./libraryWiring";
import { initLyricsPanel } from "./lyricsPanel";
import { renderBpmPill } from "./metricPill";
import { initModeButtons } from "./modeButtons";
import { initDownloadDB } from "./offlineDb";
import { revokeOfflineUrl } from "./offlineUrl";
import { initPip } from "./pip";
import { computeEffectiveThreshold, createPlaybackState } from "./playbackState";
import { createPlaybackWiring } from "./playbackWiring";
import { initBarFullscreen, initHeaderHome, initPlayerRatingEvents, showVideoOnLoad } from "./playerBarUi";
import { initPlayerEvents } from "./playerEvents";
import { initPlaylistModalEvents } from "./playlistModalEvents";
import { bindPlaylistSync } from "./playlistSync";
import { createPlaylistWiring } from "./playlistWiring";
import { clearProgressFor as clearProgressForImpl, getProgressPath, loadAndSeekProgress as loadAndSeekProgressImpl, saveProgressDebounced as saveProgressDebouncedImpl, saveProgressNow as saveProgressNowImpl } from "./progress";
import { initQueueController } from "./queueController";
import { createRouter } from "./router";
import { createSearchFilterWiring } from "./searchFilterWiring";
import { initSpritePreview, loadSpriteData as loadSpriteDataImpl } from "./spritePreview";
import { initSwipeGestures } from "./swipe";
import { initTabResume } from "./tabResume";
import { initTimeline } from "./timeline";
import { showToast } from "./toast";
import { initEditModalEvents, initToolbar } from "./toolbarUi";
import { isToolsPanelOpen } from "./toolsPanel";
import { createTrackRenderWiring } from "./trackRenderWiring";
import { applyFolderViewMode, applyTrackViewMode, isTrackViewVisible, toggleTrackViewMode } from "./trackViewMode";
import { initCastButton, initFullscreenButton } from "./videoButtons";
import { initVideoOverlay, openVideoOverlay as openVideoOverlayImpl, showVidControls, syncMiniBar } from "./videoOverlay";
import { catalogStateOpts } from "./viewEntry";
import { initViewState } from "./viewState";
import { generateWaveform as generateWaveformImpl, initWaveform } from "./waveform";

export function startApp(): void {
  var INITIAL = JSON.parse(document.getElementById('initial-data')!.textContent as string);
  var CFG = readConfig();
  var ICONS: Record<string, string> = CFG.icons || {};
  var ITEM_NOUN = CFG.itemNoun || 'track';
  var API_PATH = CFG.apiPath || '';
  function _apiBase(): any { return API_PATH.split('/').slice(0, -1).join('/'); }
  var OFFLINE_ENABLED = !!CFG.enableOffline;
  var FOLDER_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Cpath d='M30 45h25l7-10h28l0 0H90v40H30z' fill='%23444'/%3E%3C/svg%3E";
  var FILE_PLACEHOLDER  = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Ccircle cx='54' cy='72' r='12' fill='none' stroke='%23444' stroke-width='3'/%3E%3Crect x='63' y='38' width='3' height='34' fill='%23444'/%3E%3Crect x='57' y='38' width='12' height='4' rx='1' fill='%23444'/%3E%3C/svg%3E";
  var IC_PLAY = ICONS.PLAY;
  var IC_PAUSE = ICONS.PAUSE;
  var IC_DL = ICONS.DOWNLOAD;
  var IC_CHECK = ICONS.CHECK;
  var IC_FOLDER_PLAY = ICONS.FOLDER_PLAY;
  var IC_PIN = ICONS.PIN;
  var IC_STAR = ICONS.STAR;
  var IC_REPEAT = ICONS.REPEAT;
  var IC_REPEAT_ONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17,1 21,5 17,9"/><path d="M3,11V9a4,4,0,0,1,4-4h14"/><polyline points="7,23 3,19 7,15"/><path d="M21,13v2a4,4,0,0,1-4,4H3"/><text x="12" y="15.5" text-anchor="middle" fill="currentColor" stroke="none" font-size="7" font-weight="bold">1</text></svg>';
  var IC_STAR_FILLED = ICONS.STAR;
  var IC_STAR_EMPTY = ICONS.STAR_EMPTY;
  var IC_EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  var IC_FILTER = ICONS.FILTER;
  var SHUFFLE_ENABLED = !!CFG.enableShuffle;
  var REPEAT_ENABLED = !!CFG.enableRepeat;
  var SKIP_INTRO_ENABLED = !!CFG.enableSkipIntro;
  var INTRO_API_PATH = _apiBase() + '/intro';
  var RATING_WRITE_ENABLED = !!CFG.enableRatingWrite;
  var MIN_RATING_THRESHOLD = CFG.minRating || 0;
  var _effectiveThreshold = computeEffectiveThreshold(MIN_RATING_THRESHOLD, RATING_WRITE_ENABLED);
  var DEBUG_FILTER = !!CFG.debugFilter;
  var RATING_API_PATH = _apiBase() + '/rating';
  var AUDIT_UNDO_PATH = _apiBase() + '/audit/undo';
  var RECENT_ENABLED = !!CFG.enableRecent;
  var RECENT_API_PATH = _apiBase() + '/recent';
  var AUTO_RESUME_ENABLED = !!CFG.enableAutoResume;
  var CROSSFADE_DURATION = CFG.crossfadeDuration || 0;
  var METADATA_EDIT_ENABLED = !!CFG.enableMetadataEdit;
  var METADATA_EDIT_PATH = _apiBase() + '/metadata/edit';
  var IC_EDIT = ICONS.EDIT;
  var LYRICS_ENABLED = !!CFG.enableLyrics;
  var LYRICS_API_PATH = _apiBase() + '/lyrics';
  var PLAYLISTS_ENABLED = !!CFG.enablePlaylists;
  var PLAYLISTS_API_PATH = _apiBase() + '/playlists';
  var PLAYLISTS_VERSION_PATH = _apiBase() + '/playlists/version';
  var PLAYLISTS_SMART_PATH = _apiBase() + '/playlists/smart';
  var FOLDER_ORDER_API_PATH = _apiBase() + '/folder-order';
  var MOVE_API_PATH = _apiBase() + '/move-file';
  var DELETE_API_PATH = _apiBase() + '/delete-file';
  var REVEAL_API_PATH = _apiBase() + '/reveal';
  var IC_PLAYLIST = ICONS.PLAYLIST;
  var IC_SMART_PLAYLIST = ICONS.SMART_PLAYLIST;
  var IC_QUEUE = ICONS.QUEUE;
  var IC_REMOVE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  var IC_TRASH = ICONS.TRASH;
  var IC_DOTS = ICONS.DOTS;
  var IC_REFRESH = ICONS.REFRESH;
  var LANG_TO_FLAG: Record<string, string> = {
    de: ICONS.FLAG_DE,
    en: ICONS.FLAG_EN,
    fr: ICONS.FLAG_FR,
    es: ICONS.FLAG_ES,
    it: ICONS.FLAG_IT,
    ja: ICONS.FLAG_JA,
    ko: ICONS.FLAG_KO,
    zh: ICONS.FLAG_ZH,
    pt: ICONS.FLAG_PT,
    ru: ICONS.FLAG_RU,
  };
  var AUDIOBOOK_DIRS = CFG.audiobookDirs || [];
  var LANG_GROUPS = CFG.languageGroups || {};
  var DEFAULT_LANG = CFG.defaultLanguage || 'de';
  var BPM_MIN = CFG.bpmMin || 0;
  var BPM_MAX = CFG.bpmMax || 180;
  var BPM_CALC_API_PATH = _apiBase() + '/bpm/calculate';
  var BPM_ADJUST_API_PATH = _apiBase() + '/bpm/adjust';
  var BPM_SET_API_PATH = _apiBase() + '/bpm/set';
  var IC_CHEVRONS_DOWN = ICONS.CHEVRONS_DOWN;
  var IC_CHEVRONS_UP = ICONS.CHEVRONS_UP;

  function _saveCatalogCache(items: any): void { saveCatalogCache(items, API_PATH); }
  function _loadCatalogCache(): any { return loadCatalogCache(API_PATH); }
  function _clearCatalogCache(): void { clearCatalogCache(API_PATH); }
  function _saveLastPlayedLocal(rp: any, pos: any): void { saveLastPlayedLocal(rp, pos, API_PATH); }
  function _loadLastPlayedLocal(): any { return loadLastPlayedLocal(API_PATH); }
  function _applyLocalMutations(items?: any): any { return applyLocalMutations(items, _locallyDeletedPaths); }
  var _LANG_NAME_MAP = LANG_NAME_MAP;

  
  
  var _locallyDeletedPaths: Record<string, boolean> = {};

  

  
  var _pb = createPlaybackState(Array.isArray(INITIAL) ? INITIAL : []);
  window.htState = _pb;

  
  var _dom: Record<string, any> = getDom();
  var player       = _dom.player;
  var btnPlay      = _dom.btnPlay;
  var btnPrev      = _dom.btnPrev;
  var btnNext      = _dom.btnNext;
  var btnShuffle   = _dom.btnShuffle;
  var btnRepeat    = _dom.btnRepeat;
  var trackList    = _dom.trackList;
  var playerThumb  = _dom.playerThumb;
  var progressBar  = _dom.progressBar;
  var timeCur      = _dom.timeCur;
  var timeDur      = _dom.timeDur;
  var searchInput  = _dom.searchInput;
  var sortField    = _dom.sortField;
  var filterCombinedBtn = _dom.filterCombinedBtn;
  var filterHiddenBtn = _dom.filterHiddenBtn;
  
  var _view = initViewState(player.tagName === 'VIDEO');
  
  
  var folderGrid   = _dom.folderGrid;
  var trackView    = _dom.trackView;
  var backBtn      = _dom.backBtn;
  var logoHomeBtn  = _dom.logoHomeBtn;
  var headerTitle  = _dom.headerTitle;
  
  var videoOverlay   = _dom.videoOverlay;
  var videoMiniBar   = _dom.videoMiniBar;
  var miniTitle      = _dom.miniTitle;
  var miniArtist     = _dom.miniArtist;
  var miniThumb      = _dom.miniThumb;
  var miniPlayBtn    = _dom.miniPlayBtn;
  var miniExpandBtn  = _dom.miniExpandBtn;
  var videoCloseBtn  = _dom.videoCloseBtn;
  var videoFsBtn     = _dom.videoFsBtn;
  var videoCastBtn   = _dom.videoCastBtn;
  var videoSkipIntroBtn = _dom.videoSkipIntroBtn;
  var videoOverlayTitleText = _dom.videoOverlayTitleText;
  var videoFloatContainer = _dom.videoFloatContainer;
  var videoFloatWrap   = _dom.videoFloatWrap;
  var floatExpandBtn   = _dom.floatExpandBtn;
  var floatCloseBtn    = _dom.floatCloseBtn;
  var videoWrap        = _dom.videoWrap;
  
  var playAllBtn   = _dom.playAllBtn;
  var downloadedPill = _dom.downloadedPill;
  var originalTitle = headerTitle.textContent;
  
  window.originalTitle = originalTitle;
  var breadcrumb  = _dom.breadcrumb;
  var viewToggle  = _dom.viewToggle;

  
  var _RENDER_BATCH_SIZE  = 100;

  

  

  

  
  

  var progressTrack  = document.getElementById('progress-track');
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';


  
  initVideoOverlay({
    player: player, isVideoMode: isVideoMode,
    overlay: videoOverlay, miniBar: videoMiniBar,
    miniTitle: miniTitle, miniArtist: miniArtist, miniThumb: miniThumb,
    miniPlayBtn: miniPlayBtn, miniExpandBtn: miniExpandBtn,
    overlayTitleText: videoOverlayTitleText, videoWrap: videoWrap,
    floatContainer: videoFloatContainer, floatWrap: videoFloatWrap,
    floatCloseBtn: floatCloseBtn, floatExpandBtn: floatExpandBtn,
    closeBtn: videoCloseBtn, icPlay: IC_PLAY, icPause: IC_PAUSE
  });
  function openVideoOverlay(): any { openVideoOverlayImpl(); }
  function _showVidControls(): any { showVidControls(); }
  function _syncMiniBar(t?: any): any { syncMiniBar(t); }

  
  initTabResume({ player: player });

  
  initFullscreenButton({ button: videoFsBtn, overlay: videoOverlay, player: player });
  initCastButton({ button: videoCastBtn, player: player });
  
  
  initIntroUi({
    player: player, button: videoSkipIntroBtn,
    enabled: SKIP_INTRO_ENABLED, isVideoMode: isVideoMode,
    apiPath: INTRO_API_PATH,
    getProgressPath: function() { return getProgressPath(); },
    fmtTime: fmtTime, toast: function(m: any) { showToast(m); }
  });

  
  

  

  
  
  function _progHooks(): any {
    return {
      player: player, apiPath: API_PATH,
      saveLastPlayedLocal: _saveLastPlayedLocal, showToast: showToast, fmtTime: fmtTime
    };
  }
  function saveProgressNow(): any { saveProgressNowImpl(_progHooks()); }
  function saveProgressDebounced(): any { saveProgressDebouncedImpl(_progHooks()); }
  function clearProgressFor(rp?: any): any { clearProgressForImpl(rp, _progHooks()); }
  function loadAndSeekProgress(rp?: any): any { loadAndSeekProgressImpl(rp, _progHooks()); }
  
  function showIndexingToast(msg?: any, prog?: any): any { showIndexingToastImpl(msg, prog, escHtml); }
  function hideIndexingToast(): any { hideIndexingToastImpl(); }

  
  
  var _lyrics = initLyricsPanel({
    enabled: LYRICS_ENABLED, apiPath: LYRICS_API_PATH, escHtml: escHtml,
    getCurrentTrack: function() { return _pb.filteredItems[_pb.currentIndex] || _pb.playlistItems[_pb.currentIndex]; }
  });
  function openLyricsPanel(relativePath?: any, trackTitle?: any): any { _lyrics.open(relativePath, trackTitle); }
  function closeLyricsPanel(): any { _lyrics.close(); }

  
  var _queueCtl = initQueueController({
    itemNoun: ITEM_NOUN, filePlaceholder: FILE_PLACEHOLDER, icRemove: IC_REMOVE,
    esc: escHtml, toast: showToast,
    playItem: function(item: any, i: any) { playItem(item, i); },
    lyricsOpen: function() { return _lyrics.isOpen(); },
    closeLyrics: function() { closeLyricsPanel(); }
  });
  function addToQueue(item?: any): any { _queueCtl.add(item); }
  function removeFromQueue(index?: any): any { _queueCtl.remove(index); }
  function playFromQueue(index?: any): any { _queueCtl.playFrom(index); }
  function updateQueueButtons(): any { _queueCtl.updateButtons(); }

  
  
  var _cw = createCatalogWiring({
    apiPath: API_PATH, apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
    isVideo: ITEM_NOUN === 'video', ratingWriteEnabled: !!RATING_WRITE_ENABLED, icPlay: IC_PLAY
  }, function() {
    return {
      playFromQueue: playFromQueue, playTrack: playTrack,
      showIndexingToast: showIndexingToast, hideIndexingToast: hideIndexingToast,
      applyLocalMutations: _applyLocalMutations,
      invalidateDupeMap: _invalidateDupeMap, invalidateFolderCache: invalidateFolderCache,
      saveCatalogCache: _saveCatalogCache, clearCatalogCache: _clearCatalogCache,
      clearLocalDeleted: function() {
        Object.keys(_locallyDeletedPaths).forEach(function(k: any) { delete _locallyDeletedPaths[k]; });
      },
      showFolderView: showFolderView, itemsUnder: itemsUnder, applyFilter: applyFilter, toast: showToast
    };
  });
  function playNextItem(): any { _cw.playNextItem(); }
  function _triggerSilentRefresh(): any { _cw.triggerSilentRefresh(); }
  function refreshCatalog(): any { _cw.refreshCatalog(); }
  function addExtraFolder(): any { _cw.addExtraFolder(); }
  function removeExtraFolder(): any { _cw.removeExtraFolder(); }
  _cw.loadExtraFolders();

  
  initFolderGridEvents({
    folderGrid: folderGrid,
    refreshCatalog: refreshCatalog,
    addExtraFolder: addExtraFolder,
    removeExtraFolder: removeExtraFolder
  });
  function refreshFolderRatings(folderItems?: any): any { _cw.refreshFolderRatings(folderItems); }

  
  initWaveform({
    canvas: document.getElementById('waveform-canvas') as HTMLCanvasElement | null,
    isAudioMode: isAudioMode,
    apiPath: _apiBase() + '/waveform',
    currentFraction: function() { return player.duration > 0 ? player.currentTime / player.duration : 0; },
    resizeFraction: function() { return progressBar && progressBar.max > 0 ? progressBar.value / progressBar.max : 0; }
  });
  function generateWaveform(url?: any, relativePath?: any): any { generateWaveformImpl(url, relativePath); }

  
  initSpritePreview({
    player: player, isVideoMode: isVideoMode,
    track: progressTrack,
    preview: document.getElementById('thumb-preview'),
    canvas: document.getElementById('thumb-canvas') as HTMLCanvasElement | null,
    timeEl: document.getElementById('thumb-time'),
    fmtTime: fmtTime
  });
  function loadSpriteData(relativePath?: any): any { loadSpriteDataImpl(relativePath); }


  
  function itemsUnder(path?: any): any {
    return itemsUnderImpl(path, _pb.allItems);
  }

  

  

  

  
  function langBadgesHtml(langs?: any): any {
    return langBadgesHtmlImpl(langs, LANG_TO_FLAG);
  }

  function compositeFlagHtml(mainLang?: any, subLang?: any): any {
    return compositeFlagHtmlImpl(mainLang, subLang, LANG_TO_FLAG);
  }

  
  function contentsAt(path?: any): any {
    return contentsAtImpl(path, _pb.allItems, LANG_GROUPS);
  }

  

  
  function showLoadingState(message?: any): any {
    _enterFolderGridView(catalogStateOpts('loading', message, escHtml));
  }

  function showCatalogLoadError(detail?: any): any {
    _enterFolderGridView(catalogStateOpts('error', detail, escHtml));
  }

  
  function loadInitialCatalog(): any {
    return loadInitialCatalogImpl(Object.assign({}, _cw.fetchHooks(), {
      loadCache: function() { return _loadCatalogCache(); },
      showLoadingState: function(m: any) { showLoadingState(m); },
      showCatalogLoadError: function(m: any) { showCatalogLoadError(m); },
      autoRefreshOn: function() { return ((_toolFlags() && _toolFlags().autoRefresh) || 'auto') !== 'off'; }
    }));
  }
  
  function renderBreadcrumb(): any {
    renderBreadcrumbImpl({
      breadcrumb: breadcrumb, headerTitle: headerTitle, escHtml: escHtml,
      showFolderView: function() { showFolderView(); }
    });
  }

  
  var IC_GRID = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
  var IC_LIST = '<svg viewBox="0 0 24 24"><circle cx="4" cy="6" r="1.6" fill="currentColor"/><circle cx="4" cy="12" r="1.6" fill="currentColor"/><circle cx="4" cy="18" r="1.6" fill="currentColor"/><line x1="9" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_TABLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="1"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/><line x1="15" y1="10" x2="15" y2="20"/></svg>';
  
  function _trackViewHooks(): any {
    return {
      trackList: trackList, trackView: trackView, viewToggle: viewToggle,
      isVideoMode: isVideoMode, tableHeaderHtml: TRACK_TABLE_HEADER_HTML,
      icList: IC_LIST, icTable: IC_TABLE,
      getMode: function() { return _view.trackViewMode; },
      setMode: function(m: any) { _view.trackViewMode = m; },
      rerender: function() { renderTracks(_pb.playlistItems.length ? _pb.playlistItems : _pb.filteredItems, true); }
    };
  }
  function _toggleTrackViewMode(): any { toggleTrackViewMode(_trackViewHooks()); }
  function _applyTrackViewMode(): any { applyTrackViewMode(_trackViewHooks()); }
  function _isTrackViewVisible(): any { return isTrackViewVisible(trackView); }
  function applyViewMode(): any {
    if (_isTrackViewVisible()) {
      
      _applyTrackViewMode();
      return;
    }
    applyFolderViewMode({
      folderGrid: folderGrid, viewToggle: viewToggle, icList: IC_LIST, icGrid: IC_GRID,
      toolActive: _anyToolActive(), viewMode: _view.viewMode
    });
  }

  

  
  var _fw = createFolderWiring({
    itemNoun: ITEM_NOUN, defaultLang: DEFAULT_LANG,
    playlistsEnabled: !!PLAYLISTS_ENABLED, offlineEnabled: !!OFFLINE_ENABLED, recentEnabled: !!RECENT_ENABLED,
    playlistsApiPath: PLAYLISTS_API_PATH, recentApiPath: RECENT_API_PATH,
    icons: {
      smartPlaylist: IC_SMART_PLAYLIST, playlist: IC_PLAYLIST, dl: IC_DL, refresh: IC_REFRESH,
      star: IC_STAR, folderPlay: IC_FOLDER_PLAY, dots: IC_DOTS, edit: IC_EDIT, trash: IC_TRASH
    },
    audiobookDirs: AUDIOBOOK_DIRS, langNames: _LANG_NAME_MAP, langToFlag: LANG_TO_FLAG,
    folderPlaceholder: FOLDER_PLACEHOLDER, filePlaceholder: FILE_PLACEHOLDER,
    originalTitle: originalTitle
  }, function() {
    return {
      esc: escHtml, toast: showToast, toolActive: _anyToolActive, contentsAt: contentsAt,
      loadRecentlyPlayed: loadRecentlyPlayed, openOfflineLibrary: openOfflineLibrary,
      updateOfflineFolderCount: updateOfflineFolderCount, triggerSilentRefresh: _triggerSilentRefresh,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop,
      showUserPlaylistView: showUserPlaylistView, playUserPlaylist: playUserPlaylist,
      openSmartPlaylistEditor: openSmartPlaylistEditor, refreshSmartPlaylist: refreshSmartPlaylist,
      renameUserPlaylist: renameUserPlaylist, deleteUserPlaylist: deleteUserPlaylist,
      loadLastPlayedLocal: _loadLastPlayedLocal,
      sortByFolderOrder: _sortByFolderOrder, refreshFolderRatings: refreshFolderRatings,
      playTrack: playTrack, loadFolderOrderAsync: _loadFolderOrderAsync, loadFolderOrder: _loadFolderOrder,
      applyFilter: applyFilter, applyViewMode: applyViewMode, renderBreadcrumb: renderBreadcrumb,
      routerUpdate: function() { if (_router) _router.update(); },
      exitGlobalSearch: exitGlobalSearch, globalSearch: globalSearch,
      cleanFolderName: cleanFolderName, markActive: markActive, fmtTime: fmtTime,
      viewMode: function() { return _view.viewMode; },
      compositeFlagHtml: compositeFlagHtml, langBadgesHtml: langBadgesHtml
    };
  });
  function showFolderView(): any { _fw.showFolderView(); }
  function _enterTrackListView(opts?: any): any { _fw.enterTrackListView(opts); }
  function _enterFolderGridView(opts?: any): any { _fw.enterFolderGridView(opts); }
  function showPlaylist(items?: any, autoplay?: any, startIdx?: any): any { _fw.showPlaylist(items, autoplay, startIdx); }
  function goBack(): any { _fw.goBack(); }

  
  var _sfw = createSearchFilterWiring({
    itemNoun: ITEM_NOUN, filePlaceholder: FILE_PLACEHOLDER,
    icons: {
      folderPlay: IC_FOLDER_PLAY, filter: IC_FILTER, eye: IC_EYE,
      starFilled: IC_STAR_FILLED, starEmpty: IC_STAR_EMPTY,
      trash: IC_TRASH, dl: IC_DL, pin: IC_PIN, edit: IC_EDIT,
      playlist: IC_PLAYLIST, queue: IC_QUEUE, dots: IC_DOTS
    },
    debugFilter: DEBUG_FILTER, batchSize: _RENDER_BATCH_SIZE, isVideoMode: isVideoMode,
    metadataEditEnabled: !!METADATA_EDIT_ENABLED, playlistsEnabled: !!PLAYLISTS_ENABLED,
    metadataEditPath: METADATA_EDIT_PATH, bpmMin: BPM_MIN, bpmMax: BPM_MAX
  }, function() {
    return {
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return _view.showHidden; },
      viewMode: function() { return _view.viewMode; },
      trackViewMode: function() { return _view.trackViewMode; },
      getFilter: function() { return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre }; },
      setFilter: function(p: any) {
        if (p.rating !== undefined) _view.filterRating = p.rating;
        if (p.fav !== undefined) _view.filterFav = p.fav;
        if (p.genre !== undefined) _view.filterGenre = p.genre;
      },
      locallyDeleted: function() { return _locallyDeletedPaths; },
      esc: escHtml, fmtTime: fmtTime, toast: showToast,
      anyToolActive: _anyToolActive, toolFlags: _toolFlags,
      currentDupeIndex: function() { return currentDupeIndex(); },
      renderBpmPill: renderBpmPill, renderInlineRating: renderInlineRating, renderMoveWidget: renderMoveWidget,
      showFolderView: showFolderView, showPlaylist: showPlaylist, enterTrackListView: _enterTrackListView,
      playItem: playItem, contentsAt: contentsAt, itemsUnder: itemsUnder, renderTracks: renderTracks,
      updateFavoriteButtons: updateFavoriteButtons, updateAllDownloadButtons: updateAllDownloadButtons,
      updateQueueButtons: updateQueueButtons, initPlaylistDragDrop: initPlaylistDragDrop,
      renderFilterPopoverBody: _renderFilterPopoverBody,
      routerUpdate: function() { if (_router) _router.update(); },
      getAllFolders: _getAllFolders, moveFileToFolder: moveFileToFolder,
      deleteTrackFromList: _deleteTrackFromList, openTrackCtxMenu: _openTrackCtxMenu,
      setInlineRating: setInlineRating, openBpmAdjustMenu: _openBpmAdjustMenu,
      deleteTrackDownload: deleteTrackDownload, cancelDownload: cancelDownload,
      downloadTrack: downloadTrack, toggleFavorite: toggleFavorite, openEditModal: openEditModal,
      loadUserPlaylists: loadUserPlaylists, openPlaylistModal: openPlaylistModal,
      removeFromQueue: removeFromQueue, addToQueue: addToQueue,
      revealInExplorer: _revealInExplorer, playTrack: playTrack
    };
  });
  function globalSearch(needle?: any): any { _sfw.globalSearch(needle); }
  function exitGlobalSearch(): any { _sfw.exitGlobalSearch(); }
  function playAllCurrent(): any { _sfw.playAllCurrent(); }
  function updateFilterChips(): any { _sfw.updateFilterChips(); }
  function applyFilter(force?: any): any { _sfw.applyFilter(force); }
  function _renderFilterPopoverBody(): any { _sfw.renderFilterPopoverBody(); }
  function _toggleFilterPopover(btn?: any): any { _sfw.toggleFilterPopover(btn); }
  function _stopRenderObserver(): any { _sfw.stopRenderObserver(); }
  function markActive(): any { _sfw.markActive(); }
  function _startWindowedRender(realTracks?: any): any { _sfw.startWindowedRender(realTracks); }
  function jumpToCurrentTrack(): any { _sfw.jumpToCurrentTrack(); }
  function updatePlayerBarActions(): any { _sfw.updatePlayerBarActions(); }
  

  
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var _trw = createTrackRenderWiring({
    itemNoun: ITEM_NOUN, debugFilter: DEBUG_FILTER, softLimit: OFFLINE_SOFT_LIMIT,
    recentApiPath: RECENT_API_PATH, filePlaceholder: FILE_PLACEHOLDER,
    ratingWriteEnabled: !!RATING_WRITE_ENABLED,
    icDl: IC_DL, icCheck: IC_CHECK, icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY,
    icChevronsDown: IC_CHEVRONS_DOWN, icRefresh: IC_REFRESH, icChevronsUp: IC_CHEVRONS_UP,
    bpmCalcApiPath: BPM_CALC_API_PATH, bpmAdjustApiPath: BPM_ADJUST_API_PATH, bpmSetApiPath: BPM_SET_API_PATH,
    bpmMin: BPM_MIN, bpmMax: BPM_MAX
  }, function() {
    return {
      esc: escHtml, toast: showToast, formatBytes: formatBytes,
      getFilter: function() { return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre }; },
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return _view.showHidden; },
      stopRenderObserver: _stopRenderObserver, startWindowedRender: _startWindowedRender,
      markActive: markActive, openTrackPicker: openTrackPicker,
      applyFilter: applyFilter, showFolderView: showFolderView, showPlaylist: showPlaylist,
      playItem: playItem, enterTrackListView: _enterTrackListView,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop, applyViewMode: applyViewMode,
      updatePlayerBarActions: updatePlayerBarActions, invalidateDupeMap: _invalidateDupeMap,
      refreshCatalog: refreshCatalog, playDuplicates: playDuplicates, closeDupePanel: closeDupePanel,
      routerUpdate: function() { if (_router) _router.update(); }
    };
  });
  function renderTracks(tracks?: any, force?: any): any { _trw.renderTracks(tracks, force); }
  function cancelDownload(streamUrl?: any, btn?: any): any { _trw.cancelDownload(streamUrl, btn); }
  function refreshOfflineLibrary(): any { return _trw.refreshOfflineLibrary(); }
  function openOfflineLibrary(): any { _trw.openOfflineLibrary(); }
  function updateOfflineFolderCount(): any { _trw.updateOfflineFolderCount(); }
  function loadRecentlyPlayed(): any { _trw.loadRecentlyPlayed(); }
  function updateAllDownloadButtons(): any { _trw.updateAllDownloadButtons(); }
  function downloadTrack(streamUrl?: any, title?: any, btn?: any, meta?: any): any { _trw.downloadTrack(streamUrl, title, btn, meta); }
  function deleteTrackDownload(streamUrl?: any, btn?: any): any { _trw.deleteTrackDownload(streamUrl, btn); }
  function playOfflineOrStream(streamUrl?: any): any { return _trw.playOfflineOrStream(streamUrl); }
  function _anyToolActive(): any { return _trw.anyToolActive(); }
  function _toolFlags(): any { return _trw.toolFlags(); }
  function openToolsPanel(): any { _trw.openToolsPanel(); }
  _trw.start();
  function renderInlineRating(t?: any, idx?: any): any { return _trw.renderInlineRating(t, idx); }
  
  function setInlineRating(idx?: any, stars?: any): any { _lw.setInlineRating(idx, stars); }
  function _openBpmAdjustMenu(idx?: any, btnEl?: any): any { _trw.openBpmAdjustMenu(idx, btnEl); }

  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';

  
  var _lw = createLibraryWiring({
    filePlaceholder: FILE_PLACEHOLDER, deleteApiPath: DELETE_API_PATH, moveApiPath: MOVE_API_PATH,
    revealApiPath: REVEAL_API_PATH, ratingApiPath: RATING_API_PATH, auditUndoPath: AUDIT_UNDO_PATH,
    folderOrderApiPath: FOLDER_ORDER_API_PATH, apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
    ratingWriteEnabled: !!RATING_WRITE_ENABLED, metadataEditEnabled: !!METADATA_EDIT_ENABLED,
    metadataEditPath: METADATA_EDIT_PATH, icPlay: IC_PLAY, icDuplicate: IC_DUPLICATE, icTrash: IC_TRASH,
    icFolderOpen: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY
  }, function() {
    return {
      esc: escHtml, toast: showToast, applyFilter: applyFilter, markActive: markActive,
      showFolderView: showFolderView, showPlaylist: showPlaylist, playTrack: playTrack, itemsUnder: itemsUnder,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop, enterTrackListView: _enterTrackListView,
      saveCatalogCache: _saveCatalogCache, isManualPlaylistView: _isManualPlaylistView,
      removeFromUserPlaylist: removeFromUserPlaylist,
      filterFavActive: function() { return !!_view.filterFav; }
    };
  });
  function _invalidateDupeMap(): any { _lw.invalidateDupeMap(); }
  function closeDupePanel(): any { _lw.closeDupePanel(); }
  function playDuplicates(): any { _lw.playDuplicates(); }
  function _removeGoneTrack(relativePath?: any): any { _lw.removeGoneTrack(relativePath); }
  function _deleteTrackFromList(filteredIdx?: any): any { _lw.deleteTrackFromList(filteredIdx); }
  function _getAllFolders(): any { return _lw.getAllFolders(); }
  function renderMoveWidget(t?: any, idx?: any): any { return _lw.renderMoveWidget(t, idx); }
  function moveFileToFolder(idx?: any, targetFolder?: any): any { _lw.moveFileToFolder(idx, targetFolder); }
  function _openTrackCtxMenu(btn?: any, relativePath?: any, title?: any): any { _lw.openTrackCtxMenu(btn, relativePath, title); }
  function _revealInExplorer(relativePath?: any): any { _lw.revealInExplorer(relativePath); }

  
  
  var isVideoPlayer = player.tagName === 'VIDEO';
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  
  initPip({
    player: player, button: document.getElementById('btn-pip'),
    isVideoPlayer: isVideoPlayer, isIOS: isIOS,
    wasPlaying: function() { return wasPlaying(); }
  });

  
  initBackgroundPlayback({ player: player, isVideoPlayer: isVideoPlayer, isIOS: isIOS });

  
  initBarFullscreen(player, isVideoPlayer);

  
  var _pbw = createPlaybackWiring({
    apiPath: API_PATH, itemNoun: ITEM_NOUN, isVideoMode: isVideoMode, isVideoPlayer: isVideoPlayer,
    icPause: IC_PAUSE, icPlay: IC_PLAY, filePlaceholder: FILE_PLACEHOLDER,
    autoResume: AUTO_RESUME_ENABLED, lyricsEnabled: !!LYRICS_ENABLED, crossfadeDuration: CROSSFADE_DURATION
  }, function() {
    return {
      revokeOfflineUrl: revokeOfflineUrl, generateWaveform: generateWaveform,
      playOfflineOrStream: playOfflineOrStream, openVideoOverlay: openVideoOverlay, syncMiniBar: _syncMiniBar,
      markActive: markActive, renderPlayerRating: renderPlayerRating,
      updatePlayerBarActions: updatePlayerBarActions,
      isLyricsOpen: function() { return _lyrics.isOpen(); },
      openLyricsPanel: openLyricsPanel,
      saveProgressNow: saveProgressNow, clearProgressFor: clearProgressFor,
      saveLastPlayedLocal: _saveLastPlayedLocal, loadAndSeekProgress: loadAndSeekProgress,
      loadSpriteData: loadSpriteData,
      routerUpdate: function() { if (_router) _router.update(); },
      applyFilter: applyFilter, playFromQueue: playFromQueue
    };
  });
  _pbw.setPlayNext(function() { playNextItem(); });
  function playItem(t?: any, index?: any): any { _pbw.playItem(t, index); }
  function playTrack(index?: any): any { _pbw.playTrack(index); }
  function togglePlay(): any { _pbw.togglePlay(); }
  function handlePreviousTrack(): any { _pbw.handlePreviousTrack(); }

    
  
  
  function renderPlayerRating(stars?: any): any { _lw.renderPlayerRating(stars); }
  function setRating(stars?: any): any { _lw.setRating(stars); }
  
  initPlayerRatingEvents({
    writeEnabled: !!RATING_WRITE_ENABLED,
    currentRating: function() { return (_pb.filteredItems[_pb.currentIndex] && _pb.filteredItems[_pb.currentIndex].rating) || 0; },
    setRating: setRating
  });

  initModeButtons({
    btnShuffle: btnShuffle, btnRepeat: btnRepeat,
    shuffleEnabled: !!SHUFFLE_ENABLED, repeatEnabled: !!REPEAT_ENABLED,
    icRepeat: IC_REPEAT, icRepeatOne: IC_REPEAT_ONE, showToast: showToast
  });
  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', handlePreviousTrack);
  btnNext.addEventListener('click', playNextItem);
  
  if (playerThumb) playerThumb.addEventListener('click', jumpToCurrentTrack);

  function _startCrossfade(): any { _pbw.startCrossfade(); }
  function _finishCrossfade(): any { _pbw.finishCrossfade(); }
  
  initPlayerEvents({
    player: player, btnPlay: btnPlay, icPlay: IC_PLAY, icPause: IC_PAUSE, isVideoMode: isVideoMode,
    showVidControls: function() { _showVidControls(); },
    saveProgressNow: saveProgressNow,
    clearProgressFor: clearProgressFor,
    finishCrossfade: _finishCrossfade,
    playNextItem: playNextItem,
    currentStreamUrl: function() { return _pb.currentStreamUrl; },
    removeGoneTrack: _removeGoneTrack,
    showToast: showToast
  });
  
  initTimeline({
    player: player, progressBar: progressBar, timeCur: timeCur, timeDur: timeDur,
    track: progressTrack, isVideoPlayer: isVideoPlayer, crossfadeDuration: CROSSFADE_DURATION,
    fmtTime: fmtTime,
    getItemDuration: function() { return _pb.itemDuration; },
    setItemDuration: function(d: any) { _pb.itemDuration = d; },
    saveProgressNow: saveProgressNow, saveProgressDebounced: saveProgressDebounced,
    updateSkipIntroBtn: function() { updateSkipIntroBtn(); },
    startCrossfade: _startCrossfade
  });
  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);

  
  
  initHeaderHome(logoHomeBtn, {
    setRoot: function() { _pb.currentPath = ''; },
    showFolderView: showFolderView
  });
  showVideoOnLoad(player, isVideoPlayer);

  
  function loadFavorites(): any { _lw.loadFavorites(); }
  function updateFavoriteButtons(): any { _lw.updateFavoriteButtons(); }
  function toggleFavorite(item?: any, btn?: any): any { _lw.toggleFavorite(item, btn); }
  _lw.initEditModalRatingEvents();
  function openEditModal(idx?: any): any { _lw.openEditModal(idx); }
  function closeEditModal(): any { _lw.closeEditModal(); }
  function submitEditModal(): any { _lw.submitEditModal(); }


  

  
  initToolbar({
    viewToggle: viewToggle, searchInput: searchInput, sortField: sortField,
    filterCombinedBtn: filterCombinedBtn, filterHiddenBtn: filterHiddenBtn,
    isVideoMode: isVideoMode,
    isTrackViewVisible: _isTrackViewVisible, toggleTrackViewMode: _toggleTrackViewMode,
    anyToolActive: _anyToolActive,
    getViewMode: function() { return _view.viewMode; },
    setViewMode: function(m: any) { _view.viewMode = m; },
    getShowHidden: function() { return _view.showHidden; },
    setShowHidden: function(v: any) { _view.showHidden = v; },
    applyViewMode: applyViewMode, applyFilter: applyFilter, showFolderView: showFolderView,
    toggleFilterPopover: _toggleFilterPopover, updateFilterChips: updateFilterChips,
    routerUpdate: function() { if (_router) _router.update(); }
  });

  
  
  initEditModalEvents({ enabled: !!METADATA_EDIT_ENABLED, close: closeEditModal, submit: submitEditModal });

  if (!OFFLINE_ENABLED) {
    if (downloadedPill) {
      downloadedPill.textContent = 'Safe Mode';
      downloadedPill.classList.add('is-offline');
    }
  } else if (typeof indexedDB !== 'undefined') {
    initDownloadDB().catch(function(err: any) {
      console.warn('IndexedDB not available:', err);
    }).then(function() {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    });
  } else {
    refreshOfflineLibrary();
  }
  applyViewMode();

  
  var _router = createRouter({
    getUi: function() {
      return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre, showHidden: _view.showHidden, viewMode: _view.viewMode };
    },
    setUi: function(p: any) {
      if (p.rating !== undefined) _view.filterRating = p.rating;
      if (p.fav !== undefined) _view.filterFav = p.fav;
      if (p.genre !== undefined) _view.filterGenre = p.genre;
      if (p.showHidden !== undefined) _view.showHidden = p.showHidden;
      if (p.viewMode !== undefined) _view.viewMode = p.viewMode;
    },
    toolsOpen: function() { return isToolsPanelOpen(); },
    openToolsPanel: function() { openToolsPanel(); },
    contentsAt: contentsAt, itemsUnder: itemsUnder,
    showPlaylist: showPlaylist, showFolderView: showFolderView,
    showUserPlaylistView: showUserPlaylistView, openOfflineLibrary: openOfflineLibrary,
    globalSearch: globalSearch, markActive: markActive, updateFilterChips: updateFilterChips
  });

  

  
  function _loadFavoritesOrder(): any { return _lw.loadFavoritesOrder(); }
  function _saveFavoritesOrder(paths?: any): any { _lw.saveFavoritesOrder(paths); }
  function _loadFavoritesOrderAsync(cb?: any): any { _lw.loadFavoritesOrderAsync(cb); }
  function _sortFavoritesByOrder(favItems?: any): any { return _lw.sortFavoritesByOrder(favItems); }
  function _loadFolderOrder(folderPath?: any): any { return _lw.loadFolderOrder(folderPath); }
  function _saveFolderOrder(folderPath?: any, paths?: any): any { _lw.saveFolderOrder(folderPath, paths); }
  function _loadFolderOrderAsync(folderPath?: any, cb?: any): any { _lw.loadFolderOrderAsync(folderPath, cb); }
  function _sortByFolderOrder(folderPath?: any, items?: any): any { return _lw.sortByFolderOrder(folderPath, items); }
  var _PLAYLIST_SYNC_INTERVAL = CFG.playlistSyncIntervalMs || 30000; 

      
    var _plSync = bindPlaylistSync({
      enabled: PLAYLISTS_ENABLED,
      apiPath: PLAYLISTS_API_PATH,
      versionPath: PLAYLISTS_VERSION_PATH,
      intervalMs: _PLAYLIST_SYNC_INTERVAL
    }, function() { showFolderView(); });
    function loadUserPlaylists(): any { return _plSync.load(); }
    function _startPlaylistSync(): any { _plSync.start(); }

  
  


  
  var _plw = createPlaylistWiring({
    apiPath: PLAYLISTS_API_PATH,
    smartPath: PLAYLISTS_SMART_PATH,
    smartIcon: IC_SMART_PLAYLIST
  }, function() {
    return {
      toast: showToast,
      esc: escHtml,
      showFolderView: showFolderView,
      applyFilter: applyFilter,
      enterTrackListView: _enterTrackListView,
      playTrack: playTrack,
      sortFavoritesByOrder: _sortFavoritesByOrder,
      loadFavoritesOrder: _loadFavoritesOrder,
      loadFavoritesOrderAsync: _loadFavoritesOrderAsync,
      saveFavoritesOrder: _saveFavoritesOrder,
      saveFolderOrder: _saveFolderOrder,
      renderTracks: renderTracks
    };
  });
  function openSmartPlaylistEditor(existingPl?: any): any { _plw.openSmartPlaylistEditor(existingPl); }
  function refreshSmartPlaylist(plId?: any): any { _plw.refreshSmartPlaylist(plId); }
  function showUserPlaylistView(plId?: any): any { _plw.showUserPlaylistView(plId); }
  function playUserPlaylist(plId?: any): any { _plw.playUserPlaylist(plId); }
  function openPlaylistModal(relativePath?: any): any { _plw.openPlaylistModal(relativePath); }
  function closePlaylistModal(): any { _plw.closePlaylistModal(); }
  function openTrackPicker(plId?: any): any { _plw.openTrackPicker(plId); }
  function deleteUserPlaylist(plId?: any): any { _plw.deleteUserPlaylist(plId); }
  function renameUserPlaylist(plId?: any): any { _plw.renameUserPlaylist(plId); }
  function createAndAddToPlaylist(name?: any, relativePath?: any): any { _plw.createAndAddToPlaylist(name, relativePath); }
  function _isManualPlaylistView(): any { return _plw.isManualPlaylistView(); }
  function removeFromUserPlaylist(relativePath?: any): any { _plw.removeFromUserPlaylist(relativePath); }
  function initPlaylistDragDrop(): any { _plw.initPlaylistDragDrop(); }
  function destroyPlaylistDragDrop(): any { if (_plw) _plw.destroyPlaylistDragDrop(); } 

      
  
  initPlaylistModalEvents({
    enabled: !!PLAYLISTS_ENABLED,
    closeModal: closePlaylistModal,
    createAndAdd: createAndAddToPlaylist
  });

  
  initSwipeGestures({ goBack: goBack });

  
  bootstrapApp({
    loadInitialCatalog: loadInitialCatalog,
    routerInit: function() { _router.init(); },
    loadFavorites: loadFavorites,
    loadUserPlaylists: loadUserPlaylists,
    routerRestore: function() { _router.restore(); },
    showFolderView: showFolderView,
    startPlaylistSync: _startPlaylistSync
  });
}
