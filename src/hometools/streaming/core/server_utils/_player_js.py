"""Player JavaScript generation for the streaming UI."""

from __future__ import annotations

from ._svg import (  # noqa: F401
    SVG_BACK,
    SVG_CHECK,
    SVG_CLOSE_X,
    SVG_DOWNLOAD,
    SVG_DUPLICATE,
    SVG_EDIT,
    SVG_EXPAND,
    SVG_FLAG_DE,
    SVG_FLAG_EN,
    SVG_FLAG_ES,
    SVG_FLAG_FR,
    SVG_FLAG_IT,
    SVG_FLAG_JA,
    SVG_FLAG_KO,
    SVG_FLAG_PT,
    SVG_FLAG_RU,
    SVG_FLAG_ZH,
    SVG_FOLDER_PLAY,
    SVG_FULLSCREEN,
    SVG_HISTORY,
    SVG_LYRICS,
    SVG_MENU,
    SVG_MOVE,
    SVG_NEXT,
    SVG_PAUSE,
    SVG_PIN,
    SVG_PIP,
    SVG_PLAY,
    SVG_PLAYLIST,
    SVG_PREV,
    SVG_QUEUE,
    SVG_REFRESH,
    SVG_REPEAT,
    SVG_SHUFFLE,
    SVG_STAR,
    SVG_STAR_EMPTY,
    SVG_TRASH,
)


def render_player_js(
    api_path: str,
    item_noun: str = "track",
    file_emoji: str = "\U0001f3b5",
    player_bar_style: str = "classic",
    enable_offline: bool = True,
    enable_shuffle: bool = False,
    enable_repeat: bool = False,
    enable_rating_write: bool = False,
    enable_metadata_edit: bool = False,
    enable_recent: bool = True,
    enable_lyrics: bool = False,
    enable_playlists: bool = False,
    playlist_sync_interval_ms: int = 30000,
    min_rating: int = 0,
    enable_auto_resume: bool = True,
    crossfade_duration: int = 0,
    debug_filter: bool = False,
    language_groups_json: str = "{}",
    default_language: str = "de",
) -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).
    Clicking a folder navigates deeper into the hierarchy.  Leaf folders
    (no sub-folders) are displayed as playlists.  A breadcrumb trail and
    back button allow navigating up.  View preference is stored in
    localStorage.

    *enable_shuffle* activates the shuffle button in the player bar.
    Long-pressing the shuffle button activates weighted shuffle (items with
    higher ratings are more likely to play).  Works with offline downloads too.
    """
    # -- waveform/thumbnail JS (only for waveform mode) -----------------------
    if player_bar_style == "waveform":
        waveform_js = """
  /* ── waveform & thumbnail elements ── */
  var progressTrack  = document.getElementById('progress-track');
  var waveformCanvas = document.getElementById('waveform-canvas');
  var waveformCtx    = waveformCanvas ? waveformCanvas.getContext('2d') : null;
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
  var waveformData   = null;
  var waveformAbort  = null;
"""
    else:
        waveform_js = """
  var progressTrack  = document.getElementById('progress-track');
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
"""

    # -- sprite sheet preview (always available for video, both modes) ----------
    sprite_preview_js = """
  /* ── sprite sheet preview (video scrubber thumbnails) ── */
  var thumbPreview   = document.getElementById('thumb-preview');
  var thumbCanvas    = document.getElementById('thumb-canvas');
  var thumbCtx       = thumbCanvas ? thumbCanvas.getContext('2d') : null;
  var thumbTimeEl    = document.getElementById('thumb-time');
  var spriteData     = null;
  var spriteImg      = null;

  function loadSpriteData(relativePath) {
    spriteData = null;
    spriteImg = null;
    if (!isVideoMode || !relativePath) return;
    fetch('/api/video/sprites?path=' + encodeURIComponent(relativePath))
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta || !meta.cols) return;
        spriteData = meta;
        var img = new Image();
        img.onload = function() { spriteImg = img; };
        img.src = '/thumb?path=' + encodeURIComponent(relativePath) + '&size=sprite';
      })
      .catch(function() {});
  }

  if (isVideoMode && progressTrack) {
    progressTrack.addEventListener('mousemove', function(e) {
      if (!spriteData || !spriteImg || !player.duration || !isFinite(player.duration)) return;
      var rect = progressTrack.getBoundingClientRect();
      var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      var seekTime = ratio * player.duration;
      var pctLeft = Math.max(5, Math.min(95, ratio * 100));
      thumbPreview.style.left = pctLeft + '%';
      thumbPreview.classList.add('visible');
      thumbTimeEl.textContent = fmtTime(seekTime);
      var idx = Math.min(Math.floor(seekTime / spriteData.interval), spriteData.count - 1);
      var col = idx % spriteData.cols;
      var row = Math.floor(idx / spriteData.cols);
      if (thumbCtx) {
        thumbCanvas.width = spriteData.frame_w;
        thumbCanvas.height = spriteData.frame_h;
        thumbCtx.drawImage(spriteImg,
          col * spriteData.frame_w, row * spriteData.frame_h,
          spriteData.frame_w, spriteData.frame_h,
          0, 0, spriteData.frame_w, spriteData.frame_h);
      }
    });
    progressTrack.addEventListener('mouseleave', function() {
      thumbPreview.classList.remove('visible');
    });
  }
"""

    if player_bar_style == "waveform":
        waveform_setup_js = """
  /* ── waveform (audio) & video mode setup ── */
  if (isVideoMode && progressTrack) {
    progressTrack.classList.add('video-mode');
  }

  function generateWaveform(url) {
    if (!isAudioMode || !waveformCanvas) return;
    if (waveformAbort) waveformAbort.abort();
    waveformAbort = new AbortController();
    waveformData = null;
    drawWaveform(0);
    fetch(url, { signal: waveformAbort.signal })
      .then(function(r) { return r.arrayBuffer(); })
      .then(function(buf) {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        return audioCtx.decodeAudioData(buf).then(function(decoded) {
          audioCtx.close();
          return decoded;
        });
      })
      .then(function(audioBuffer) {
        var rawData = audioBuffer.getChannelData(0);
        var samples = 120;
        var blockSize = Math.floor(rawData.length / samples);
        if (blockSize < 1) return;
        var data = [];
        for (var i = 0; i < samples; i++) {
          var sum = 0;
          for (var j = 0; j < blockSize; j++) sum += Math.abs(rawData[i * blockSize + j]);
          data.push(sum / blockSize);
        }
        var max = Math.max.apply(null, data);
        if (max > 0) data = data.map(function(d) { return d / max; });
        waveformData = data;
        var prog = player.duration > 0 ? player.currentTime / player.duration : 0;
        drawWaveform(prog);
      })
      .catch(function(e) {
        if (e.name !== 'AbortError') waveformData = null;
      });
  }

  function drawWaveform(progress) {
    if (!waveformCanvas || !waveformCtx) return;
    var W = 600, H = 48;
    waveformCanvas.width = W;
    waveformCanvas.height = H;
    waveformCtx.clearRect(0, 0, W, H);
    var accent = getComputedStyle(document.documentElement)
      .getPropertyValue('--accent').trim() || '#1db954';
    if (isAudioMode && waveformData && waveformData.length) {
      var BAR_COUNT = 120;
      var slotW = W / BAR_COUNT;
      var gapW = slotW * 0.15;
      var barW = slotW - gapW;
      var playedBars = Math.floor(progress * BAR_COUNT);
      for (var i = 0; i < BAR_COUNT; i++) {
        var di = Math.min(Math.floor(i * waveformData.length / BAR_COUNT), waveformData.length - 1);
        var bh = Math.max(2, waveformData[di] * H * 0.85);
        var x = i * slotW, y = (H - bh) / 2;
        waveformCtx.fillStyle = i < playedBars ? accent : '#555';
        waveformCtx.fillRect(x, y, barW, bh);
      }
    } else {
      var barH = 6, cy = H / 2, ty = cy - barH / 2;
      var playedW = W * progress;
      waveformCtx.fillStyle = '#555';
      waveformCtx.fillRect(0, ty, W, barH);
      if (playedW > 0) {
        waveformCtx.fillStyle = accent;
        waveformCtx.fillRect(0, ty, playedW, barH);
      }
      waveformCtx.fillStyle = '#fff';
      waveformCtx.beginPath();
      waveformCtx.arc(Math.max(7, Math.min(W - 7, playedW)), cy, 7, 0, Math.PI * 2);
      waveformCtx.fill();
    }
  }
"""
    else:
        waveform_setup_js = """
  function generateWaveform() {}
  function drawWaveform() {}
"""

    return (
        """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  var ITEM_NOUN = '"""
        + item_noun
        + """';
  var FILE_EMOJI = '"""
        + file_emoji
        + """';
  var API_PATH = '"""
        + api_path
        + """';
  var OFFLINE_ENABLED = """
        + ("true" if enable_offline else "false")
        + """;

  /* Placeholder SVG thumbnails — same dimensions as real thumbs so layout never shifts.
     Simple dark-grey squares with a subtle icon silhouette. */
  var FOLDER_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Cpath d='M30 45h25l7-10h28l0 0H90v40H30z' fill='%23444'/%3E%3C/svg%3E";
  var FILE_PLACEHOLDER  = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Ccircle cx='54' cy='72' r='12' fill='none' stroke='%23444' stroke-width='3'/%3E%3Crect x='63' y='38' width='3' height='34' fill='%23444'/%3E%3Crect x='57' y='38' width='12' height='4' rx='1' fill='%23444'/%3E%3C/svg%3E";

  /* SVG icons for play/pause — cross-platform, no emoji rendering */
  var IC_PLAY  = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>';
  var IC_PAUSE = '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>';
  var IC_DL    = '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 19h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_CHECK = '<svg viewBox="0 0 24 24"><polyline points="4,12 10,18 20,6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_FOLDER_PLAY = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>';
  var IC_PIN = '<svg viewBox="0 0 24 24"><path d="M16 4l4 4-2.5 2.5 1.5 5.5-6-6-5 5v-2l3.5-3.5L6 4h2l5 1.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_STAR = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>';
  var IC_SHUFFLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16,3 21,3 21,8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21,16 21,21 16,21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>';
  var IC_REPEAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17,1 21,5 17,9"/><path d="M3,11V9a4,4,0,0,1,4-4h14"/><polyline points="7,23 3,19 7,15"/><path d="M21,13v2a4,4,0,0,1-4,4H3"/></svg>';
  var IC_REPEAT_ONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17,1 21,5 17,9"/><path d="M3,11V9a4,4,0,0,1,4-4h14"/><polyline points="7,23 3,19 7,15"/><path d="M21,13v2a4,4,0,0,1-4,4H3"/><text x="12" y="15.5" text-anchor="middle" fill="currentColor" stroke="none" font-size="7" font-weight="bold">1</text></svg>';
  var IC_STAR_FILLED = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>';
  var IC_STAR_EMPTY  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>';
  var IC_EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  var IC_EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  var SHUFFLE_ENABLED = """
        + ("true" if enable_shuffle else "false")
        + """;
  var REPEAT_ENABLED = """
        + ("true" if enable_repeat else "false")
        + """;
  var RATING_WRITE_ENABLED = """
        + ("true" if enable_rating_write else "false")
        + """;
  var MIN_RATING_THRESHOLD = """
        + str(min_rating)
        + """;
  /* When ratings are enabled but no explicit threshold is configured,
     treat 1-star tracks as "ausgeblendet" (threshold=2, used with < comparison: r < 2 hides 1★).
     Setting min_rating=0 explicitly disables the feature entirely. */
  var _effectiveThreshold = MIN_RATING_THRESHOLD > 0 ? MIN_RATING_THRESHOLD : (RATING_WRITE_ENABLED ? 2 : 0);
  var DEBUG_FILTER = """
        + ("true" if debug_filter else "false")
        + """;
  var RATING_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/rating';
  var AUDIT_UNDO_PATH = '"""
        + api_path.rsplit("/", 1)[0].replace("/api/", "/api/")
        + """/audit/undo';
  var RECENT_ENABLED = """
        + ("true" if enable_recent else "false")
        + """;
  var RECENT_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/recent';
  var AUTO_RESUME_ENABLED = """
        + ("true" if enable_auto_resume else "false")
        + """;
  var CROSSFADE_DURATION = """
        + str(crossfade_duration)
        + """;
  var METADATA_EDIT_ENABLED = """
        + ("true" if enable_metadata_edit else "false")
        + """;
  var METADATA_EDIT_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/metadata/edit';
  var IC_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  var IC_LYRICS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>';
  var LYRICS_ENABLED = """
        + ("true" if enable_lyrics else "false")
        + """;
  var LYRICS_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/lyrics';
  var PLAYLISTS_ENABLED = """
        + ("true" if enable_playlists else "false")
        + """;
  var PLAYLISTS_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/playlists';
  var PLAYLISTS_VERSION_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/playlists/version';
  var FOLDER_ORDER_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/folder-order';
  var MOVE_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/move-file';
  var DELETE_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/delete-file';
  var FOLDERS_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/folders';
  var IC_PLAYLIST = '"""
        + SVG_PLAYLIST.replace("'", "\\'")
        + """';
  var IC_QUEUE = '"""
        + SVG_QUEUE.replace("'", "\\'")
        + """';
  var IC_REMOVE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  var IC_TRASH = '"""
        + SVG_TRASH.replace("'", "\\'")
        + """';
  var IC_REFRESH = '"""
        + SVG_REFRESH.replace("'", "\\'")
        + """';
  var LANG_TO_FLAG = {
    'de': '"""
        + SVG_FLAG_DE.replace("'", "\\'")
        + """',
    'en': '"""
        + SVG_FLAG_EN.replace("'", "\\'")
        + """',
    'fr': '"""
        + SVG_FLAG_FR.replace("'", "\\'")
        + """',
    'es': '"""
        + SVG_FLAG_ES.replace("'", "\\'")
        + """',
    'it': '"""
        + SVG_FLAG_IT.replace("'", "\\'")
        + """',
    'ja': '"""
        + SVG_FLAG_JA.replace("'", "\\'")
        + """',
    'ko': '"""
        + SVG_FLAG_KO.replace("'", "\\'")
        + """',
    'zh': '"""
        + SVG_FLAG_ZH.replace("'", "\\'")
        + """',
    'pt': '"""
        + SVG_FLAG_PT.replace("'", "\\'")
        + """',
    'ru': '"""
        + SVG_FLAG_RU.replace("'", "\\'")
        + """'
  };
  var AUDIOBOOK_DIRS = """
        + __import__("json").dumps(__import__("hometools.config", fromlist=["get_audiobook_dirs"]).get_audiobook_dirs())
        + """;
  var LANG_GROUPS = """
        + language_groups_json
        + """;
  var DEFAULT_LANG = '"""
        + default_language
        + """';
  var _LANG_NAME_MAP = {
    'de': 'Deutsch', 'en': 'English', 'fr': 'Fran\u00e7ais', 'es': 'Espa\u00f1ol',
    'it': 'Italiano', 'ja': '\u65e5\u672c\u8a9e', 'ko': '\ud55c\uad6d\uc5b4',
    'zh': '\u4e2d\u6587', 'pt': 'Portugu\u00eas', 'ru': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439'
  };

  var allItems = Array.isArray(INITIAL) ? INITIAL : [];
  var currentPath = '';
  var playlistItems = [];
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;
  var initialCatalogRetryTimer = null;
  var initialCatalogRetryCount = 0;
  /* ── Shuffle state ── */
  var shuffleMode = false;       /* false = off, 'normal' = random, 'weighted' = rating-weighted */
  var repeatMode  = false;       /* false = off, 'all' = repeat playlist, 'one' = repeat single track */
  var shuffleQueue = [];         /* pre-built queue of indices for current session */
  var shufflePos = -1;           /* current position within shuffleQueue */

  /* ── Queue (Warteschlange) state ── */
  var _userQueue = [];           /* Array of item objects {title, artist, stream_url, relative_path, thumbnail_url, ...} */
  var _queueOpen = false;
  var _queueDndCleanup = null;

  var player       = document.getElementById('player');
  var btnPlay      = document.getElementById('btn-play');
  var btnPrev      = document.getElementById('btn-prev');
  var btnNext      = document.getElementById('btn-next');
  var btnShuffle   = document.getElementById('btn-shuffle');
  var btnRepeat    = document.getElementById('btn-repeat');
  var trackList    = document.getElementById('track-list');
  var trackCount   = document.getElementById('track-count');
  var playerTitle  = document.getElementById('player-title');
  var playerArtist = document.getElementById('player-artist');
  var playerThumb  = document.getElementById('player-thumb');
  var progressBar  = document.getElementById('progress-bar');
  var timeCur      = document.getElementById('time-cur');
  var timeDur      = document.getElementById('time-dur');
  var searchInput  = document.getElementById('search-input');
  var sortField    = document.getElementById('sort-field');
  var filterRatingBtn = document.getElementById('filter-rating');
  var filterFavBtn    = document.getElementById('filter-fav');
  var filterGenreBtn  = document.getElementById('filter-genre');
  var filterHiddenBtn = document.getElementById('filter-hidden');
  /* Persisted quick-filter state */
  var filterRating = parseInt(localStorage.getItem('ht-filter-rating') || '0', 10) || 0;
  var filterFav    = localStorage.getItem('ht-filter-fav') === '1';
  var filterGenre  = localStorage.getItem('ht-filter-genre') || '';
  var showHidden   = localStorage.getItem('ht-show-hidden') !== '0'; /* default true = ausgeblendet werden ausgegraut angezeigt */
  var folderGrid   = document.getElementById('folder-grid');
  var folderFilterBar = document.getElementById('folder-filter-bar');
  var trackView    = document.getElementById('track-view');
  var filterBar    = document.querySelector('.filter-bar');
  var backBtn      = document.getElementById('back-btn');
  /* Global search state */
  var _globalSearchActive = false;
  var logoHomeBtn  = document.getElementById('header-logo');
  var headerTitle  = document.getElementById('header-title');
  var playerBar    = document.querySelector('.player-bar');
  /* ── Video overlay (video-mode only) ── */
  var videoOverlay   = document.getElementById('video-overlay');
  var videoMiniBar   = document.getElementById('video-mini-bar');
  var miniTitle      = document.getElementById('mini-title');
  var miniArtist     = document.getElementById('mini-artist');
  var miniThumb      = document.getElementById('mini-thumb');
  var miniPlayBtn    = document.getElementById('mini-play-btn');
  var miniExpandBtn  = document.getElementById('mini-expand-btn');
  var videoCloseBtn  = document.getElementById('video-close-btn');
  var videoFsBtn     = document.getElementById('video-fs-btn');
  var videoOverlayTitleText = document.getElementById('video-overlay-title-text');
  var videoFloatContainer = document.getElementById('video-float-container');
  var videoFloatWrap   = document.getElementById('video-float-wrap');
  var floatExpandBtn   = document.getElementById('float-expand-btn');
  var floatCloseBtn    = document.getElementById('float-close-btn');
  var videoWrap        = document.querySelector('.video-wrap');
  /* In video-mode the overlay controls visibility; playerBar points to
     the .player-bar INSIDE the overlay, so existing classList calls work
     on the inner controls and the overlay is managed separately. */
  var playAllBtn   = document.getElementById('play-all-btn');
  var offlineLibrary = document.getElementById('offline-library');
  var offlineClose = document.getElementById('offline-close');
  var offlineSort  = document.getElementById('offline-sort');
  var offlinePersistBtn = document.getElementById('offline-persist-btn');
  var offlinePruneBtn = document.getElementById('offline-prune-btn');
  var offlineDownloadList = document.getElementById('offline-download-list');
  var offlineStorageSummary = document.getElementById('offline-storage-summary');
  var offlineStorageDetail = document.getElementById('offline-storage-detail');
  var downloadedPill = document.getElementById('downloaded-pill');
  var originalTitle = headerTitle.textContent;
  var breadcrumb  = document.getElementById('breadcrumb');
  var viewToggle  = document.getElementById('view-toggle');
  var _savedViewMode = localStorage.getItem('ht-view-mode');
  var viewMode    = (_savedViewMode === 'list' || _savedViewMode === 'grid') ? _savedViewMode : 'list';
  var currentStreamUrl = '';
  var currentOfflineUrl = null;
"""
        + waveform_js
        + """

  /* ── Video overlay helpers (no-op in audio mode) ── */
  var _isFloating = false;

  function _fixOverlaySize() {
    /* iOS Safari clips position:fixed inside body{overflow:hidden} to the flex
       container height. Setting an explicit pixel height via JS is the only
       reliable cross-browser fix. */
    if (!videoOverlay) return;
    var h = window.innerHeight;
    videoOverlay.style.height = h + 'px';
    videoOverlay.style.width  = window.innerWidth + 'px';
  }
  if (isVideoMode) {
    window.addEventListener('resize', _fixOverlaySize);
    _fixOverlaySize();
  }

  function openVideoOverlay() {
    if (!videoOverlay) return;
    _isFloating = false;
    _fixOverlaySize(); /* ensure pixel-perfect height before showing */
    videoOverlay.classList.remove('view-hidden');
    if (videoMiniBar) videoMiniBar.hidden = true;
    if (videoFloatContainer) videoFloatContainer.classList.remove('active');
    /* Move <video> back to overlay if it was in float container */
    if (videoWrap && player.parentNode !== videoWrap) videoWrap.appendChild(player);
    player.style.display = 'block';
  }
  function closeVideoOverlay() {
    if (!videoOverlay) return;
    videoOverlay.classList.add('view-hidden');
    /* Show mini-bar only when a video source is loaded */
    if (videoMiniBar) videoMiniBar.hidden = !player.currentSrc;
  }
  function enterFloatPlayer() {
    /* Move <video> to float container and show it without closing the overlay completely */
    if (!videoFloatContainer || !videoFloatWrap || !isVideoMode) return;
    if (_isFloating) return; /* already floating */
    _isFloating = true;
    videoOverlay.classList.add('view-hidden');
    if (videoMiniBar) videoMiniBar.hidden = true;
    /* Move <video> into float wrap */
    videoFloatWrap.appendChild(player);
    player.style.display = 'block';
    videoFloatContainer.classList.add('active');
    /* Reset position to default bottom-right */
    videoFloatContainer.style.bottom = '80px';
    videoFloatContainer.style.right = '16px';
    videoFloatContainer.style.left = '';
    videoFloatContainer.style.top = '';
  }
  function exitFloatPlayer() {
    if (!_isFloating) return;
    _isFloating = false;
    videoFloatContainer.classList.remove('active');
    /* Move <video> back to overlay */
    if (videoWrap) videoWrap.appendChild(player);
    player.style.display = 'block';
    openVideoOverlay();
  }
  function _syncMiniBar(t) {
    if (!videoMiniBar) return;
    if (miniTitle)  miniTitle.textContent  = t.title  || '';
    if (miniArtist) miniArtist.textContent = t.artist || '';
    if (miniThumb) {
      var src = t.thumbnail_lg_url || t.thumbnail_url || '';
      miniThumb.src = src;
      miniThumb.style.display = src ? '' : 'none';
    }
    if (videoOverlayTitleText) videoOverlayTitleText.textContent = t.title || '';
  }
  function _syncMiniPlayBtn() {
    if (!miniPlayBtn) return;
    miniPlayBtn.innerHTML = player.paused ? IC_PLAY : IC_PAUSE;
  }

  /* ── Background-tab resume ──────────────────────────────────────────────
     Chrome (and other browsers) can pause media when a tab becomes hidden.
     We track whether the player was running before hide and resume it when
     the tab becomes visible again. Works for both audio and video mode.     */
  var _wasPlayingBeforeHide = false;
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      _wasPlayingBeforeHide = !player.paused;
    } else {
      if (_wasPlayingBeforeHide && player.paused) {
        player.play().catch(function() {});
      }
    }
  });

  if (videoCloseBtn) {
    videoCloseBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeVideoOverlay();
    });
  }
  if (miniExpandBtn) {
    miniExpandBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      openVideoOverlay();
    });
  }
  if (videoMiniBar) {
    videoMiniBar.addEventListener('click', function(e) {
      /* Clicking the bar (not its buttons) reopens the overlay */
      if (e.target === miniPlayBtn || miniPlayBtn && miniPlayBtn.contains(e.target)) return;
      if (e.target === miniExpandBtn || miniExpandBtn && miniExpandBtn.contains(e.target)) return;
      openVideoOverlay();
    });
  }
  if (miniPlayBtn) {
    miniPlayBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      if (player.paused) { player.play(); } else { player.pause(); }
    });
  }

  /* ── Fullscreen button — uses requestFullscreen on the OVERLAY div ── */
  if (videoFsBtn) {
    videoFsBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var target = videoOverlay || player;
      if (document.fullscreenEnabled && target.requestFullscreen) {
        target.requestFullscreen().catch(function() {
          /* fallback: iOS webkitEnterFullscreen on video element */
          if (player.webkitEnterFullscreen) player.webkitEnterFullscreen();
        });
      } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
      } else if (player.webkitEnterFullscreen) {
        player.webkitEnterFullscreen(); /* iOS Safari */
      }
    });
  }

  /* ── Fullscreen exit → float player ── */
  function _handleFullscreenChange() {
    var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    if (!fsEl && !videoOverlay.classList.contains('view-hidden') && player.currentSrc) {
      /* Exited native fullscreen (Escape / browser UI) while overlay was visible */
      enterFloatPlayer();
    }
  }
  document.addEventListener('fullscreenchange', _handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', _handleFullscreenChange);

  /* ── Escape key in overlay → float player ── */
  document.addEventListener('keydown', function(e) {
    if (!isVideoMode) return;
    if (e.key !== 'Escape') return;
    /* Escape while overlay is open (and not in native fullscreen) → float */
    if (!videoOverlay.classList.contains('view-hidden') && !document.fullscreenElement) {
      enterFloatPlayer();
    }
  });

  /* ── Float player: close and expand buttons ── */
  if (floatCloseBtn) {
    floatCloseBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      player.pause();
      videoFloatContainer.classList.remove('active');
      _isFloating = false;
      /* Move <video> back to overlay (hidden) */
      if (videoWrap) videoWrap.appendChild(player);
    });
  }
  if (floatExpandBtn) {
    floatExpandBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      exitFloatPlayer();
    });
  }

  /* ── Float player: drag to reposition ── */
  if (videoFloatContainer && isVideoMode) {
    (function _initFloatDrag() {
      var _dragging = false;
      var _startX = 0, _startY = 0;
      var _origLeft = 0, _origTop = 0;

      function _getControlled(e) {
        /* Don't start drag if clicking a button */
        var t = e.target;
        while (t && t !== videoFloatContainer) {
          if (t.tagName === 'BUTTON') return false;
          t = t.parentNode;
        }
        return true;
      }
      function _onDown(e) {
        if (!videoFloatContainer.classList.contains('active')) return;
        if (!_getControlled(e)) return;
        _dragging = true;
        var rect = videoFloatContainer.getBoundingClientRect();
        var cx = e.touches ? e.touches[0].clientX : e.clientX;
        var cy = e.touches ? e.touches[0].clientY : e.clientY;
        _startX = cx - rect.left;
        _startY = cy - rect.top;
        videoFloatContainer.classList.add('dragging');
        /* Switch to left/top positioning */
        videoFloatContainer.style.right = '';
        videoFloatContainer.style.bottom = '';
        videoFloatContainer.style.left = rect.left + 'px';
        videoFloatContainer.style.top  = rect.top  + 'px';
        e.preventDefault();
      }
      function _onMove(e) {
        if (!_dragging) return;
        var cx = e.touches ? e.touches[0].clientX : e.clientX;
        var cy = e.touches ? e.touches[0].clientY : e.clientY;
        var newLeft = cx - _startX;
        var newTop  = cy - _startY;
        var maxL = window.innerWidth  - videoFloatContainer.offsetWidth;
        var maxT = window.innerHeight - videoFloatContainer.offsetHeight;
        newLeft = Math.max(0, Math.min(newLeft, maxL));
        newTop  = Math.max(0, Math.min(newTop, maxT));
        videoFloatContainer.style.left = newLeft + 'px';
        videoFloatContainer.style.top  = newTop  + 'px';
        e.preventDefault();
      }
      function _onUp() {
        if (!_dragging) return;
        _dragging = false;
        videoFloatContainer.classList.remove('dragging');
      }
      videoFloatContainer.addEventListener('mousedown',  _onDown, {passive: false});
      videoFloatContainer.addEventListener('touchstart', _onDown, {passive: false});
      document.addEventListener('mousemove',  _onMove, {passive: false});
      document.addEventListener('touchmove',  _onMove, {passive: false});
      document.addEventListener('mouseup',  _onUp);
      document.addEventListener('touchend', _onUp);
    })();
  }

  /* Toggle play/pause by clicking the video area */
  if (isVideoMode) {
    var _videoWrap = document.querySelector('.video-wrap');
    if (_videoWrap) {
      _videoWrap.addEventListener('click', function() {
        if (player.paused) { player.play(); } else { player.pause(); }
      });
    }
  }
  /* Keep mini-bar play button icon in sync */
  player.addEventListener('play',  _syncMiniPlayBtn);
  player.addEventListener('pause', _syncMiniPlayBtn);

  /* ── helpers ── */
  function fmtTime(s) {
    if (!isFinite(s)) return '0:00';
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    var sec = String(Math.floor(s % 60)).padStart(2, '0');
    return h > 0 ? h + ':' + String(m).padStart(2, '0') + ':' + sec : m + ':' + sec;
  }
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function formatBytes(b) {
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
    if (b < 1073741824) return (b / 1048576).toFixed(1) + ' MB';
    return (b / 1073741824).toFixed(2) + ' GB';
  }
  var _toastEl = null;
  var _toastTimer = 0;
  function showToast(msg, durationMs) {
    if (!_toastEl) {
      _toastEl = document.createElement('div');
      _toastEl.className = 'ht-toast';
      document.body.appendChild(_toastEl);
    }
    _toastEl.textContent = msg;
    _toastEl.classList.add('visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function() { _toastEl.classList.remove('visible'); }, durationMs || 4000);
  }

  /* ── click-distance guard: suppress clicks when the mouse moved ── */
  var _mdX = 0, _mdY = 0;
  var CLICK_MOVE_THRESHOLD = 6; /* pixels */
  document.addEventListener('mousedown', function(e) { _mdX = e.clientX; _mdY = e.clientY; }, true);
  document.addEventListener('touchstart', function(e) {
    if (e.touches.length === 1) { _mdX = e.touches[0].clientX; _mdY = e.touches[0].clientY; }
  }, { passive: true, capture: true });
  function wasDrag(e) {
    var dx = Math.abs(e.clientX - _mdX);
    var dy = Math.abs(e.clientY - _mdY);
    return dx > CLICK_MOVE_THRESHOLD || dy > CLICK_MOVE_THRESHOLD;
  }

  /* ── playback progress persistence ── */
  var _progressTimer = 0;
  var _progressRelPath = '';
  function _progressApiBase() {
    return API_PATH.substring(0, API_PATH.lastIndexOf('/')) + '/progress';
  }
  function saveProgressNow() {
    var rp = _progressRelPath;
    if (!rp) return;
    var pos = player.currentTime;
    var dur = player.duration;
    if (!isFinite(pos) || !isFinite(dur)) return;
    if (pos < 5 || pos > dur - 5) return;
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({relative_path: rp, position_seconds: pos, duration: dur})
    }).catch(function() {});
  }
  function saveProgressDebounced() {
    clearTimeout(_progressTimer);
    _progressTimer = setTimeout(saveProgressNow, 5000);
  }
  function clearProgressFor(rp) {
    if (!rp) return;
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({relative_path: rp, position_seconds: 0, duration: 0})
    }).catch(function() {});
  }
  function loadAndSeekProgress(rp) {
    if (!rp) return;
    fetch(_progressApiBase() + '?path=' + encodeURIComponent(rp))
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        if (!data || !data.items || !data.items.length) return;
        var entry = data.items[0];
        var pos = entry.position_seconds || 0;
        if (pos < 5) return;
        function doSeek() {
          if (isFinite(player.duration) && pos < player.duration - 5) {
            player.currentTime = pos;
            showToast('Fortfahren bei ' + fmtTime(pos), 3000);
          }
        }
        if (isFinite(player.duration) && player.duration > 0) {
          doSeek();
        } else {
          player.addEventListener('loadedmetadata', doSeek, { once: true });
        }
      })
      .catch(function() {});
  }

  var _indexToastEl = null;
  var _indexRefreshTimer = null;
  function showIndexingToast(msg) {
    if (!_indexToastEl) {
      _indexToastEl = document.createElement('div');
      _indexToastEl.className = 'ht-indexing-toast';
      document.body.appendChild(_indexToastEl);
    }
    _indexToastEl.innerHTML = '<span class="spinner"></span>' + escHtml(msg || 'Indexing…');
    _indexToastEl.classList.add('visible');
  }
  function hideIndexingToast() {
    if (_indexToastEl) _indexToastEl.classList.remove('visible');
    if (_indexRefreshTimer) { clearTimeout(_indexRefreshTimer); _indexRefreshTimer = null; }
  }

  /* ── Lyrics panel ── */
  var _lyricsBtn   = document.getElementById('btn-lyrics');
  var _lyricsPanel = document.getElementById('lyrics-panel');
  var _lyricsBody  = document.getElementById('lyrics-body');
  var _lyricsClose = document.getElementById('lyrics-close-btn');
  var _lyricsCache = {};   /* relative_path → lyrics text or '' */
  var _lyricsOpen  = false;

  function openLyricsPanel(relativePath, trackTitle) {
    if (!LYRICS_ENABLED || !_lyricsPanel) return;
    _lyricsOpen = true;
    _lyricsPanel.classList.add('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext schlie\u00dfen';

    /* Serve from cache if available */
    if (relativePath in _lyricsCache) {
      _renderLyrics(_lyricsCache[relativePath], trackTitle);
      return;
    }
    if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-loading">Lade Songtext\u2026</div>';
    fetch(LYRICS_API_PATH + '?path=' + encodeURIComponent(relativePath), { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        var text = (d && d.lyrics) ? d.lyrics : '';
        _lyricsCache[relativePath] = text;
        if (_lyricsOpen) _renderLyrics(text, trackTitle);
      })
      .catch(function() {
        if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-empty">Songtext konnte nicht geladen werden.</div>';
      });
  }

  function _renderLyrics(text, trackTitle) {
    if (!_lyricsBody) return;
    if (text) {
      _lyricsBody.innerHTML = '<div class="lyrics-text">' + escHtml(text) + '</div>';
      if (_lyricsBtn) _lyricsBtn.classList.add('has-lyrics');
    } else {
      _lyricsBody.innerHTML = '<div class="lyrics-empty">Kein Songtext f\u00fcr \u201e' + escHtml(trackTitle || 'diesen Titel') + '\u201c hinterlegt.</div>';
      if (_lyricsBtn) _lyricsBtn.classList.remove('has-lyrics');
    }
  }

  function closeLyricsPanel() {
    _lyricsOpen = false;
    if (_lyricsPanel) _lyricsPanel.classList.remove('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext anzeigen';
  }

  if (_lyricsBtn) {
    _lyricsBtn.addEventListener('click', function() {
      if (_lyricsOpen) {
        closeLyricsPanel();
      } else {
        /* Find the currently playing track */
        var t = filteredItems[currentIndex] || playlistItems[currentIndex];
        if (t) openLyricsPanel(t.relative_path, t.title);
      }
    });
  }
  if (_lyricsClose) {
    _lyricsClose.addEventListener('click', closeLyricsPanel);
  }

  if (_lyricsClose) {
    _lyricsClose.addEventListener('click', closeLyricsPanel);
  }

  /* ── Queue (Warteschlange) panel ── */
  var _queueBtn   = document.getElementById('btn-queue');
  var _queuePanel = document.getElementById('queue-panel');
  var _queueBody  = document.getElementById('queue-body');
  var _queueClose = document.getElementById('queue-close-btn');
  var _queueBadge = document.getElementById('queue-badge');
  var _queueClearBtn = document.getElementById('queue-clear-btn');
  var _queueDragHandle = document.getElementById('queue-drag-handle');
  var _queueUserHeight = null; /* user-chosen height in px, null = auto */
  var _QUEUE_HEIGHT_KEY = 'hometools_queue_height';
  var _QUEUE_MIN_H = 220; /* head ~57px + at least 3 items à 53px */
  /* Restore saved height preference (enforce minimum) */
  try {
    var _sh = localStorage.getItem(_QUEUE_HEIGHT_KEY);
    if (_sh) { var _sv = parseInt(_sh, 10); _queueUserHeight = (_sv >= _QUEUE_MIN_H) ? _sv : null; }
  } catch(e) {}

  /** Re-query queue DOM refs — called before every render to guard against
   *  stale references (e.g. if the player-bar was not yet visible at init). */
  function _domNodeMissingOrDetached(el) {
    return !el || !el.isConnected;
  }

  function _ensureQueueDom() {
    if (_domNodeMissingOrDetached(_queuePanel)) _queuePanel = document.getElementById('queue-panel');
    if (_domNodeMissingOrDetached(_queueBody)) _queueBody = document.getElementById('queue-body');
    if (_domNodeMissingOrDetached(_queueBadge)) _queueBadge = document.getElementById('queue-badge');
    if (_domNodeMissingOrDetached(_queueClearBtn)) _queueClearBtn = document.getElementById('queue-clear-btn');
    if (_domNodeMissingOrDetached(_queueBtn)) _queueBtn = document.getElementById('btn-queue');
    if (_domNodeMissingOrDetached(_queueClose)) _queueClose = document.getElementById('queue-close-btn');
    if (_domNodeMissingOrDetached(_queueDragHandle)) _queueDragHandle = document.getElementById('queue-drag-handle');
  }

  function addToQueue(item) {
    _ensureQueueDom();
    if (!item || !item.relative_path) return;
    /* Prevent duplicates */
    var exists = _userQueue.some(function(q) { return q.relative_path === item.relative_path; });
    if (exists) {
      showToast('Bereits in der Warteschlange');
      return;
    }
    _userQueue.push({
      title: item.title || '',
      artist: item.artist || '',
      stream_url: item.stream_url || '',
      relative_path: item.relative_path || '',
      thumbnail_url: item.thumbnail_url || '',
      thumbnail_lg_url: item.thumbnail_lg_url || '',
      rating: item.rating || 0,
      media_type: item.media_type || ITEM_NOUN
    });
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
    showToast('\u201e' + escHtml(item.title || 'Titel') + '\u201c zur Warteschlange hinzugef\u00fcgt');
  }

  function removeFromQueue(index) {
    if (index < 0 || index >= _userQueue.length) return;
    _userQueue.splice(index, 1);
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
  }

  function clearQueue() {
    _userQueue = [];
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
  }

  function updateQueueBadge() {
    if (!_queueBadge) return;
    _queueBadge.textContent = _userQueue.length > 0 ? String(_userQueue.length) : '';
  }

  function updateQueueButtons() {
    /* Update .track-queue-btn states in track list */
    document.querySelectorAll('.track-queue-btn').forEach(function(btn) {
      var rp = btn.dataset.relativePath;
      var inQ = _userQueue.some(function(q) { return q.relative_path === rp; });
      btn.classList.toggle('in-queue', inQ);
      btn.title = inQ ? 'Aus Warteschlange entfernen' : 'Zur Warteschlange hinzuf\u00fcgen';
    });
  }

  function renderQueuePanel() {
    if (!_queueBody) return;
    if (_userQueue.length === 0) {
      _queueBody.innerHTML = '<div class="queue-empty">Die Warteschlange ist leer.</div>';
      if (_queueClearBtn) _queueClearBtn.style.display = 'none';
      return;
    }
    if (_queueClearBtn) _queueClearBtn.style.display = '';
    var html = '<ul class="queue-list" id="queue-list">';
    _userQueue.forEach(function(item, idx) {
      var thumbSrc = item.thumbnail_url || FILE_PLACEHOLDER;
      html += '<li class="queue-item" data-queue-index="' + idx + '">' +
        '<img class="queue-item-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="queue-item-info">' +
          '<div class="queue-item-title">' + escHtml(item.title) + '</div>' +
          '<div class="queue-item-artist">' + escHtml(item.artist || item.relative_path) + '</div>' +
        '</div>' +
        '<button class="queue-item-remove" data-queue-index="' + idx + '" title="Entfernen">' + IC_REMOVE + '</button>' +
        '</li>';
    });
    html += '</ul>';
    _queueBody.innerHTML = html;
    /* Wire up click handlers */
    _queueBody.querySelectorAll('.queue-item').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (e.target.closest('.queue-item-remove')) return;
        var qi = Number(el.dataset.queueIndex);
        playFromQueue(qi);
      });
    });
    _queueBody.querySelectorAll('.queue-item-remove').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        removeFromQueue(Number(btn.dataset.queueIndex));
      });
    });
    initQueueDragDrop();
  }

  function playFromQueue(index) {
    if (index < 0 || index >= _userQueue.length) return;
    var item = _userQueue[index];
    /* Remove played item from queue */
    _userQueue.splice(index, 1);
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
    /* Play via playItem — find in filteredItems for correct index, or play directly */
    var fiIdx = filteredItems.findIndex(function(fi) { return fi.relative_path === item.relative_path; });
    if (fiIdx >= 0) {
      playItem(filteredItems[fiIdx], fiIdx);
    } else {
      playItem(item, -1);
    }
  }

  /** Dequeue next item from queue — returns true if an item was played */
  function dequeueNext() {
    if (_userQueue.length === 0) return false;
    playFromQueue(0);
    return true;
  }

  function playNextItem() {
    if (repeatMode === 'one') {
      /* Repeat single: restart the current track */
      player.currentTime = 0;
      player.play().catch(function() {});
      return;
    }
    if (dequeueNext()) return;
    if (!filteredItems.length) return;
    var ni = nextIndex();
    if (ni < 0) {
      /* End of list, no repeat — stop playback */
      wasPlaying = false;
      btnPlay.innerHTML = IC_PLAY;
      return;
    }
    playTrack(ni);
  }

  function _syncQueueBottom() {
    if (!_queuePanel) return;
    var bar = document.querySelector('.player-bar');
    var barH = bar ? bar.offsetHeight : 80;
    _queuePanel.style.bottom = barH + 'px';
    /* Compute available space: header top → player bar top */
    var hdr = document.querySelector('header');
    var hdrH = hdr ? hdr.offsetHeight : 56;
    var available = window.innerHeight - hdrH - barH - 8; /* 8px breathing room */
    if (available < _QUEUE_MIN_H) available = _QUEUE_MIN_H;
    /* Apply user-chosen height if set, otherwise use full available space */
    var h = _queueUserHeight ? Math.min(_queueUserHeight, available) : available;
    if (h < _QUEUE_MIN_H) h = _QUEUE_MIN_H;
    _queuePanel.style.maxHeight = h + 'px';
  }

  /* ── Queue drag-to-resize ── */
  (function _initQueueResize() {
    if (!_queueDragHandle || !_queuePanel) return;
    var _dragging = false;
    var _startY = 0;
    var _startH = 0;

    function _getAvailable() {
      var bar = document.querySelector('.player-bar');
      var barH = bar ? bar.offsetHeight : 80;
      var hdr = document.querySelector('header');
      var hdrH = hdr ? hdr.offsetHeight : 56;
      return window.innerHeight - hdrH - barH - 8;
    }

    function onPointerDown(e) {
      if (!_queueOpen) return;
      e.preventDefault();
      _dragging = true;
      _startY = e.touches ? e.touches[0].clientY : e.clientY;
      _startH = _queuePanel.offsetHeight;
      _queuePanel.classList.add('dragging');
      document.addEventListener('mousemove', onPointerMove, {passive: false});
      document.addEventListener('touchmove', onPointerMove, {passive: false});
      document.addEventListener('mouseup', onPointerUp);
      document.addEventListener('touchend', onPointerUp);
    }

    function onPointerMove(e) {
      if (!_dragging) return;
      e.preventDefault();
      var clientY = e.touches ? e.touches[0].clientY : e.clientY;
      var delta = _startY - clientY; /* positive = dragging up = taller */
      var available = _getAvailable();
      if (available < _QUEUE_MIN_H) available = _QUEUE_MIN_H;
      var newH = Math.max(_QUEUE_MIN_H, Math.min(_startH + delta, available));
      _queuePanel.style.maxHeight = newH + 'px';
    }

    function onPointerUp(e) {
      if (!_dragging) return;
      _dragging = false;
      _queuePanel.classList.remove('dragging');
      /* Persist the chosen height (enforce minimum) */
      var finalH = _queuePanel.offsetHeight;
      if (finalH >= _QUEUE_MIN_H) {
        _queueUserHeight = finalH;
        try { localStorage.setItem(_QUEUE_HEIGHT_KEY, String(finalH)); } catch(ex) {}
      }
      document.removeEventListener('mousemove', onPointerMove);
      document.removeEventListener('touchmove', onPointerMove);
      document.removeEventListener('mouseup', onPointerUp);
      document.removeEventListener('touchend', onPointerUp);
    }

    _queueDragHandle.addEventListener('mousedown', onPointerDown);
    _queueDragHandle.addEventListener('touchstart', onPointerDown, {passive: false});
  })();
  /* Recalc on window resize */
  window.addEventListener('resize', function() { if (_queueOpen) _syncQueueBottom(); });

  function openQueuePanel() {
    _ensureQueueDom();
    if (!_queuePanel) return;
    _queueOpen = true;
    /* Close lyrics panel if open */
    if (_lyricsOpen) closeLyricsPanel();
    _syncQueueBottom();
    renderQueuePanel();
    _queuePanel.classList.add('visible');
    if (_queueBtn) _queueBtn.classList.add('queue-active');
  }

  function closeQueuePanel() {
    _ensureQueueDom();
    _queueOpen = false;
    destroyQueueDragDrop();
    if (_queuePanel) _queuePanel.classList.remove('visible');
    if (_queueBtn) _queueBtn.classList.remove('queue-active');
  }

  function toggleQueuePanel() {
    _ensureQueueDom();
    if (_queueOpen) closeQueuePanel();
    else openQueuePanel();
  }

  if (_queueBtn) {
    _queueBtn.addEventListener('click', toggleQueuePanel);
  }
  if (_queueClose) {
    _queueClose.addEventListener('click', closeQueuePanel);
  }
  if (_queueClearBtn) {
    _queueClearBtn.addEventListener('click', function() {
      clearQueue();
      showToast('Warteschlange geleert');
    });
  }

  /* ── Queue drag-and-drop reorder ── */
  function destroyQueueDragDrop() {
    if (_queueDndCleanup) { _queueDndCleanup(); _queueDndCleanup = null; }
  }

  function initQueueDragDrop() {
    destroyQueueDragDrop();
    var qList = document.getElementById('queue-list');
    if (!qList) return;
    var items = qList.querySelectorAll('.queue-item');
    if (items.length < 2) return;

    var _dragItem = null;
    var _dragFromIdx = -1;
    var _ghost = null;
    var _dropTarget = null;
    var _dropAbove = true;
    var _longPressTimer = null;
    var _touchStartY = 0;
    var _touchStartX = 0;
    var _dragActive = false;
    var LONG_PRESS_MS = 400;
    var MOVE_THRESHOLD = 8;

    function getQueueItem(el) {
      while (el && el !== qList) {
        if (el.classList && el.classList.contains('queue-item')) return el;
        el = el.parentElement;
      }
      return null;
    }

    function createGhost(item, x, y) {
      var g = document.createElement('div');
      g.className = 'playlist-drag-ghost';
      var img = item.querySelector('.queue-item-thumb');
      var title = item.querySelector('.queue-item-title');
      if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
      g.innerHTML += '<span>' + (title ? title.textContent : '') + '</span>';
      g.style.left = (x - 20) + 'px';
      g.style.top = (y - 20) + 'px';
      document.body.appendChild(g);
      return g;
    }

    function moveGhost(x, y) {
      if (!_ghost) return;
      _ghost.style.left = (x - 20) + 'px';
      _ghost.style.top = (y - 20) + 'px';
    }

    function clearDropIndicator() {
      qList.querySelectorAll('.drag-over-above,.drag-over-below').forEach(function(el) {
        el.classList.remove('drag-over-above', 'drag-over-below');
      });
      _dropTarget = null;
    }

    function updateDropTarget(x, y) {
      if (_ghost) _ghost.style.display = 'none';
      var el = document.elementFromPoint(x, y);
      if (_ghost) _ghost.style.display = '';
      var target = el ? getQueueItem(el) : null;
      if (!target || target === _dragItem) { clearDropIndicator(); return; }
      var rect = target.getBoundingClientRect();
      var above = (y - rect.top) < rect.height / 2;
      clearDropIndicator();
      _dropTarget = target;
      _dropAbove = above;
      target.classList.add(above ? 'drag-over-above' : 'drag-over-below');
    }

    function finishDrag() {
      if (!_dragActive || !_dragItem || !_dropTarget) { cancelDrag(); return; }
      var fromIdx = Number(_dragItem.dataset.queueIndex);
      var toIdx = Number(_dropTarget.dataset.queueIndex);
      if (!_dropAbove) toIdx += 1;
      if (fromIdx < toIdx) toIdx -= 1;
      if (fromIdx !== toIdx && fromIdx >= 0 && toIdx >= 0 && fromIdx < _userQueue.length) {
        var moved = _userQueue.splice(fromIdx, 1)[0];
        _userQueue.splice(Math.min(toIdx, _userQueue.length), 0, moved);
      }
      cancelDrag();
      renderQueuePanel();
    }

    function cancelDrag() {
      _dragActive = false;
      if (_ghost) { _ghost.remove(); _ghost = null; }
      clearDropIndicator();
      if (_dragItem) _dragItem.style.opacity = '';
      _dragItem = null;
      _dragFromIdx = -1;
      document.body.classList.remove('playlist-dragging');
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
    }

    function startDrag(item, x, y) {
      _dragActive = true;
      _dragItem = item;
      _dragFromIdx = Number(item.dataset.queueIndex);
      _ghost = createGhost(item, x, y);
      item.style.opacity = '0.3';
      document.body.classList.add('playlist-dragging');
    }

    /* Touch events */
    function onTouchStart(e) {
      var item = getQueueItem(e.target);
      if (!item || e.target.closest('.queue-item-remove')) return;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
      _longPressTimer = setTimeout(function() {
        _longPressTimer = null;
        if (navigator.vibrate) navigator.vibrate(30);
        startDrag(item, _touchStartX, _touchStartY);
      }, LONG_PRESS_MS);
    }
    function onTouchMove(e) {
      if (_longPressTimer) {
        var dx = Math.abs(e.touches[0].clientX - _touchStartX);
        var dy = Math.abs(e.touches[0].clientY - _touchStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          clearTimeout(_longPressTimer); _longPressTimer = null;
        }
      }
      if (_dragActive) {
        e.preventDefault();
        var tx = e.touches[0].clientX, ty = e.touches[0].clientY;
        moveGhost(tx, ty);
        updateDropTarget(tx, ty);
      }
    }
    function onTouchEnd() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      if (_dragActive) finishDrag();
    }

    /* Mouse events */
    var _mouseItem = null;
    var _mouseStartX = 0, _mouseStartY = 0;
    function onMouseDown(e) {
      if (e.button !== 0) return;
      var item = getQueueItem(e.target);
      if (!item || e.target.closest('.queue-item-remove')) return;
      _mouseItem = item;
      _mouseStartX = e.clientX;
      _mouseStartY = e.clientY;
    }
    function onMouseMove(e) {
      if (_mouseItem && !_dragActive) {
        var dx = Math.abs(e.clientX - _mouseStartX);
        var dy = Math.abs(e.clientY - _mouseStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          startDrag(_mouseItem, e.clientX, e.clientY);
          _mouseItem = null;
        }
      }
      if (_dragActive) {
        e.preventDefault();
        moveGhost(e.clientX, e.clientY);
        updateDropTarget(e.clientX, e.clientY);
      }
    }
    function onMouseUp() {
      _mouseItem = null;
      if (_dragActive) finishDrag();
    }

    qList.addEventListener('touchstart', onTouchStart, { passive: true });
    qList.addEventListener('touchmove', onTouchMove, { passive: false });
    qList.addEventListener('touchend', onTouchEnd);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    qList.addEventListener('mousedown', onMouseDown);

    _queueDndCleanup = function() {
      qList.removeEventListener('touchstart', onTouchStart);
      qList.removeEventListener('touchmove', onTouchMove);
      qList.removeEventListener('touchend', onTouchEnd);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      qList.removeEventListener('mousedown', onMouseDown);
      cancelDrag();
    };
  }

  function scheduleBackgroundRefresh(delay) {
    if (_indexRefreshTimer) return;
    _indexRefreshTimer = setTimeout(function() {
      _indexRefreshTimer = null;
      fetch(API_PATH, { cache: 'no-store' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (!data || data.error) return;
          if (data.refreshing) {
            var detail = data.detail || 'Building index…';
            showIndexingToast(detail);
            scheduleBackgroundRefresh();
            /* Update items if more are now available */
            var newItems = data && Array.isArray(data.items) ? data.items : [];
            if (newItems.length > allItems.length) {
              allItems = newItems;
              _invalidateDupeMap();
              _invalidateFolderCache();
              showFolderView();
            }
            return;
          }
          /* Full index ready */
          hideIndexingToast();
          allItems = data && Array.isArray(data.items) ? data.items : [];
          _invalidateDupeMap();
          _invalidateFolderCache();
          console.info('Background refresh complete:', allItems.length, 'items');
          showFolderView();
        })
        .catch(function() { scheduleBackgroundRefresh(); });
    }, delay !== undefined ? delay : 800);
  }

  /* Cancel the pending poll timer and re-fetch immediately.
     Only acts when an index build is actually in progress. */
  function forceBackgroundRefresh() {
    if (!_indexRefreshTimer) return; /* nothing scheduled → no build in progress */
    clearTimeout(_indexRefreshTimer);
    _indexRefreshTimer = null;
    scheduleBackgroundRefresh(0);
  }

  /* ── Manual catalog refresh (user-triggered) ── */
  var _refreshBtn = document.getElementById('refresh-btn');

  function _refreshPoll() {
    fetch(API_PATH, { cache: 'no-store' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
      if (!data) {
        if (_refreshBtn) _refreshBtn.classList.remove('spinning');
        showToast('Refresh fehlgeschlagen');
        return;
      }
      if (data.refreshing) {
        setTimeout(_refreshPoll, 800);
        return;
      }
      var oldCount = allItems.length;
      allItems = Array.isArray(data.items) ? data.items : [];
      _invalidateDupeMap();
      _invalidateFolderCache();
      if (_refreshBtn) _refreshBtn.classList.remove('spinning');

      /* Show refresh timestamp */
      var infoEl = document.getElementById('refresh-info');
      if (infoEl) {
        var dt = new Date();
        var hhmm = String(dt.getHours()).padStart(2, '0') + ':' + String(dt.getMinutes()).padStart(2, '0');
        infoEl.textContent = allItems.length + ' Titel (' + hhmm + ')';
        infoEl.title = 'Letzter Katalog-Refresh: ' + dt.toLocaleString();
      }

      /* Re-render current view */
      if (inPlaylist) {
        var newItems = itemsUnder(currentPath);
        if (newItems.length) playlistItems = newItems;
        applyFilter();
      } else {
        showFolderView();
      }
      var diff = allItems.length - oldCount;
      var msg = allItems.length + ' Titel geladen';
      if (diff > 0) msg += ' (+' + diff + ' neu)';
      else if (diff < 0) msg += ' (' + diff + ' entfernt)';
      showToast(msg);
    })
    .catch(function() { setTimeout(_refreshPoll, 2000); });
  }

  function refreshCatalog() {
    if (_refreshBtn) _refreshBtn.classList.add('spinning');
    _ratingRefreshPath = null;

    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    /* Invalidate server-side index cache and trigger full rebuild */
    fetch(base + '/refresh', { method: 'POST' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function() { _refreshPoll(); })
    .catch(function() {
      if (_refreshBtn) _refreshBtn.classList.remove('spinning');
      showToast('Refresh fehlgeschlagen');
    });
  }
  if (_refreshBtn) _refreshBtn.addEventListener('click', refreshCatalog);

  /* ── Lazy per-folder rating refresh ── */
  var _ratingRefreshPath = null;
  function refreshFolderRatings(folderItems) {
    if (!RATING_WRITE_ENABLED || !folderItems.length) return;
    var refreshPath = currentPath;
    /* Skip if we just refreshed this exact folder */
    if (_ratingRefreshPath === refreshPath) return;
    _ratingRefreshPath = refreshPath;
    var paths = folderItems.map(function(t) { return t.relative_path; });
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    fetch(base + '/refresh-ratings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: paths })
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
      if (!data || !data.ratings) return;
      var ratings = data.ratings;
      var anyChange = data.changed > 0;
      /* Patch allItems */
      for (var i = 0; i < allItems.length; i++) {
        var rp = allItems[i].relative_path;
        if (ratings.hasOwnProperty(rp) && allItems[i].rating !== ratings[rp]) {
          allItems[i] = Object.assign({}, allItems[i], { rating: ratings[rp] });
        }
      }
      /* Patch playlistItems */
      for (var j = 0; j < playlistItems.length; j++) {
        var rp2 = playlistItems[j].relative_path;
        if (ratings.hasOwnProperty(rp2) && playlistItems[j].rating !== ratings[rp2]) {
          playlistItems[j] = Object.assign({}, playlistItems[j], { rating: ratings[rp2] });
        }
      }
      /* Show refresh timestamp */
      var infoEl = document.getElementById('refresh-info');
      if (infoEl && data.last_refresh) {
        var dt = new Date(data.last_refresh);
        var hhmm = String(dt.getHours()).padStart(2, '0') + ':' + String(dt.getMinutes()).padStart(2, '0');
        var countInfo = Object.keys(ratings).length + ' Ratings gelesen';
        if (anyChange) countInfo += ', ' + data.changed + ' aktualisiert';
        infoEl.textContent = countInfo + ' (' + hhmm + ')';
        infoEl.title = 'Letzte Rating-Aktualisierung: ' + dt.toLocaleString();
      }
      /* Re-render if still viewing the same folder */
      if (inPlaylist && currentPath === refreshPath) {
        applyFilter();
      }
    })
    .catch(function() { /* silent background refresh */ });
  }

"""
        + waveform_setup_js
        + sprite_preview_js
        + """

  /* items under a path prefix (recursive) */
  function itemsUnder(path) {
    if (!path) return allItems;
    var prefix = path + '/';
    return allItems.filter(function(it) { return it.relative_path.startsWith(prefix); });
  }

  /* compute direct sub-folders and loose files at a path level */
  var IGNORED_FOLDERS = {'#recycle': true, '@eaDir': true};
  var _LANG_TAG_RE = /\\s*\\(\\s*(?:engl(?:ish)?|eng|en|german|deutsch|ger|de|french|fran[c\u00e7]ais(?:e)?|fr|spanish|espa[n\u00f1]ol|es|italian(?:o)?|it|japanese|jap|jpn?|ja|korean|kor?|ko|chinese|zh|portuguese|pt|russian|ru)(?:\\s*,\\s*(?:ger|de|eng|en)(?:\\s*sub(?:s)?)?)?\\s*\\)/gi;
  var _LANG_DETECT_MAP = [
    [/\\(\\s*engl(?:ish)?\\s*(?:,\\s*(?:ger|de)(?:\\s*sub(?:s)?)?)?\\s*\\)/i, 'en'],
    [/\\(\\s*eng\\s*\\)/i, 'en'], [/\\(\\s*en\\s*\\)/i, 'en'],
    [/\\(\\s*german\\s*\\)/i, 'de'], [/\\(\\s*deutsch\\s*\\)/i, 'de'],
    [/\\(\\s*ger\\s*\\)/i, 'de'], [/\\(\\s*de\\s*\\)/i, 'de'],
    [/\\(\\s*french\\s*\\)/i, 'fr'], [/\\(\\s*fran[c\u00e7]ais(?:e)?\\s*\\)/i, 'fr'], [/\\(\\s*fr\\s*\\)/i, 'fr'],
    [/\\(\\s*spanish\\s*\\)/i, 'es'], [/\\(\\s*espa[n\u00f1]ol\\s*\\)/i, 'es'], [/\\(\\s*es\\s*\\)/i, 'es'],
    [/\\(\\s*italian(?:o)?\\s*\\)/i, 'it'], [/\\(\\s*it\\s*\\)/i, 'it'],
    [/\\(\\s*japanese\\s*\\)/i, 'ja'], [/\\(\\s*jap\\s*\\)/i, 'ja'], [/\\(\\s*jpn?\\s*\\)/i, 'ja'],
    [/\\(\\s*korean\\s*\\)/i, 'ko'], [/\\(\\s*kor?\\s*\\)/i, 'ko'],
    [/\\(\\s*chinese\\s*\\)/i, 'zh'], [/\\(\\s*zh\\s*\\)/i, 'zh'],
    [/\\(\\s*portuguese\\s*\\)/i, 'pt'], [/\\(\\s*pt\\s*\\)/i, 'pt'],
    [/\\(\\s*russian\\s*\\)/i, 'ru'], [/\\(\\s*ru\\s*\\)/i, 'ru']
  ];

  function detectLangFromName(name) {
    for (var i = 0; i < _LANG_DETECT_MAP.length; i++) {
      if (_LANG_DETECT_MAP[i][0].test(name)) return _LANG_DETECT_MAP[i][1];
    }
    return '';
  }

  function cleanFolderName(name) {
    /* Strip # favourite prefix */
    if (name.charAt(0) === '#') name = name.substring(1);
    /* Strip language tags */
    name = name.replace(_LANG_TAG_RE, '');
    return name.replace(/\\s{2,}/g, ' ').trim();
  }

  function langBadgesHtml(langs) {
    if (!langs || !langs.length) return '';
    var html = '';
    langs.forEach(function(lc) {
      var svg = LANG_TO_FLAG[lc];
      if (svg) {
        html += '<span class="lang-badge" title="' + lc.toUpperCase() + '">' + svg + '</span>';
      }
    });
    return html;
  }

  /* Detect subtitle language hint from folder name, e.g. "(engl, gersub)" → "de" */
  var _SUB_DETECT_MAP = [
    [/\\(\\s*\\w+\\s*,\\s*(?:ger(?:man)?|de(?:utsch)?)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'de'],
    [/\\(\\s*\\w+\\s*,\\s*(?:eng(?:l(?:ish)?)?|en)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'en'],
    [/\\(\\s*\\w+\\s*,\\s*(?:fr(?:ench)?|fran[c\\u00e7]ais(?:e)?)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'fr'],
    [/\\(\\s*\\w+\\s*,\\s*(?:es(?:pa[n\\u00f1]ol)?|spanish)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'es'],
    [/\\(\\s*\\w+\\s*,\\s*(?:it(?:alian(?:o)?)?)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'it'],
    [/\\(\\s*\\w+\\s*,\\s*(?:ja(?:p(?:anese)?|pn?)?)(?:\\s*sub(?:s|title)?(?:s)?)?\\s*\\)/i, 'ja']
  ];
  function detectSubLangFromName(name) {
    for (var i = 0; i < _SUB_DETECT_MAP.length; i++) {
      if (_SUB_DETECT_MAP[i][0].test(name)) return _SUB_DETECT_MAP[i][1];
    }
    return '';
  }

  /* Composite flag: main language flag with optional smaller subtitle flag overlay */
  function compositeFlagHtml(mainLang, subLang) {
    var mainSvg = mainLang && LANG_TO_FLAG[mainLang] ? LANG_TO_FLAG[mainLang] : '';
    if (!mainSvg) return '';
    var subSvg = subLang && LANG_TO_FLAG[subLang] ? LANG_TO_FLAG[subLang] : '';
    if (!subSvg) {
      return '<span class="composite-flag" title="' + (mainLang || '').toUpperCase() + '">' + mainSvg + '</span>';
    }
    return '<span class="composite-flag" title="' + (mainLang || '').toUpperCase() + ' + ' + (subLang || '').toUpperCase() + ' Sub">' +
      mainSvg +
      '<span class="composite-flag-sub">' + subSvg + '</span>' +
    '</span>';
  }

  function contentsAt(path) {
    var items = itemsUnder(path);
    var folderMap = {};
    var folderThumb = {};
    var folderThumbLg = {};
    var folderLangs = {};
    var folderSubLangs = {};
    var files = [];
    var off = path ? path.length + 1 : 0;
    items.forEach(function(it) {
      var rest = it.relative_path.substring(off);
      var slash = rest.indexOf('/');
      if (slash >= 0) {
        var name = rest.substring(0, slash);
        if (IGNORED_FOLDERS[name]) return;
        if (!folderMap[name]) folderMap[name] = 0;
        folderMap[name]++;
        if (!folderThumb[name] && it.thumbnail_url) folderThumb[name] = it.thumbnail_url;
        if (!folderThumbLg[name] && it.thumbnail_lg_url) folderThumbLg[name] = it.thumbnail_lg_url;
        /* Aggregate languages from items + folder-name detection */
        if (!folderLangs[name]) folderLangs[name] = {};
        if (it.language) folderLangs[name][it.language] = true;
        var folderLang = detectLangFromName(name);
        if (folderLang) folderLangs[name][folderLang] = true;
        /* Aggregate subtitle languages from items + folder-name detection */
        if (!folderSubLangs[name]) folderSubLangs[name] = '';
        if (!folderSubLangs[name] && it.subtitle_language) folderSubLangs[name] = it.subtitle_language;
        if (!folderSubLangs[name]) {
          var detSub = detectSubLangFromName(name);
          if (detSub) folderSubLangs[name] = detSub;
        }
      } else {
        files.push(it);
      }
    });
    var folders = Object.keys(folderMap)
      .sort(function(a, b) {
        /* Favorites (#-prefixed) first, then alphabetical */
        var aFav = a.charAt(0) === '#';
        var bFav = b.charAt(0) === '#';
        if (aFav !== bFav) return aFav ? -1 : 1;
        return a.localeCompare(b);
      })
      .map(function(n) {
        var isFav = n.charAt(0) === '#';
        var langs = folderLangs[n] ? Object.keys(folderLangs[n]).sort() : [];
        return {
          name: n,
          displayName: cleanFolderName(n),
          isFavorite: isFav,
          count: folderMap[n],
          thumbnail_url: folderThumb[n] || '',
          thumbnail_lg_url: folderThumbLg[n] || '',
          languages: langs,
          subLang: folderSubLangs[n] || '',
          variants: null
        };
      });

    /* ── Multi-language merge ── */
    /* Group folders by merge-key: LANG_GROUPS[name] or displayName */
    var _mergeMap = {};
    folders.forEach(function(f) {
      var key = LANG_GROUPS[f.name] || f.displayName;
      if (!_mergeMap[key]) _mergeMap[key] = [];
      _mergeMap[key].push(f);
    });
    var merged = [];
    Object.keys(_mergeMap).forEach(function(key) {
      var group = _mergeMap[key];
      if (group.length === 1) {
        merged.push(group[0]);
        return;
      }
      /* Pick primary: prefer variant without language tag, or favorite, or first */
      var primary = group[0];
      for (var gi = 0; gi < group.length; gi++) {
        if (group[gi].isFavorite) { primary = group[gi]; break; }
        if (!detectLangFromName(group[gi].name) && !LANG_GROUPS[group[gi].name]) primary = group[gi];
      }
      var allLangs = {};
      var totalCount = 0;
      var variants = [];
      group.forEach(function(g) {
        totalCount += g.count;
        g.languages.forEach(function(lc) { allLangs[lc] = true; });
        var lang = g.languages.length ? g.languages[0] : detectLangFromName(g.name) || '';
        var subLang = detectSubLangFromName(g.name) || g.subLang || '';
        variants.push({ name: g.name, lang: lang, subLang: subLang, count: g.count });
      });
      merged.push({
        name: primary.name,
        displayName: primary.displayName,
        isFavorite: group.some(function(g) { return g.isFavorite; }),
        count: totalCount,
        thumbnail_url: primary.thumbnail_url || group[1].thumbnail_url || '',
        thumbnail_lg_url: primary.thumbnail_lg_url || group[1].thumbnail_lg_url || '',
        languages: Object.keys(allLangs).sort(),
        variants: variants
      });
    });

    return { folders: merged, files: files };
  }

  function leafName(path) {
    if (!path) return originalTitle;
    var i = path.lastIndexOf('/');
    var raw = i >= 0 ? path.substring(i + 1) : path;
    return cleanFolderName(raw);
  }

  function parentPath(path) {
    if (!path) return '';
    var i = path.lastIndexOf('/');
    return i >= 0 ? path.substring(0, i) : '';
  }

  function showLoadingState(message) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.style.display = 'none';
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    trackCount.textContent = 'Loading…';
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(message || 'Loading library…') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function showCatalogLoadError(detail) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.style.display = 'none';
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    trackCount.textContent = 'Library unavailable';
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(detail || 'Library could not be loaded.') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function scheduleInitialCatalogRetry(reason) {
    if (initialCatalogRetryTimer) return;
    console.info('Initial catalog retry scheduled:', reason || 'loading');
    initialCatalogRetryTimer = window.setTimeout(function() {
      initialCatalogRetryTimer = null;
      loadInitialCatalog();
    }, 800);
  }

  function loadInitialCatalog() {
    if (allItems.length) {
      console.info('Initial catalog already present in page payload:', allItems.length, 'items');
      return Promise.resolve(allItems);
    }
    initialCatalogRetryCount += 1;
    if (initialCatalogRetryCount <= 1) {
      showLoadingState('Loading library…');
    }
    var t0 = Date.now();
    console.info('Initial catalog fetch started:', API_PATH);
    return fetch(API_PATH, { cache: 'no-store' })
      .then(function(r) {
        console.info('Initial catalog response received after', Date.now() - t0, 'ms with status', r.status);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        if (data && data.error) {
          throw new Error(data.error);
        }
        /* Handle loading state (truly empty, no quick scan available) */
        if (data && data.loading && (!data.items || data.items.length === 0)) {
          var detail = data.detail || 'Library cache is warming in the background.';
          console.info('Initial catalog still building (empty):', detail);
          showIndexingToast(detail);
          scheduleInitialCatalogRetry(detail);
          return [];
        }
        if (initialCatalogRetryTimer) {
          window.clearTimeout(initialCatalogRetryTimer);
          initialCatalogRetryTimer = null;
        }
        initialCatalogRetryCount = 0;
        allItems = data && Array.isArray(data.items) ? data.items : [];
        _invalidateDupeMap();
        _invalidateFolderCache();
        console.info('Initial catalog parsed after', Date.now() - t0, 'ms:', allItems.length, 'items');
        showFolderView();
        /* If still building, show indexing toast and poll for updates */
        if (data && data.refreshing) {
          var refreshDetail = data.detail || 'Building index in background…';
          console.info('Catalog served from quick scan, index still building:', refreshDetail);
          showIndexingToast(refreshDetail);
          scheduleBackgroundRefresh();
        } else {
          hideIndexingToast();
        }
        return allItems;
      })
      .catch(function(err) {
        console.error('Initial catalog load failed:', err);
        showCatalogLoadError(err && err.message ? err.message : 'Library could not be loaded.');
        return [];
      });
  }

  /* ── breadcrumb ── */
  function renderBreadcrumb() {
    if (!currentPath) { breadcrumb.classList.remove('visible'); return; }
    breadcrumb.classList.add('visible');
    /* Special offline playlist breadcrumb */
    if (currentPath === '__offline__') {
      breadcrumb.innerHTML = '<a data-path="">\\u{1F3E0} Home</a>' +
        '<span class="sep">\\u203A</span>' +
        '<span class="current">Downloaded</span>';
      breadcrumb.querySelectorAll('a').forEach(function(a) {
        a.addEventListener('click', function() {
          currentPath = a.dataset.path;
          showFolderView();
        });
      });
      return;
    }
    var parts = currentPath.split('/');
    var h = '<a data-path="">\\u{1F3E0} Home</a>';
    for (var i = 0; i < parts.length; i++) {
      h += '<span class="sep">\\u203A</span>';
      var p = parts.slice(0, i + 1).join('/');
      var label = cleanFolderName(parts[i]);
      if (i < parts.length - 1) {
        h += '<a data-path="' + escHtml(p) + '">' + escHtml(label) + '</a>';
      } else {
        h += '<span class="current">' + escHtml(label) + '</span>';
      }
    }
    breadcrumb.innerHTML = h;
    breadcrumb.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() {
        currentPath = a.dataset.path;
        showFolderView();
      });
    });
  }

  /* ── view toggle ── */
  var IC_GRID = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
  var IC_LIST = '<svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_FILENAMES = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="14" y2="6"/><line x1="3" y1="12" x2="18" y2="12"/><line x1="3" y1="18" x2="11" y2="18"/><polyline points="17,15 20,18 17,21" stroke-linejoin="round"/></svg>';
  function applyViewMode() {
    if (_anyToolActive()) {
      /* Tools mode: force list view with raw filenames, toggle locked */
      folderGrid.classList.add('list-mode');
      folderGrid.classList.add('filenames-mode');
      viewToggle.innerHTML = IC_LIST;
      viewToggle.title = 'Tools aktiv \u2014 Listenansicht mit Dateinamen';
      viewToggle.classList.add('view-toggle-locked');
    } else if (viewMode === 'list') {
      folderGrid.classList.add('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_GRID;
      viewToggle.title = 'Listenansicht \u2014 Klick f\u00fcr Kachelansicht';
      viewToggle.classList.remove('view-toggle-locked');
    } else {
      /* 'grid' */
      folderGrid.classList.remove('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_LIST;
      viewToggle.title = 'Kachelansicht \u2014 Klick f\u00fcr Listenansicht';
      viewToggle.classList.remove('view-toggle-locked');
    }
  }

  /* ── folder view ── */

  function showFolderView() {
    destroyPlaylistDragDrop();
    closeLangPicker();
    inPlaylist = false;
    _currentPlaylistId = '';
    _globalSearchActive = false;
    /* Clear refresh-info when leaving playlist view */
    var rInfo = document.getElementById('refresh-info');
    if (rInfo) rInfo.textContent = '';
    var c = contentsAt(currentPath);
    var isRoot = !currentPath;
    var showOrigNames = _anyToolActive();

    /* Global search bar — always visible when catalog loaded */
    if (allItems.length > 0) {
      initGlobalSearch();
    } else {
      _hideGlobalSearch();
    }

    /* empty library */
    if (c.folders.length === 0 && c.files.length === 0) {
      folderGrid.classList.remove('view-hidden');
      trackView.classList.add('view-hidden');
      filterBar.classList.add('view-hidden');
      playAllBtn.style.display = 'none';
      headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
      backBtn.style.display = currentPath ? 'inline-block' : 'none';
      if (!player.currentSrc) playerBar.classList.add('view-hidden');
      folderGrid.innerHTML = '<div class="empty-hint">No items found. Run a sync first.</div>';
      trackCount.textContent = '';
      renderBreadcrumb();
      applyViewMode();
      return;
    }

    /* leaf folder (no sub-folders) → playlist */
    if (c.folders.length === 0) {
      showPlaylist(c.files, false);
      return;
    }

    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    if (!player.currentSrc) playerBar.classList.add('view-hidden');

    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    playAllBtn.style.display = '';

    var label = c.folders.length + ' folder' + (c.folders.length !== 1 ? 's' : '');
    if (c.files.length > 0) {
      label += ', ' + c.files.length + ' ' + (c.files.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    }
    trackCount.textContent = label;

    var html = '';

    /* Offline Downloads folder card — only on root */
    if (isRoot && OFFLINE_ENABLED) {
      html += '<div class="folder-card offline-folder-card" id="offline-folder-card">' +
        '<div class="folder-thumb offline-folder-icon">' + IC_DL + '</div>' +
        '<div class="folder-name">Downloaded</div>' +
        '<div class="folder-count" id="offline-folder-count">0 downloads</div>' +
      '</div>';
    }

    /* Auto-Favorites playlist card — only on root when favorites exist */
    if (isRoot && PLAYLISTS_ENABLED) {
      var _favCount = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; }).length;
      if (_favCount > 0) {
        html += '<div class="folder-card playlist-folder-card" data-playlist-id="__favorites__">' +
          '<div class="folder-thumb playlist-folder-icon">' + IC_STAR + '</div>' +
          '<div class="folder-name">Favoriten</div>' +
          '<div class="folder-count">' + _favCount + ' Titel</div>' +
          '<button class="folder-play-btn playlist-folder-play" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
        '</div>';
      }
    }

    /* Playlist pseudo-folder cards — only on root, only when playlists enabled */
    var _playlistCardsRendered = false;
    if (isRoot && PLAYLISTS_ENABLED) {
      _playlistCardsRendered = true;
      _userPlaylists.forEach(function(pl) {
        var cnt = (pl.items || []).length;
        html += '<div class="folder-card playlist-folder-card" data-playlist-id="' + escHtml(pl.id) + '">' +
          '<div class="folder-thumb playlist-folder-icon">' + IC_PLAYLIST + '</div>' +
          '<div class="folder-name">' + escHtml(pl.name) + '</div>' +
          '<div class="folder-count">' + cnt + ' Titel</div>' +
          '<button class="folder-play-btn playlist-folder-play" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
          '<button class="playlist-folder-del" title="L\u00f6schen">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</button>' +
        '</div>';
      });
      /* "+ Neue Playlist" card */
      html += '<div class="folder-card playlist-new-card" id="playlist-new-card">' +
        '<div class="folder-thumb playlist-folder-icon">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
        '</div>' +
        '<div class="folder-name">Neue Playlist\u2026</div>' +
        '<div class="folder-count"></div>' +
      '</div>';
    }

    c.folders.forEach(function(f) {
      var noun = f.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
      var thumbSrc = viewMode !== 'list'
        ? (f.thumbnail_lg_url || f.thumbnail_url || FOLDER_PLACEHOLDER)
        : (f.thumbnail_url || FOLDER_PLACEHOLDER);
      var displayLabel = showOrigNames ? f.name : f.displayName;
      var favBadge = f.isFavorite && !showOrigNames ? '<span class="fav-badge" title="Favorit">' + IC_STAR + '</span>' : '';
      var langBadges = !showOrigNames ? langBadgesHtml(f.languages) : '';
      var isAudiobook = AUDIOBOOK_DIRS.some(function(d) { return f.name.toLowerCase().startsWith(d.toLowerCase()); });
      var hasVariants = f.variants && f.variants.length > 1;
      var extraClass = (f.isFavorite ? ' fav-folder' : '') + (isAudiobook ? ' audiobook-folder' : '') + (hasVariants ? ' multi-lang-folder' : '');
      var variantsAttr = hasVariants ? ' data-variants="' + escHtml(JSON.stringify(f.variants)) + '"' : '';

      /* Build folder-count content: inline flag buttons for multi-lang, plain count otherwise */
      var countContent;
      if (hasVariants && !showOrigNames) {
        /* Sort: DEFAULT_LANG first, then alphabetical */
        var sortedV = f.variants.slice().sort(function(a, b) {
          if (a.lang === DEFAULT_LANG && b.lang !== DEFAULT_LANG) return -1;
          if (b.lang === DEFAULT_LANG && a.lang !== DEFAULT_LANG) return 1;
          return (a.lang || '').localeCompare(b.lang || '');
        });
        countContent = '';
        sortedV.forEach(function(v) {
          var flag = compositeFlagHtml(v.lang, v.subLang);
          if (flag) {
            countContent += '<button class="lang-select-btn" data-variant-name="' + escHtml(v.name) + '" title="' +
              escHtml((_LANG_NAME_MAP[v.lang] || v.lang || '') + (v.subLang ? ' + ' + (_LANG_NAME_MAP[v.subLang] || v.subLang) + ' Sub' : '') + ' (' + v.count + ')') + '">' +
              flag + '<span class="lang-select-count">' + v.count + '</span></button>';
          }
        });
        if (!countContent) countContent = f.count + ' ' + noun;
      } else {
        countContent = f.count + ' ' + noun;
      }

      html += '<div class="folder-card' + extraClass + '" data-folder="' + escHtml(f.name) + '"' + variantsAttr + '>' +
        favBadge +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="folder-name">' + escHtml(displayLabel) + (langBadges && !hasVariants ? ' ' + langBadges : '') + '</div>' +
        '<div class="folder-count">' + countContent + '</div>' +
        '<button class="folder-play-btn" title="Play all">' + IC_FOLDER_PLAY + '</button>' +
      '</div>';
    });
    c.files.forEach(function(it, i) {
      var thumbSrc = viewMode !== 'list'
        ? (it.thumbnail_lg_url || it.thumbnail_url || FILE_PLACEHOLDER)
        : (it.thumbnail_url || FILE_PLACEHOLDER);
      var ratingBar = it.rating > 0 ? '<div class="rating-bar" style="width:' + (it.rating / 5 * 100) + '%"></div>' : '';
      html += '<div class="folder-card file-card" data-file-idx="' + i + '">' +
        '<div class="thumb-wrap folder-thumb-wrap">' +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        ratingBar + '</div>' +
        '<div class="folder-name">' + escHtml(it.title) + '</div>' +
        '<div class="folder-count">' + escHtml(it.artist || '') + '</div>' +
      '</div>';
    });
    folderGrid.innerHTML = html;

    /* Offline folder card click → open offline library */
    var offFolderCard = document.getElementById('offline-folder-card');
    if (offFolderCard) {
      offFolderCard.addEventListener('click', function() { openOfflineLibrary(); });
      updateOfflineFolderCount();
    }

    /* Playlist pseudo-folder card click handlers */
    if (_playlistCardsRendered) {
      folderGrid.querySelectorAll('.playlist-folder-card').forEach(function(card) {
        var playBtn = card.querySelector('.playlist-folder-play');
        var delBtn = card.querySelector('.playlist-folder-del');
        card.addEventListener('click', function(e) {
          if (wasDrag(e)) return;
          if (e.target.closest('.playlist-folder-play') || e.target.closest('.playlist-folder-del')) return;
          showUserPlaylistView(card.dataset.playlistId);
        });
        if (playBtn) playBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          playUserPlaylist(card.dataset.playlistId);
        });
        if (delBtn) delBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          deleteUserPlaylist(card.dataset.playlistId);
        });
      });
      var newCard = document.getElementById('playlist-new-card');
      if (newCard) newCard.addEventListener('click', function() {
        var name = prompt('Playlist-Name:');
        if (!name || !name.trim()) return;
        fetch(PLAYLISTS_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name.trim() })
        }).then(function(r) { return r.json(); })
          .then(function(d) {
            if (d.playlist) {
              _userPlaylists.unshift(d.playlist);
              showFolderView();
              showToast('Playlist "' + d.playlist.name + '" erstellt');
            }
          }).catch(function() { showToast('Fehler beim Erstellen'); });
      });
    }

    /* Recently played — only on root, only when catalog is loaded, only when enabled */
    if (RECENT_ENABLED && isRoot && allItems.length > 0) {
      loadRecentlyPlayed();
    } else {
      var rs = document.getElementById('recent-section');
      if (rs) rs.hidden = true;
    }

    folderGrid.querySelectorAll('.folder-card:not(.file-card):not(.offline-folder-card):not(.playlist-folder-card):not(.playlist-new-card)').forEach(function(card) {
      var pb = card.querySelector('.folder-play-btn');
      var variants = card.dataset.variants ? JSON.parse(card.dataset.variants) : null;

      /* Lang-select buttons: direct navigation into that variant */
      card.querySelectorAll('.lang-select-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          var vName = btn.dataset.variantName;
          if (vName) navigateInto(vName);
        });
      });

      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        if (e.target.closest('.folder-play-btn')) return;
        if (e.target.closest('.lang-select-btn')) return;
        if (variants && variants.length > 1) {
          /* Navigate into the DEFAULT_LANG variant, or first variant */
          var defaultV = variants.find(function(v) { return v.lang === DEFAULT_LANG; });
          navigateInto(defaultV ? defaultV.name : card.dataset.folder);
        } else {
          navigateInto(card.dataset.folder);
        }
      });
      pb.addEventListener('click', function(e) {
        e.stopPropagation();
        if (wasDrag(e)) return;
        if (variants && variants.length > 1) {
          showLangPicker(card, variants, true);
        } else {
          playAllIn(card.dataset.folder);
        }
      });
    });

    var looseFiles = c.files;
    folderGrid.querySelectorAll('.file-card').forEach(function(card) {
      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        forceBackgroundRefresh(); /* get freshest data while index builds */
        showPlaylist(looseFiles, true, Number(card.dataset.fileIdx));
      });
    });

    renderBreadcrumb();
    applyViewMode();
  }

  /* ── Language picker for multi-language folders ── */
  var _langPickerCleanup = null;
  function closeLangPicker() {
    if (_langPickerCleanup) { _langPickerCleanup(); _langPickerCleanup = null; }
    var old = document.querySelector('.lang-picker-overlay');
    if (old) old.remove();
  }
  function showLangPicker(card, variants, playMode) {
    closeLangPicker();
    var overlay = document.createElement('div');
    overlay.className = 'lang-picker-overlay';
    var heading = playMode ? 'Sprache zum Abspielen w\u00e4hlen' : 'Sprachversion w\u00e4hlen';
    var inner = '<div class="lang-picker-title">' + escHtml(heading) + '</div>';
    variants.forEach(function(v) {
      var flagSvg = v.lang && LANG_TO_FLAG[v.lang] ? LANG_TO_FLAG[v.lang] : '';
      var langLabel = v.lang && _LANG_NAME_MAP[v.lang] ? _LANG_NAME_MAP[v.lang] : cleanFolderName(v.name);
      var countLabel = v.count + ' ' + (v.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
      inner += '<button class="lang-picker-item" data-variant-name="' + escHtml(v.name) + '">' +
        (flagSvg ? '<span class="lang-picker-flag">' + flagSvg + '</span>' : '') +
        '<span class="lang-picker-label">' + escHtml(langLabel) + '</span>' +
        '<span class="lang-picker-count">' + countLabel + '</span>' +
      '</button>';
    });
    overlay.innerHTML = inner;

    /* Position near the card */
    var rect = card.getBoundingClientRect();
    overlay.style.position = 'fixed';
    overlay.style.left = Math.max(4, Math.min(rect.left, window.innerWidth - 260)) + 'px';
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 200) {
      overlay.style.top = rect.bottom + 4 + 'px';
    } else {
      overlay.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
    }
    document.body.appendChild(overlay);

    overlay.querySelectorAll('.lang-picker-item').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var vName = btn.dataset.variantName;
        closeLangPicker();
        if (playMode) { playAllIn(vName); } else { navigateInto(vName); }
      });
    });

    /* Close on click outside or Escape */
    function onDocClick(e) { if (!overlay.contains(e.target) && !card.contains(e.target)) closeLangPicker(); }
    function onKeyDown(e) { if (e.key === 'Escape') closeLangPicker(); }
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onKeyDown);
    _langPickerCleanup = function() {
      document.removeEventListener('click', onDocClick, true);
      document.removeEventListener('keydown', onKeyDown);
    };
  }

  function navigateInto(name) {
    currentPath = currentPath ? currentPath + '/' + name : name;
    forceBackgroundRefresh(); /* get freshest data while index builds */
    showFolderView();
  }

  function playAllIn(name) {
    var full = currentPath ? currentPath + '/' + name : name;
    var items = itemsUnder(full);
    if (items.length) { currentPath = full; showPlaylist(items, true); }
  }

  /* ── playlist view ── */
  function showPlaylist(items, autoplay, startIdx) {
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__folder__';
    playlistItems = _sortByFolderOrder(currentPath, items);

    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    playAllBtn.style.display = 'none';

    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    playerBar.classList.remove('view-hidden');

    searchInput.value = '';
    currentIndex = -1;
    renderBreadcrumb();
    applyFilter();
    /* Lazy refresh: re-read ratings from filesystem for visible items */
    refreshFolderRatings(items);
    /* Rebuild shuffle queue for the new playlist */
    if (shuffleMode) rebuildShuffleQueue(startIdx || 0);
    if (autoplay && playlistItems.length) {
      /* When shuffle is on, start from shuffleQueue[0] instead of startIdx */
      var firstIdx = shuffleMode && shuffleQueue.length ? shuffleQueue[0] : (startIdx || 0);
      playTrack(firstIdx);
    }
    /* Pre-warm: fetch server-side order and re-sort if different */
    var _showPlaylistPath = currentPath;
    _loadFolderOrderAsync(currentPath, function(serverOrder) {
      if (!serverOrder.length) return;
      if (_currentPlaylistId !== '__folder__') return;
      var localOrder = _loadFolderOrder(_showPlaylistPath);
      if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
      playlistItems = _sortByFolderOrder(_showPlaylistPath, items);
      applyFilter();
    });
  }

  /* ── back ── */
  function goBack() {
    if (_globalSearchActive) { exitGlobalSearch(); return; }
    if (currentPath === '__offline__') {
      currentPath = '';
      showFolderView();
      return;
    }
    if (inPlaylist) {
      var c = contentsAt(currentPath);
      if (c.folders.length > 0) { showFolderView(); return; }
    }
    currentPath = parentPath(currentPath);
    showFolderView();
  }

  /* ── global search (root view) ── */
  var _globalSearchDebounce = null;
  var _globalSearchListenersInit = false;
  function initGlobalSearch() {
    var inp = document.getElementById('global-search-input');
    if (!inp) return;
    /* Show in header */
    inp.classList.remove('view-hidden');
    /* Wire events only once */
    if (_globalSearchListenersInit) return;
    _globalSearchListenersInit = true;
    inp.addEventListener('input', function() {
      clearTimeout(_globalSearchDebounce);
      var val = inp.value.trim();
      if (!val) {
        if (_globalSearchActive) exitGlobalSearch();
        return;
      }
      _globalSearchDebounce = setTimeout(function() { globalSearch(val); }, 200);
    });
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        inp.value = '';
        if (_globalSearchActive) exitGlobalSearch();
        inp.blur();
      }
    });
  }

  function _hideGlobalSearch() {
    var inp = document.getElementById('global-search-input');
    if (inp) { inp.classList.add('view-hidden'); inp.value = ''; }
    if (folderFilterBar) folderFilterBar.hidden = true;
  }

  /* ── Filter bar scroll-reveal ── */
  var _fbScrollInitDone = false;
  var _fbLastScrollY = 0;
  function _initFilterBarScrollReveal() {
    if (_fbScrollInitDone) return;
    _fbScrollInitDone = true;
    var wrap = document.getElementById('track-view');
    if (!wrap) return;
    wrap.addEventListener('scroll', function() {
      var y = wrap.scrollTop;
      /* Reveal when near top (y < 10) or scrolling upward */
      if (y < 10 || y < _fbLastScrollY - 2) {
        filterBar.classList.remove('fb-scroll-hidden');
      } else if (y > _fbLastScrollY + 8) {
        filterBar.classList.add('fb-scroll-hidden');
      }
      _fbLastScrollY = y;
    });
  }

  function globalSearch(needle) {
    needle = needle.toLowerCase();
    /* Filter allItems by needle — respect effective hidden threshold */
    var results = allItems.filter(function(t) {
      var r = t.rating || 0;
      if (_effectiveThreshold > 0 && !showHidden && r > 0 && r < _effectiveThreshold) return false;
      return (t.title || '').toLowerCase().indexOf(needle) >= 0 ||
             (t.artist || '').toLowerCase().indexOf(needle) >= 0 ||
             (t.relative_path || '').toLowerCase().indexOf(needle) >= 0;
    });
    _globalSearchActive = true;
    /* Hide folder grid, show track view with results */
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.add('view-hidden');
    playerBar.classList.remove('view-hidden');
    headerTitle.textContent = results.length + ' Ergebnis' + (results.length !== 1 ? 'se' : '');
    backBtn.style.display = 'inline-block';
    playAllBtn.style.display = 'none';
    trackCount.textContent = results.length + ' ' + (results.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    /* Hide recently played */
    var rs = document.getElementById('recent-section');
    if (rs) rs.hidden = true;
    /* Use search results as current playlist so next/prev works */
    playlistItems = results;
    filteredItems = results;
    inPlaylist = true;
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    /* Render search results */
    renderSearchResults(results);
  }

  function renderSearchResults(results) {
    trackList.innerHTML = '';
    if (results.length === 0) {
      trackList.innerHTML = '<li class="track-item" style="opacity:0.5;pointer-events:none"><div class="track-info"><div class="track-title">Keine Ergebnisse</div></div></li>';
      return;
    }
    results.forEach(function(t, i) {
      var li = document.createElement('li');
      li.className = 'track-item';
      li.setAttribute('data-index', i);
      var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
      var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
      /* Extract folder path for context */
      var folderPath = '';
      var lastSlash = (t.relative_path || '').lastIndexOf('/');
      if (lastSlash > 0) folderPath = t.relative_path.substring(0, lastSlash);
      li.innerHTML = '<div class="track-number">' + (i + 1) + '</div>' +
        '<div class="track-thumb-wrap"><img class="track-thumb" src="' + escHtml(thumbSrc) + '" loading="lazy">' + ratingBar + '</div>' +
        '<div class="track-info">' +
          '<div class="track-title">' + escHtml(t.title || t.relative_path) + '</div>' +
          '<div class="track-artist">' + escHtml(t.artist || '') + '</div>' +
          (folderPath ? '<div class="search-result-folder">' + escHtml(folderPath) + '</div>' : '') +
        '</div>';
      li.addEventListener('click', function() { navigateToSearchResult(t, i); });
      trackList.appendChild(li);
    });
  }

  function navigateToSearchResult(item, idx) {
    /* Play directly within search results — search stays open */
    playItem(item, idx);
    markActive();
  }

  function exitGlobalSearch() {
    _globalSearchActive = false;
    var inp = document.getElementById('global-search-input');
    if (inp) inp.value = '';
    showFolderView();
  }

  /* play all items under current path */
  function playAllCurrent() {
    var items = itemsUnder(currentPath);
    if (!items.length) items = contentsAt(currentPath).files;
    if (items.length) showPlaylist(items, true);
  }

  /* ── filter / sort within playlist ── */
  /* ── Quick-filter chips ── */
  function updateFilterChips() {
    if (filterRatingBtn) {
      if (filterRating > 0) {
        filterRatingBtn.innerHTML = IC_STAR_FILLED + ' ' + filterRating + '+';
        filterRatingBtn.classList.add('active');
        filterRatingBtn.title = filterRating + '+ Sterne — klicken zum Weiterschalten';
      } else {
        filterRatingBtn.innerHTML = IC_STAR_EMPTY + ' Bewertung';
        filterRatingBtn.classList.remove('active');
        filterRatingBtn.title = 'Nach Bewertung filtern';
      }
    }
    if (filterFavBtn) {
      filterFavBtn.innerHTML = IC_PIN + ' Favoriten';
      filterFavBtn.classList.toggle('active', filterFav);
      filterFavBtn.title = filterFav
        ? 'Favoriten-Filter aktiv — klicken zum Aufheben'
        : 'Nur Favoriten anzeigen';
    }
    if (filterGenreBtn) {
      /* Collect genres from current playlist items */
      var genres = {};
      (playlistItems || []).forEach(function(t) {
        if (t.genre) genres[t.genre] = true;
      });
      var genreList = Object.keys(genres).sort();
      if (genreList.length === 0) {
        filterGenreBtn.style.display = 'none';
      } else {
        filterGenreBtn.style.display = '';
        if (filterGenre) {
          filterGenreBtn.textContent = filterGenre;
          filterGenreBtn.classList.add('active');
          filterGenreBtn.title = 'Genre: ' + filterGenre + ' — klicken zum Weiterschalten';
        } else {
          filterGenreBtn.textContent = 'Genre';
        filterGenreBtn.classList.remove('active');
        filterGenreBtn.title = 'Nach Genre filtern';
        }
      }
    }
    if (filterHiddenBtn) {
      if (_effectiveThreshold > 0) {
        var _hiddenCount = playlistItems.filter(function(t) {
          var r = t.rating || 0; return r > 0 && r < _effectiveThreshold;
        }).length;
        var _totalCount = playlistItems.length;
        filterHiddenBtn.style.display = '';
        /* Always render "(N/M)" so the button width stays stable — prevents layout shift on click */
        filterHiddenBtn.innerHTML = IC_EYE + ' Ausgeblendet (' + _hiddenCount + '/' + _totalCount + ')';
        filterHiddenBtn.classList.toggle('active', !showHidden);
        filterHiddenBtn.title = showHidden
          ? 'Ausgeblendete Songs sichtbar \u2014 klicken zum Verstecken'
          : 'Ausgeblendete Songs einblenden';
      } else {
        filterHiddenBtn.style.display = 'none';
      }
    }
  }

  function applyFilter() {
    var needle = searchInput.value.trim().toLowerCase();
    var sortBy = sortField.value;
    var items = playlistItems;

    if (DEBUG_FILTER) {
      /* ── Debug mode: annotate items with reasons instead of removing ──
         showHidden=true  → rating-below-threshold items get _hiddenShown (grayed, same UX as normal mode)
         showHidden=false → rating-below-threshold items get _debugReason (visible with filter-reason overlay) */
      items = items.map(function(t) {
        var r = t.rating || 0;
        /* Rating threshold: when showHidden=true, gray items in-place (don't annotate as debug-filtered) */
        if (_effectiveThreshold > 0 && r > 0 && r < _effectiveThreshold) {
          var hClone = {}; for (var k in t) { if (t.hasOwnProperty(k)) hClone[k] = t[k]; }
          if (showHidden) {
            hClone._hiddenShown = true;
            hClone._hiddenReason = 'Bewertung: ' + r + '\u2605';
            return hClone;
          } else {
            hClone._debugReason = 'Rating ' + r + '\\u2605 < Schwelle ' + _effectiveThreshold;
            return hClone;
          }
        }
        var reasons = [];
        if (filterRating > 0 && (r < filterRating)) {
          reasons.push('Quick-Filter: Rating < ' + filterRating + '\\u2605');
        }
        if (filterFav && !_savedFavorites[t.relative_path]) {
          reasons.push('Kein Favorit');
        }
        if (filterGenre && t.genre !== filterGenre) {
          reasons.push('Genre \\u2260 ' + filterGenre);
        }
        if (reasons.length > 0) {
          /* Clone the item so we don't mutate the original in playlistItems */
          var clone = {};
          for (var k in t) { if (t.hasOwnProperty(k)) clone[k] = t[k]; }
          clone._debugReason = reasons.join(' | ');
          return clone;
        }
        return t;
      });
      /* Text search always filters even in debug mode */
      if (needle) {
        items = items.filter(function(t) {
          return t.title.toLowerCase().indexOf(needle) >= 0 ||
                 t.artist.toLowerCase().indexOf(needle) >= 0 ||
                 t.relative_path.toLowerCase().indexOf(needle) >= 0;
        });
      }
    } else {
      /* ── Normal mode ── */
      /* Effective threshold: tracks with rating < threshold are "ausgeblendet".
         Unrated tracks (rating 0) are always shown regardless of threshold.
         showHidden=false  → hidden songs filtered out entirely.
         showHidden=true   → hidden songs kept at their natural position, grayed
                             out with a reason label so the full list is visible. */
      if (_effectiveThreshold > 0) {
        if (!showHidden) {
          items = items.filter(function(t) {
            var r = t.rating || 0; return r === 0 || r >= _effectiveThreshold;
          });
        } else {
          /* Mark hidden items in-place — they stay at their sorted position */
          items = items.map(function(t) {
            var r = t.rating || 0;
            if (r > 0 && r < _effectiveThreshold) {
              var clone = {}; for (var k in t) { if (t.hasOwnProperty(k)) clone[k] = t[k]; }
              clone._hiddenShown = true;
              clone._hiddenReason = 'Bewertung: ' + r + '\u2605';
              return clone;
            }
            return t;
          });
        }
      }
      if (needle) {
        items = items.filter(function(t) {
          return t.title.toLowerCase().indexOf(needle) >= 0 ||
                 t.artist.toLowerCase().indexOf(needle) >= 0 ||
                 t.relative_path.toLowerCase().indexOf(needle) >= 0;
        });
      }
      /* Quick-filters (never affect hidden-shown items — they are already grayed) */
      if (filterRating > 0) {
        items = items.filter(function(t) { return t._hiddenShown || (t.rating || 0) >= filterRating; });
      }
      if (filterFav) {
        items = items.filter(function(t) { return t._hiddenShown || !!_savedFavorites[t.relative_path]; });
      }
      if (filterGenre) {
        items = items.filter(function(t) { return t._hiddenShown || t.genre === filterGenre; });
      }
    }
    items = items.slice().sort(function(a, b) {
      var sa = a.season || 0, sb = b.season || 0;
      var ea = a.episode || 0, eb = b.episode || 0;
      if (sortBy === 'custom') {
        /* In playlist context: preserve playlist order (no sort).
           In filesystem context: sort by rating desc, title asc as tiebreaker. */
        if (_currentPlaylistId) return 0;
        var ra = a.rating || 0, rb = b.rating || 0;
        if (ra !== rb) return rb - ra;
        return a.title.localeCompare(b.title);
      }
      if (sortBy === 'recent') {
        /* newest first by mtime, title as tiebreaker */
        var ma = a.mtime || 0, mb = b.mtime || 0;
        if (ma !== mb) return mb - ma;
        return a.title.localeCompare(b.title);
      }
      if (sortBy === 'title') {
        /* Series-aware title sort: prefer season/episode when present */
        if (sa > 0 || sb > 0) {
          if (sa !== sb) return sa - sb;
          if (ea !== eb) return ea - eb;
        }
        return a.title.localeCompare(b.title) || a.relative_path.localeCompare(b.relative_path);
      }
      if (sortBy === 'path') return a.relative_path.localeCompare(b.relative_path);
      /* artist sort: group by folder, then season/episode within */
      var ad = a.artist.localeCompare(b.artist);
      if (ad !== 0) return ad;
      if (sa !== sb) return sa - sb;
      if (ea !== eb) return ea - eb;
      return a.title.localeCompare(b.title);
    });
    renderTracks(items);
  }

  /* ── track list rendering ── */
  var NATIVE_EXT = ['.mp4','.m4v','.webm','.ogg','.ogv','.mp3','.m4a','.aac','.opus','.flac','.wav'];
  function needsConversion(rp) {
    if (!rp) return false;
    var dot = rp.lastIndexOf('.');
    if (dot < 0) return false;
    return NATIVE_EXT.indexOf(rp.substring(dot).toLowerCase()) < 0;
  }
  function filenameFromPath(rp) {
    if (!rp) return '';
    var slash = rp.lastIndexOf('/');
    var name = slash >= 0 ? rp.substring(slash + 1) : rp;
    var dot = name.lastIndexOf('.');
    return dot > 0 ? name.substring(0, dot) : name;
  }

  function markActive() {
    document.querySelectorAll('.track-item:not(.missing-episode):not(.debug-filtered)').forEach(function(el) {
      var idx = Number(el.dataset.index);
      el.classList.toggle('active', idx === currentIndex);
      if (idx === currentIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  /* insert placeholder rows for missing episodes within the same season */
  function withMissingEpisodes(tracks) {
    /* only insert gaps if all tracks are series episodes */
    var allSeries = tracks.length > 0 && tracks.every(function(t) { return (t.season || 0) > 0; });
    if (!allSeries) return tracks;

    var result = [];
    for (var i = 0; i < tracks.length; i++) {
      var t = tracks[i];
      /* insert gap placeholders within the same season */
      if (i > 0) {
        var prev = tracks[i - 1];
        if ((prev.season || 0) === (t.season || 0)) {
          var gap = (t.episode || 0) - (prev.episode || 0);
          for (var g = 1; g < gap && g < 20; g++) {
            result.push({ _missing: true, season: prev.season, episode: (prev.episode || 0) + g });
          }
        }
      }
      result.push(t);
    }
    return result;
  }

  function renderTracks(tracks) {
    /* Ensure dupe data is available when the dupe tool is active */
    if (_toolState.duplicates) _ensureDupeMap();
    /* Separate real items from debug-dimmed items and moved ghosts for filteredItems / shuffle */
    var realTracks = DEBUG_FILTER
      ? tracks.filter(function(t) { return !t._debugReason && !t._movedTo; })
      : tracks.filter(function(t) { return !t._movedTo; });
    var debugCount = tracks.filter(function(t) { return !!t._debugReason; }).length;
    var movedCount = tracks.filter(function(t) { return !!t._movedTo; }).length;
    filteredItems = realTracks;
    /* Rebuild shuffle queue whenever the filtered set changes */
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    var hiddenShownCount = realTracks.filter(function(t) { return !!t._hiddenShown; }).length;
    var visibleCount = realTracks.length - hiddenShownCount;
    var noun = visibleCount !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    /* "ausgeblendet" count shown in filter-hidden chip; debug count omitted here to keep track-count width stable */
    trackCount.textContent = visibleCount + ' ' + noun +
      (movedCount > 0 ? ' (' + movedCount + ' verschoben)' : '');
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }
    var showOrig = _anyToolActive();
    /* Pass realTracks to withMissingEpisodes so ghost items don't confuse ep-gap detection */
    var displayTracks = withMissingEpisodes(realTracks);
    /* Re-inject ghost items at their original positions */
    if (movedCount > 0) {
      var _ghostInserted = [];
      var _realOffset = 0;
      for (var _gi = 0; _gi < tracks.length; _gi++) {
        if (tracks[_gi]._movedTo) {
          /* Insert ghost at this position in the display list (after adjusting for gaps already inserted) */
          _ghostInserted.push(_gi);
        }
      }
      /* Rebuild displayTracks with ghosts inserted at their original index in tracks[] */
      var _dt2 = [];
      var _ri2 = 0; /* index into realTracks */
      var _di2 = 0; /* index into displayTracks (includes missing-episode placeholders) */
      for (var _ti = 0; _ti < tracks.length; _ti++) {
        if (tracks[_ti]._movedTo) {
          _dt2.push(tracks[_ti]);
        } else {
          /* copy the corresponding entry from displayTracks, which may include preceding gap placeholders */
          while (_di2 < displayTracks.length && displayTracks[_di2]._missing) {
            _dt2.push(displayTracks[_di2++]);
          }
          if (_di2 < displayTracks.length) _dt2.push(displayTracks[_di2++]);
          _ri2++;
        }
      }
      /* Append any remaining gap placeholders at the end */
      while (_di2 < displayTracks.length) { _dt2.push(displayTracks[_di2++]); }
      displayTracks = _dt2;
    }
    var realIdx = 0;
    trackList.innerHTML = displayTracks.map(function(t) {
      /* missing episode placeholder */
      if (t._missing) {
        var seLabel = 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0');
        return '<li class="track-item missing-episode">' +
          '<span class="track-num"><span class="num-text">' + seLabel + '</span></span>' +
          '<div class="track-info"><div class="track-title">\u2014</div></div></li>';
      }
      /* moved ghost: file was moved this session — shown dimmed with target hint, not playable */
      if (t._movedTo) {
        var displayTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
        var subtitle = t.artist || t.relative_path;
        var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
        var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
        return '<li class="track-item track-item--moved">' +
          '<span class="track-num"><span class="num-text">\u2192</span></span>' +
          '<div class="thumb-wrap track-thumb-wrap">' +
          '<img class="track-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
          ratingBar + '</div>' +
          '<div class="track-info">' +
            '<div class="track-title"><span class="track-title-text">' + escHtml(displayTitle) + '</span>' +
              '<span class="moved-hint">\u2192\u00a0' + escHtml(t._movedTo) + '</span></div>' +
            '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
          '</div></li>';
      }
      /* debug-filtered placeholder: dimmed, not playable */
      if (t._debugReason) {
        var displayTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
        var subtitle = t.artist || t.relative_path;
        var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
        var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
        return '<li class="track-item debug-filtered">' +
          '<span class="track-num"><span class="num-text">\u00b7</span></span>' +
          '<div class="thumb-wrap track-thumb-wrap">' +
          '<img class="track-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
          ratingBar + '</div>' +
          '<div class="track-info">' +
            '<div class="track-title">' + escHtml(displayTitle) + '</div>' +
            '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
            '<div class="debug-reason">' + escHtml(t._debugReason) + '</div>' +
          '</div></li>';
      }
      var idx = realIdx++;
      var isSeries = (t.season || 0) > 0;
      var numLabel = isSeries
        ? 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0')
        : String(idx + 1);
      var displayTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
      var subtitle = t.artist || t.relative_path;
      var extraCls = (idx === currentIndex ? ' active' : '') + (t._hiddenShown ? ' track-item--hidden-shown' : '');
      var hiddenBadge = t._hiddenShown ? '<span class="hidden-badge">' + escHtml(t._hiddenReason || 'ausgeblendet') + '</span>' : '';
      var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
      var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
      var convertBadge = needsConversion(t.relative_path) ? '<span class="convert-badge" title="Wird on-the-fly konvertiert">\\u26A1</span>' : '';
      var isDupe = _dupePaths && _dupePaths.has(t.relative_path);
      var dupeBadge = isDupe ? '<span class="dupe-badge" title="Duplikat erkannt">Duplikat<button class="track-delete-btn" data-index="' + idx + '" title="Duplikat l\\u00f6schen">' + IC_TRASH + '</button></span>' : '';
      return '<li class="track-item' + extraCls +
        '" data-index="' + idx + '">' +
        '<span class="track-num"><span class="num-text">' + numLabel + '</span></span>' +
        '<div class="thumb-wrap track-thumb-wrap">' +
        '<img class="track-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        ratingBar + '</div>' +
        '<div class="track-info">' +
          '<div class="track-title"><span class="track-title-text">' + hiddenBadge + escHtml(displayTitle) + convertBadge + dupeBadge + '</span></div>' +
          '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
        '</div>' +
        '<button class="track-dl-btn" data-stream-url="' + escHtml(t.stream_url) +
          '" data-title="' + escHtml(t.title) +
          '" data-artist="' + escHtml(t.artist || '') +
          '" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-thumbnail-url="' + escHtml(t.thumbnail_url || '') +
          '" data-media-type="' + escHtml(t.media_type || ITEM_NOUN) + '" title="Download">' + IC_DL + '</button>' +
        '<button class="track-pin-btn" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-title="' + escHtml(t.title) +
          '" title="Favorit">' + IC_PIN + '</button>' +
        (METADATA_EDIT_ENABLED ? '<button class="track-edit-btn" data-index="' + idx + '" title="Bearbeiten">' + IC_EDIT + '</button>' : '') +
        (PLAYLISTS_ENABLED ? '<button class="track-playlist-btn" data-relative-path="' + escHtml(t.relative_path || '') + '" title="Zur Playlist hinzuf\\u00fcgen">' + IC_PLAYLIST + '</button>' : '') +
        '<button class="track-queue-btn" data-relative-path="' + escHtml(t.relative_path || '') + '" data-index="' + idx + '" title="Zur Warteschlange hinzuf\\u00fcgen">' + IC_QUEUE + '</button>' +
        renderInlineRating(t, idx) +
        renderMoveWidget(t, idx) +
        '</li>';
    }).join('');
    document.querySelectorAll('.track-item:not(.missing-episode):not(.debug-filtered)').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (!wasDrag(e) && !window.getSelection().toString()) playTrack(Number(el.dataset.index));
      });
    });
    /* Wire up inline rating star clicks */
    document.querySelectorAll('.track-inline-rating-star').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        setInlineRating(Number(btn.dataset.index), Number(btn.dataset.star));
      });
    });
    document.querySelectorAll('.track-dl-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        var url = btn.dataset.streamUrl;
        var title = btn.dataset.title;
        var meta = {
          artist: btn.dataset.artist || '',
          relativePath: btn.dataset.relativePath || '',
          thumbnailUrl: btn.dataset.thumbnailUrl || '',
          mediaType: btn.dataset.mediaType || ITEM_NOUN
        };
        if (btn.classList.contains('cached')) {
          deleteTrackDownload(url, btn);
        } else if (btn.classList.contains('downloading')) {
          cancelDownload(url, btn);
        } else {
          downloadTrack(url, title, btn, meta);
        }
      });
    });
    document.querySelectorAll('.track-pin-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        var item = filteredItems.find(function(it) { return it.relative_path === btn.dataset.relativePath; });
        if (item) toggleFavorite(item, btn);
      });
    });
    if (METADATA_EDIT_ENABLED) {
      document.querySelectorAll('.track-edit-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          e.preventDefault();
          openEditModal(Number(btn.dataset.index));
        });
      });
    }
    if (PLAYLISTS_ENABLED) {
      document.querySelectorAll('.track-playlist-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          e.preventDefault();
          loadUserPlaylists().then(function() { openPlaylistModal(btn.dataset.relativePath); });
        });
      });
      if (inPlaylist && _currentPlaylistId && viewMode === 'list') initPlaylistDragDrop();
    }
    updateFavoriteButtons();
    updateAllDownloadButtons();
    /* Wire up queue buttons */
    document.querySelectorAll('.track-queue-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        var rp = btn.dataset.relativePath;
        var inQ = _userQueue.some(function(q) { return q.relative_path === rp; });
        if (inQ) {
          var qi = _userQueue.findIndex(function(q) { return q.relative_path === rp; });
          if (qi >= 0) removeFromQueue(qi);
          showToast('Aus Warteschlange entfernt');
        } else {
          var idx = Number(btn.dataset.index);
          if (idx >= 0 && idx < filteredItems.length) addToQueue(filteredItems[idx]);
        }
      });
    });
    updateQueueButtons();
    /* Wire up file-mover widgets */
    document.querySelectorAll('.move-quick-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        moveFileToFolder(Number(btn.dataset.index), btn.dataset.target);
      });
    });
    document.querySelectorAll('.move-folder-select').forEach(function(sel) {
      sel.addEventListener('click', function(e) { e.stopPropagation(); });
      sel.addEventListener('change', function(e) {
        e.stopPropagation();
        var target = sel.value;
        if (!target) return;
        moveFileToFolder(Number(sel.dataset.index), target);
        sel.value = '';
      });
    });
    /* Wire up inline delete buttons for duplicate tracks */
    document.querySelectorAll('.track-delete-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        _deleteTrackFromList(Number(btn.dataset.index));
      });
    });
  }

  /* ── offline download management ── */
  var downloadDB = null;
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var activeDownloads = {};

  function cancelDownload(streamUrl, btn) {
    var controller = activeDownloads[streamUrl];
    if (controller) {
      controller.abort();
      delete activeDownloads[streamUrl];
    }
    if (btn) {
      btn.classList.remove('downloading');
      btn.classList.remove('cached');
      btn.innerHTML = IC_DL;
      btn.title = 'Download';
    }
    showToast('Download abgebrochen');
  }

  function revokeOfflineUrl() {
    if (currentOfflineUrl) {
      URL.revokeObjectURL(currentOfflineUrl);
      currentOfflineUrl = null;
    }
  }

  function initDownloadDB() {
    return new Promise(function(resolve, reject) {
      var req = indexedDB.open('hometools-downloads', 2);
      req.onerror = function() { reject(req.error); };
      req.onsuccess = function() { downloadDB = req.result; resolve(req.result); };
      req.onupgradeneeded = function(e) {
        var db = e.target.result;
        var store;
        if (!db.objectStoreNames.contains('downloads')) {
          store = db.createObjectStore('downloads', { keyPath: 'id', autoIncrement: true });
        } else {
          store = e.target.transaction.objectStore('downloads');
        }
        if (!store.indexNames.contains('streamUrl')) {
          store.createIndex('streamUrl', 'streamUrl', { unique: true });
        }
        if (!store.indexNames.contains('status')) {
          store.createIndex('status', 'status', { unique: false });
        }
        if (!store.indexNames.contains('timestamp')) {
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }
        if (!store.indexNames.contains('title')) {
          store.createIndex('title', 'title', { unique: false });
        }
      };
    });
  }

  function getDownloadByStreamUrl(streamUrl) {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve(null); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readonly');
        var store = tx.objectStore('downloads');
        var index = store.index('streamUrl');
        var req = index.get(streamUrl);
        req.onerror = function() { resolve(null); };
        req.onsuccess = function() { resolve(req.result || null); };
      } catch (e) {
        resolve(null);
      }
    });
  }

  function getAllDownloads() {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve([]); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readonly');
        var store = tx.objectStore('downloads');
        var req = store.getAll();
        req.onerror = function() { resolve([]); };
        req.onsuccess = function() { resolve(req.result || []); };
      } catch (e) {
        resolve([]);
      }
    });
  }

  function deleteDownloadById(id) {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve(false); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readwrite');
        tx.objectStore('downloads').delete(id);
        tx.oncomplete = function() { resolve(true); };
        tx.onerror = function() { resolve(false); };
      } catch (e) {
        resolve(false);
      }
    });
  }

  function deleteDownloadByStreamUrl(streamUrl) {
    return getDownloadByStreamUrl(streamUrl).then(function(download) {
      if (!download) return false;
      return deleteDownloadById(download.id).then(function(ok) {
        if (ok && navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'DELETE_DOWNLOAD', url: streamUrl });
        }
        return ok;
      });
    });
  }

  function formatBytes(bytes) {
    var value = Number(bytes || 0);
    if (value <= 0) return '0 MB';
    var units = ['B', 'KB', 'MB', 'GB'];
    var idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx++;
    }
    return value.toFixed(idx === 0 ? 0 : 1) + ' ' + units[idx];
  }

  function formatDate(ts) {
    if (!ts) return 'Unbekannt';
    try {
      return new Date(ts).toLocaleString();
    } catch (e) {
      return 'Unbekannt';
    }
  }

  function findItemByStreamUrl(streamUrl) {
    var idx = filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; });
    if (idx >= 0) return { item: filteredItems[idx], index: idx };
    for (var i = 0; i < allItems.length; i++) {
      if (allItems[i].stream_url === streamUrl) return { item: allItems[i], index: -1 };
    }
    return null;
  }

  function sortDownloads(downloads, sortBy) {
    return downloads.slice().sort(function(a, b) {
      if (sortBy === 'oldest') return (a.timestamp || 0) - (b.timestamp || 0);
      if (sortBy === 'title') return String(a.title || '').localeCompare(String(b.title || ''));
      if (sortBy === 'size') return (b.size || 0) - (a.size || 0);
      return (b.timestamp || 0) - (a.timestamp || 0);
    });
  }

  function getAppDownloadUsage(downloads) {
    return (downloads || []).reduce(function(sum, d) {
      return sum + (d.status === 'ready' ? Number(d.size || 0) : 0);
    }, 0);
  }

  function estimateOfflineStorage(downloads) {
    var list = downloads || [];
    var info = {
      downloads: list,
      appUsage: getAppDownloadUsage(list),
      softLimit: OFFLINE_SOFT_LIMIT,
      browserUsage: null,
      browserQuota: null,
      persistent: null
    };
    var tasks = [];
    if (navigator.storage && navigator.storage.estimate) {
      tasks.push(
        navigator.storage.estimate().then(function(estimate) {
          info.browserUsage = estimate && estimate.usage ? estimate.usage : 0;
          info.browserQuota = estimate && estimate.quota ? estimate.quota : 0;
        }).catch(function() {})
      );
    }
    if (navigator.storage && navigator.storage.persisted) {
      tasks.push(
        navigator.storage.persisted().then(function(persistent) {
          info.persistent = !!persistent;
        }).catch(function() {})
      );
    }
    return Promise.all(tasks).then(function() { return info; });
  }

  function renderStorageSummary(info) {
    if (!info) return;
    var warn = info.appUsage >= info.softLimit * 0.8 ||
      (info.browserQuota && info.browserUsage >= info.browserQuota * 0.8);
    if (offlineStorageSummary) {
      offlineStorageSummary.classList.toggle('warn', !!warn);
      offlineStorageSummary.textContent = info.downloads.length
        ? info.downloads.length + ' Offline-Download' + (info.downloads.length !== 1 ? 's' : '') +
          ' · ' + formatBytes(info.appUsage) + ' lokal gespeichert'
        : 'Noch keine Offline-Downloads.';
    }
    if (offlineStorageDetail) {
      var parts = [
        'App-Budget ' + formatBytes(info.appUsage) + ' / ' + formatBytes(info.softLimit)
      ];
      if (info.browserQuota) {
        parts.push('Browser ' + formatBytes(info.browserUsage) + ' / ' + formatBytes(info.browserQuota));
      }
      if (info.persistent !== null) {
        parts.push(info.persistent ? 'Persistent aktiv' : 'Nicht persistent');
      }
      offlineStorageDetail.textContent = parts.join(' · ');
    }
    if (downloadedPill) {
      downloadedPill.textContent = 'Downloaded (' + info.downloads.length + ')';
      downloadedPill.classList.toggle('has-downloads', info.downloads.length > 0);
    }
    updateOfflineFolderCount();
  }

  function renderOfflineDownloadList(downloads) {
    if (!offlineDownloadList) return;
    if (!downloads.length) {
      offlineDownloadList.innerHTML = '<li class="empty-downloads">Noch keine Offline-Downloads gespeichert.</li>';
      return;
    }
    offlineDownloadList.innerHTML = downloads.map(function(download) {
      var thumbSrc = download.thumbnailUrl || FILE_PLACEHOLDER;
      var subtitle = download.artist || download.relativePath || '';
      var statusText = download.status === 'ready' ? 'Offline bereit' : (download.status || 'unbekannt');
      return '<li class="offline-download-item" data-stream-url="' + escHtml(download.streamUrl) + '">' +
        '<img class="offline-download-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="offline-download-meta">' +
          '<div class="offline-download-title">' + escHtml(download.title || 'Unbenannter Download') + '</div>' +
          '<div class="offline-download-sub">' + escHtml(subtitle) + '</div>' +
          '<div class="offline-download-size">' + escHtml(statusText) + ' · ' +
            escHtml(formatBytes(download.size || 0)) + ' · ' + escHtml(formatDate(download.timestamp)) + '</div>' +
        '</div>' +
        '<button class="offline-download-delete" data-stream-url="' + escHtml(download.streamUrl) + '" title="Entfernen">Entfernen</button>' +
      '</li>';
    }).join('');
    offlineDownloadList.querySelectorAll('.offline-download-item').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (e.target && e.target.classList && e.target.classList.contains('offline-download-delete')) return;
        playStoredDownload(el.dataset.streamUrl);
      });
    });
    offlineDownloadList.querySelectorAll('.offline-download-delete').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        deleteTrackDownload(btn.dataset.streamUrl);
      });
    });
  }

  function refreshOfflineLibrary() {
    return getAllDownloads().then(function(downloads) {
      /* If currently viewing the offline playlist, refresh it */
      if (currentPath === '__offline__') {
        var ready = downloads.filter(function(d) { return d.status === 'ready'; });
        var sortBy = offlineSort ? offlineSort.value : 'newest';
        var sorted = sortDownloads(ready, sortBy);
        var items = sorted.map(function(d) {
          return {
            title: d.title || 'Offline-Download',
            artist: d.artist || '',
            relative_path: d.relativePath || d.title || d.streamUrl,
            stream_url: d.streamUrl,
            thumbnail_url: d.thumbnailUrl || '',
            media_type: d.mediaType || ITEM_NOUN,
            rating: 0
          };
        });
        playlistItems = items;
        applyFilter();
        estimateOfflineStorage(ready).then(function(info) {
          if (info && info.appUsage > 0) {
            trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
              ' · ' + formatBytes(info.appUsage);
          }
        });
      }
      updateOfflineFolderCount();
      return downloads;
    });
  }

  function openOfflineLibrary() {
    getAllDownloads().then(function(downloads) {
      var ready = downloads.filter(function(d) { return d.status === 'ready'; });
      var sortBy = offlineSort ? offlineSort.value : 'newest';
      var sorted = sortDownloads(ready, sortBy);
      var items = sorted.map(function(d) {
        return {
          title: d.title || 'Offline-Download',
          artist: d.artist || '',
          relative_path: d.relativePath || d.title || d.streamUrl,
          stream_url: d.streamUrl,
          thumbnail_url: d.thumbnailUrl || '',
          media_type: d.mediaType || ITEM_NOUN,
          rating: 0
        };
      });
      currentPath = '__offline__';
      showPlaylist(items, false);
      headerTitle.textContent = 'Downloaded';
      backBtn.style.display = 'inline-block';
      estimateOfflineStorage(ready).then(function(info) {
        if (info && info.appUsage > 0) {
          trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
            ' · ' + formatBytes(info.appUsage);
        }
      });
    });
  }

  function closeOfflineLibrary() {
    if (currentPath === '__offline__') {
      currentPath = '';
      showFolderView();
    }
  }

  function updateOfflineFolderCount() {
    getAllDownloads().then(function(downloads) {
      var ready = downloads.filter(function(d) { return d.status === 'ready'; });
      var el = document.getElementById('offline-folder-count');
      if (el) {
        var n = ready.length;
        el.textContent = n + ' download' + (n !== 1 ? 's' : '');
      }
      if (downloadedPill) {
        downloadedPill.textContent = 'Downloaded (' + ready.length + ')';
        downloadedPill.classList.toggle('has-downloads', ready.length > 0);
      }
    });
  }

  /* ── Recently played section ── */
  function loadRecentlyPlayed() {
    var section = document.getElementById('recent-section');
    if (!section) return;
    fetch(RECENT_API_PATH + '?limit=10')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.items || d.items.length === 0) {
          section.hidden = true;
          return;
        }
        var scroll = section.querySelector('.recent-scroll');
        scroll.innerHTML = d.items.map(function(it) {
          var pct = Math.min(100, Math.max(0, it.progress_pct || 0));
          var thumb = it.thumbnail_url || FILE_PLACEHOLDER;
          var isPlaceholder = !it.thumbnail_url;
          var imgStyle = isPlaceholder ? ' style="object-fit:contain;padding:14px;opacity:.4"' : '';
          return '<div class="recent-card" data-path="' + escHtml(it.relative_path || '') + '"'
            + ' data-pos="' + (it.position_seconds || 0) + '" title="' + escHtml(it.title || '') + '">'
            + '<div class="recent-thumb-wrap">'
            + '<img class="recent-thumb" src="' + escHtml(thumb) + '" loading="lazy"' + imgStyle + '>'
            + (pct > 2 ? '<div class="recent-progress-bar" style="width:' + pct + '%"></div>' : '')
            + '</div>'
            + '<div class="recent-title">' + escHtml(it.title || it.relative_path || '') + '</div>'
            + '<div class="recent-sub">' + escHtml(it.artist || '') + '</div>'
            + '</div>';
        }).join('');
        section.hidden = false;
        /* attach click handlers */
        scroll.querySelectorAll('.recent-card').forEach(function(card) {
          card.addEventListener('click', function() {
            var path = card.dataset.path;
            var seekPos = parseFloat(card.dataset.pos) || 0;
            /* find item in the full allItems list */
            var found = null;
            for (var i = 0; i < allItems.length; i++) {
              if (allItems[i].relative_path === path) { found = allItems[i]; break; }
            }
            if (!found) return;
            /* navigate to the item's folder and play it */
            var folder = path.lastIndexOf('/') >= 0
              ? path.substring(0, path.lastIndexOf('/')) : '';
            currentPath = folder;
            inPlaylist = true;
            var folderItems = folder
              ? allItems.filter(function(it) {
                  return it.relative_path.startsWith(folder + '/') &&
                    it.relative_path.indexOf('/', folder.length + 1) < 0;
                })
              : allItems.filter(function(it) { return it.relative_path.indexOf('/') < 0; });
            if (!folderItems.length) folderItems = [found];
            var idx = 0;
            for (var j = 0; j < folderItems.length; j++) {
              if (folderItems[j].relative_path === path) { idx = j; break; }
            }
            showPlaylist(folderItems, false);
            playItem(found, idx);
            /* seek to saved position after canplay */
            if (seekPos > 2) {
              player.addEventListener('canplay', function onCp() {
                player.removeEventListener('canplay', onCp);
                player.currentTime = seekPos;
              }, { once: true });
            }
          });
        });
      })
      .catch(function() { if (section) section.hidden = true; });
  }



  function requestPersistentStorage() {
    if (!(navigator.storage && navigator.storage.persist)) return Promise.resolve(false);
    if (offlinePersistBtn) offlinePersistBtn.textContent = 'Prüfe persistenten Speicher…';
    return navigator.storage.persist().then(function(persistent) {
      if (offlinePersistBtn) {
        offlinePersistBtn.textContent = persistent ? 'Persistenter Speicher aktiv' : 'Persistenz nicht verfügbar';
      }
      return refreshOfflineLibrary().then(function() { return persistent; });
    }).catch(function() {
      if (offlinePersistBtn) offlinePersistBtn.textContent = 'Persistenz fehlgeschlagen';
      return false;
    });
  }

  function pruneOldDownloads(requiredBytes, protectedStreamUrl) {
    return getAllDownloads().then(function(downloads) {
      var total = getAppDownloadUsage(downloads);
      var candidates = downloads.filter(function(download) {
        return download.status === 'ready' && download.streamUrl !== protectedStreamUrl;
      }).sort(function(a, b) {
        return (a.timestamp || 0) - (b.timestamp || 0);
      });
      var victims = [];
      while (total + requiredBytes > OFFLINE_SOFT_LIMIT && candidates.length) {
        var victim = candidates.shift();
        victims.push(victim);
        total -= Number(victim.size || 0);
      }
      if (total + requiredBytes > OFFLINE_SOFT_LIMIT) return false;
      var chain = Promise.resolve();
      victims.forEach(function(victim) {
        chain = chain.then(function() { return deleteDownloadById(victim.id); });
      });
      return chain.then(function() { return true; });
    }).then(function(ok) {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
      return ok;
    });
  }

  function ensureStorageBudget(requiredBytes, protectedStreamUrl) {
    return getAllDownloads().then(function(downloads) {
      var total = getAppDownloadUsage(downloads);
      if (total + requiredBytes <= OFFLINE_SOFT_LIMIT) return true;
      return pruneOldDownloads(requiredBytes, protectedStreamUrl);
    });
  }

  function updateAllDownloadButtons() {
    if (!downloadDB) return;
    getAllDownloads().then(function(downloads) {
      var cached = {};
      downloads.forEach(function(d) {
        if (d.streamUrl && d.status === 'ready') cached[d.streamUrl] = true;
      });
      document.querySelectorAll('.track-dl-btn').forEach(function(btn) {
        var url = btn.dataset.streamUrl;
        btn.classList.remove('cached');
        if (!btn.classList.contains('downloading')) {
          btn.innerHTML = IC_DL;
          btn.title = 'Download';
        }
        if (cached[url]) {
          btn.classList.add('cached');
          btn.classList.remove('downloading');
          btn.innerHTML = IC_CHECK;
          btn.title = 'Offline gespeichert — klicken zum Entfernen';
        }
      });
    });
  }

  function downloadTrack(streamUrl, title, btn, meta) {
    if (!downloadDB) return;
    btn.classList.add('downloading');
    btn.classList.remove('cached');
    btn.textContent = '0%';
    btn.title = 'Download l\\u00e4uft \\u2014 klicken zum Abbrechen';

    var controller = new AbortController();
    activeDownloads[streamUrl] = controller;

    fetch(streamUrl, { signal: controller.signal }).then(function(response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var total = parseInt(response.headers.get('content-length'), 10) || 0;
      if (total > OFFLINE_SOFT_LIMIT) {
        throw new Error('Datei zu gro\\u00df f\\u00fcr Offline-Speicher (' + formatBytes(total) + ', max ' + formatBytes(OFFLINE_SOFT_LIMIT) + ')');
      }
      return Promise.resolve(total > 0 ? ensureStorageBudget(total, streamUrl) : true).then(function(ok) {
        if (!ok) throw new Error('Offline-Speicher voll \\u2014 l\\u00f6sche alte Downloads oder erh\\u00f6he den Speicher');
        var received = 0;
        var reader = response.body.getReader();
        var chunks = [];

        function pump() {
          return reader.read().then(function(result) {
            if (result.done) return;
            chunks.push(result.value);
            received += result.value.length;
            if (total > 0) {
              btn.textContent = Math.round(received / total * 100) + '%';
            }
            return pump();
          });
        }

        return pump().then(function() {
          var blob = new Blob(chunks, { type: response.headers.get('content-type') || 'application/octet-stream' });
          return ensureStorageBudget(blob.size, streamUrl).then(function(stillOk) {
            if (!stillOk) throw new Error('Offline-Speicher voll');
            return deleteDownloadByStreamUrl(streamUrl).then(function() {
              return new Promise(function(resolve, reject) {
                var tx = downloadDB.transaction('downloads', 'readwrite');
                var store = tx.objectStore('downloads');
                store.add({
                  streamUrl: streamUrl,
                  title: title,
                  artist: meta && meta.artist ? meta.artist : '',
                  relativePath: meta && meta.relativePath ? meta.relativePath : '',
                  thumbnailUrl: meta && meta.thumbnailUrl ? meta.thumbnailUrl : '',
                  mediaType: meta && meta.mediaType ? meta.mediaType : ITEM_NOUN,
                  blob: blob,
                  size: blob.size,
                  timestamp: Date.now(),
                  status: 'ready'
                });
                tx.oncomplete = resolve;
                tx.onerror = function() { reject(tx.error || new Error('IndexedDB write failed')); };
              });
            });
          });
        });
      });
    }).then(function() {
      delete activeDownloads[streamUrl];
      btn.classList.remove('downloading');
      btn.classList.add('cached');
      btn.innerHTML = IC_CHECK;
      btn.title = 'Offline gespeichert — klicken zum Entfernen';
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    }).catch(function(err) {
      delete activeDownloads[streamUrl];
      if (err && err.name === 'AbortError') return;
      console.error('Download failed:', err);
      btn.classList.remove('downloading');
      btn.classList.remove('cached');
      btn.innerHTML = IC_DL;
      btn.title = 'Download fehlgeschlagen';
      showToast(err && err.message ? err.message : 'Download fehlgeschlagen');
      refreshOfflineLibrary();
    });
  }

  function deleteTrackDownload(streamUrl, btn) {
    deleteDownloadByStreamUrl(streamUrl).then(function(deleted) {
      if (!deleted) return;
      if (btn) {
        btn.classList.remove('cached');
        btn.classList.remove('downloading');
        btn.innerHTML = IC_DL;
        btn.title = 'Download';
      }
      refreshOfflineLibrary();
      updateAllDownloadButtons();
    });
  }

  function checkIfMediaCached(streamUrl) {
    return getDownloadByStreamUrl(streamUrl).then(function(download) {
      return download && download.status === 'ready' && download.blob ? download : null;
    });
  }

  function getOfflineUrl(blob) {
    revokeOfflineUrl();
    currentOfflineUrl = URL.createObjectURL(blob);
    return currentOfflineUrl;
  }

  function playOfflineOrStream(streamUrl) {
    return checkIfMediaCached(streamUrl).then(function(download) {
      if (download && download.blob) {
        return {
          url: getOfflineUrl(download.blob),
          offline: true,
          fallbackUrl: streamUrl
        };
      }
      return {
        url: streamUrl,
        offline: false,
        fallbackUrl: streamUrl
      };
    });
  }

  function playStoredDownload(streamUrl) {
    getDownloadByStreamUrl(streamUrl).then(function(download) {
      if (!download) return;
      /* If currently in offline playlist, find track in filtered items */
      if (currentPath === '__offline__') {
        var offIdx = filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; });
        if (offIdx >= 0) { playTrack(offIdx); return; }
      }
      var match = findItemByStreamUrl(streamUrl);
      if (match) {
        playTrack(match.index >= 0 ? match.index : filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; }));
        if (match.index < 0) {
          playItem(match.item, -1);
        }
        return;
      }
      playItem({
        title: download.title || 'Offline-Download',
        artist: download.artist || '',
        relative_path: download.relativePath || download.title || streamUrl,
        stream_url: download.streamUrl,
        thumbnail_url: download.thumbnailUrl || '',
        media_type: download.mediaType || ITEM_NOUN,
        rating: 0
      }, -1);
    });
  }

  /* Listen for Service Worker download notifications */
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener('message', function(e) {
      if (e.data && (e.data.type === 'DOWNLOAD_CACHED' || e.data.type === 'DOWNLOAD_DELETED')) {
        updateAllDownloadButtons();
        refreshOfflineLibrary();
      }
    });
  }

  if (downloadedPill) downloadedPill.addEventListener('click', openOfflineLibrary);
  if (offlineClose) offlineClose.addEventListener('click', closeOfflineLibrary);
  if (offlineLibrary) {
    offlineLibrary.addEventListener('click', function(e) {
      if (e.target === offlineLibrary) closeOfflineLibrary();
    });
  }
  if (offlineSort) offlineSort.addEventListener('change', refreshOfflineLibrary);
  if (offlinePersistBtn) {
    if (!(navigator.storage && navigator.storage.persist)) {
      offlinePersistBtn.hidden = true;
    } else {
      offlinePersistBtn.addEventListener('click', requestPersistentStorage);
    }
  }
  if (offlinePruneBtn) {
    offlinePruneBtn.addEventListener('click', function() {
      pruneOldDownloads(0, currentStreamUrl);
    });
  }
  window.addEventListener('online', refreshOfflineLibrary);
  window.addEventListener('offline', refreshOfflineLibrary);

  /* ── Tools panel ── */
  var toolsPill = document.getElementById('tools-pill');
  var toolsBackdrop = document.getElementById('tools-panel-backdrop');
  var toolsClose = document.getElementById('tools-panel-close');
  var _toolInlineRatings = document.getElementById('tool-inline-ratings');
  var _toolDownloads = document.getElementById('tool-downloads');
  var _toolPlaylists = document.getElementById('tool-playlists');
  var _toolDuplicates = document.getElementById('tool-duplicates');
  var _dupeShowLink = document.getElementById('dupe-show-link');
  var _toolFileMover = document.getElementById('tool-file-mover');

  /* Load saved tool states from localStorage */
  var _toolState = JSON.parse(localStorage.getItem('ht-tools') || '{}');

  function _anyToolActive() {
    return !!_toolState.active && (!!_toolState.inlineRatings || !!_toolState.duplicates || !!_toolState.fileMover);
  }

  function _updateActivateBtn() {
    if (!_toolsActivateAll) return;
    var isOn = !!_toolState.active;
    _toolsActivateAll.textContent = isOn ? 'Tool-Modus deaktivieren' : 'Tool-Modus aktivieren';
    _toolsActivateAll.classList.toggle('tools-activate-all--active', isOn);
    _toolsActivateAll.title = isOn ? 'Tool-Modus ausschalten' : 'Tool-Modus mit den konfigurierten Einstellungen aktivieren';
  }

  function _applyToolState() {
    _updateActivateBtn();
    if (!_toolState.active) {
      /* Tool mode is off: hide all tool UI without changing saved preferences */
      document.body.classList.remove('tool-inline-ratings');
      document.body.classList.remove('tool-hide-downloads');
      document.body.classList.remove('tool-hide-playlists');
      document.body.classList.remove('tool-show-duplicates');
      document.body.classList.remove('tool-show-file-mover');
      if (_dupeShowLink) _dupeShowLink.style.display = 'none';
      if (toolsPill) toolsPill.classList.remove('has-active');
      /* Re-render to remove tool widgets from track list */
      if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
        showFolderView();
      } else if (inPlaylist) {
        applyViewMode();
        renderTracks(filteredItems);
      }
      return;
    }
    if (_toolState.inlineRatings) {
      document.body.classList.add('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = true;
    } else {
      document.body.classList.remove('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = false;
    }
    if (_toolState.downloads === false) {
      document.body.classList.add('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = false;
    } else {
      document.body.classList.remove('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = true;
    }
    if (_toolState.playlists === false) {
      document.body.classList.add('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = false;
    } else {
      document.body.classList.remove('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = true;
    }
    if (_toolState.duplicates) {
      document.body.classList.add('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = true;
      _ensureDupeMap();
      var dc = _getDupeCount();
      if (_dupeShowLink) {
        _dupeShowLink.textContent = dc > 0 ? dc + ' Duplikat-Gruppe' + (dc !== 1 ? 'n' : '') + ' gefunden \\u2014 anzeigen' : 'Keine Duplikate gefunden';
        _dupeShowLink.style.display = 'inline-block';
      }
    } else {
      document.body.classList.remove('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = false;
      if (_dupeShowLink) _dupeShowLink.style.display = 'none';
    }
    if (_toolState.fileMover) {
      document.body.classList.add('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = true;
    } else {
      document.body.classList.remove('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = false;
    }
    /* Update pill highlight */
    var anyActive = _anyToolActive();
    if (toolsPill) toolsPill.classList.toggle('has-active', anyActive);
    /* Re-render current view so folder names / view mode reflect new tool state */
    if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
      showFolderView();
    } else if (inPlaylist) {
      applyViewMode();
      renderTracks(filteredItems);
    }
  }

  function _saveToolState() {
    localStorage.setItem('ht-tools', JSON.stringify(_toolState));
    _applyToolState();
  }

  function openToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.removeAttribute('hidden');
  }
  function closeToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.setAttribute('hidden', '');
  }

  if (toolsPill) toolsPill.addEventListener('click', openToolsPanel);
  if (toolsClose) toolsClose.addEventListener('click', closeToolsPanel);
  if (toolsBackdrop) {
    toolsBackdrop.addEventListener('click', function(e) {
      if (e.target === toolsBackdrop) closeToolsPanel();
    });
  }
  var _dupePanelBackdrop = document.getElementById('dupe-panel-backdrop');
  var _dupePanelClose = document.getElementById('dupe-panel-close');
  var _dupePanelPlayAll = document.getElementById('dupe-panel-play-all');
  if (_dupePanelClose) _dupePanelClose.addEventListener('click', closeDupePanel);
  if (_dupePanelPlayAll) _dupePanelPlayAll.addEventListener('click', playDuplicates);
  if (_dupePanelBackdrop) {
    _dupePanelBackdrop.addEventListener('click', function(e) {
      if (e.target === _dupePanelBackdrop) closeDupePanel();
    });
  }
  if (_toolInlineRatings) {
    _toolInlineRatings.addEventListener('change', function() {
      _toolState.inlineRatings = _toolInlineRatings.checked;
      _saveToolState();
      /* Re-render current track list to add/remove inline stars */
      if (inPlaylist) applyFilter();
    });
  }
  if (_toolDownloads) {
    _toolDownloads.addEventListener('change', function() {
      _toolState.downloads = _toolDownloads.checked;
      _saveToolState();
    });
  }
  if (_toolPlaylists) {
    _toolPlaylists.addEventListener('change', function() {
      _toolState.playlists = _toolPlaylists.checked;
      _saveToolState();
    });
  }
  if (_toolDuplicates) {
    _toolDuplicates.addEventListener('change', function() {
      _toolState.duplicates = _toolDuplicates.checked;
      if (_toolDuplicates.checked) _ensureDupeMap();
      else _invalidateDupeMap();
      _saveToolState();
      /* Re-render to show/hide badges */
      if (inPlaylist) applyFilter();
    });
  }
  if (_dupeShowLink) {
    _dupeShowLink.addEventListener('click', function(e) {
      e.preventDefault();
      closeToolsPanel();
      openDupePanel();
    });
  }
  if (_toolFileMover) {
    _toolFileMover.addEventListener('change', function() {
      _toolState.fileMover = _toolFileMover.checked;
      _saveToolState();
      /* Re-render to show/hide move widgets */
      if (inPlaylist) applyFilter();
    });
  }
  var _toolsActivateAll = document.getElementById('tools-activate-all');
  if (_toolsActivateAll) {
    _toolsActivateAll.addEventListener('click', function() {
      _toolState.active = !_toolState.active;
      /* When activating: if duplicates tool is configured, ensure dupe map is ready */
      if (_toolState.active && _toolState.duplicates) _ensureDupeMap();
      /* When deactivating: invalidate dupe map to release memory */
      if (!_toolState.active) _invalidateDupeMap();
      _saveToolState();
      if (inPlaylist) applyFilter();
    });
  }
  _applyToolState();

  /* ── Inline track rating stars ── */
  function renderInlineRating(t, idx) {
    if (!RATING_WRITE_ENABLED) return '';
    var rounded = Math.round(t.rating || 0);
    var html = '<span class="track-inline-rating" data-index="' + idx + '">';
    for (var i = 1; i <= 5; i++) {
      html += '<button class="track-inline-rating-star' + (i <= rounded ? ' active' : '') +
        '" data-star="' + i + '" data-index="' + idx + '" title="' + i + (i === 1 ? ' Stern' : ' Sterne') + '">' +
        (i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY) + '</button>';
    }
    html += '</span>';
    return html;
  }

  function setInlineRating(idx, stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[idx];
    if (!t) return;
    var prevRating = t.rating || 0;
    fetch(RATING_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, rating: stars })
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) {
      if (!d || !d.ok) return;
      t.rating = d.rating;
      /* Update the inline stars in-place */
      var container = document.querySelector('.track-inline-rating[data-index="' + idx + '"]');
      if (container) {
        var rounded = Math.round(d.rating || 0);
        container.querySelectorAll('.track-inline-rating-star').forEach(function(btn) {
          var s = Number(btn.dataset.star);
          btn.className = 'track-inline-rating-star' + (s <= rounded ? ' active' : '');
          btn.innerHTML = s <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
        });
      }
      /* Also update player rating if this track is currently playing */
      if (currentIndex === idx) renderPlayerRating(d.rating);
      /* rebuild weighted shuffle queue so new rating is reflected */
      if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
      if (d.entry_id) {
        showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
      } else {
        showToast(stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben');
      }
    })
    .catch(function() {});
  }

  /* ── Duplicate detection (client-side) ── */
  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
  var _dupeMap = null;   /* Map<key, [itemIndex, ...]> — only groups with 2+ items */
  var _dupePaths = null;  /* Set<relative_path> — all paths that belong to a dupe group */

  function _normalizeStem(s) {
    if (!s) return '';
    s = s.replace(/&amp;/g, '&');
    s = s.replace(/\\(\\d{1,3}kbit_[A-Za-z]+\\)/gi, '');
    s = s.replace(/\\(Official.{0,8}Video\\)/gi, '');
    s = s.replace(/\\(\\w*\\.[a-zA-Z]{2,5}\\)/gi, '');
    s = s.replace(/\\w*\\.(?:com|net|org|co\\.uk|de|vu|ru|pl)/gi, '');
    s = s.replace(/(?<=\\W)(?:featuring|feat\\.|feat)\\W/gi, 'feat. ');
    s = s.replace(/(?<=\\W)(?:produced by|produced|prod\\. by|prod by|prod\\.|prod)\\W/gi, 'prod. ');
    s = s.replace(/(?<=(?:\\W|\\(|\\[))(?:vs\\.|vs|versus)/gi, 'vs. ');
    s = s.replace(/\\(\\s*\\)|\\[\\s*\\]/g, '');
    s = s.replace(/ {2,}/g, ' ');
    return s.trim().toLowerCase();
  }

  function _dupeKey(item) {
    /* Build a stable key from artist + title — strip remix/version keywords, remove non-word chars.
       Artist is included so that "Blümchen - Nur Geträumt" and "Nena - Nur Geträumt"
       are NOT considered duplicates. Duplicates must match artist, title AND remix version. */
    var raw = item.title || '';
    if (!raw) {
      var rp = item.relative_path || '';
      var sl = rp.lastIndexOf('/');
      raw = sl >= 0 ? rp.substring(sl + 1) : rp;
      var dot = raw.lastIndexOf('.');
      if (dot > 0) raw = raw.substring(0, dot);
    }
    var cleaned = _normalizeStem(raw);
    /* Strip common download-duplicate suffixes: _2, (2), -2, _copy, - Copy, (copy) etc. */
    cleaned = cleaned.replace(/[\\s_-]*\\(?(?:copy|kopie)\\)?\\s*$/i, '');
    cleaned = cleaned.replace(/[\\s_-]+\\d{1,2}\\s*$/, '');
    cleaned = cleaned.replace(/\\s*\\(\\d{1,2}\\)\\s*$/, '');
    cleaned = cleaned.replace(/\\s*\\[\\d{1,2}\\]\\s*$/, '');
    /* Split on common separators */
    var parts = cleaned.split(/feat\\.|prod\\.|vs\\.|\\(|\\[| - |, | & |\\)|\\]/i);
    /* Remove music keywords aggressively */
    parts = parts.map(function(p) {
      return p.replace(/original|official|extended|radio|vocal|edit|remix|mix|version|release|remaster|remastered|live|acoustic|instrumental|explicit|clean/gi, '');
    });
    /* Strip non-word characters and filter short parts */
    parts = parts.map(function(p) { return p.replace(/[^a-z0-9]/gi, ''); });
    parts = parts.filter(function(p) { return p.length > 2; });
    /* Deduplicate and sort for stable key */
    var seen = {};
    var unique = [];
    parts.forEach(function(p) { if (!seen[p]) { seen[p] = true; unique.push(p); } });
    unique.sort();
    var titleKey = unique.join('|');
    /* Include the artist to prevent false positives across different artists */
    var artistRaw = (item.artist || '').toLowerCase().replace(/[^a-z0-9]/gi, '');
    if (artistRaw.length > 2) titleKey = artistRaw + '::' + titleKey;
    return titleKey;
  }

  function _buildDuplicateMap() {
    var map = {};
    allItems.forEach(function(item, i) {
      var key = _dupeKey(item);
      if (!key) return;
      if (!map[key]) map[key] = [];
      map[key].push(i);
    });
    /* Keep only groups with 2+ items */
    _dupeMap = {};
    _dupePaths = new Set();
    var keys = Object.keys(map);
    for (var k = 0; k < keys.length; k++) {
      if (map[keys[k]].length > 1) {
        _dupeMap[keys[k]] = map[keys[k]];
        map[keys[k]].forEach(function(idx) {
          var rp = allItems[idx] ? allItems[idx].relative_path : null;
          if (rp) _dupePaths.add(rp);
        });
      }
    }
  }

  function _invalidateDupeMap() {
    _dupeMap = null;
    _dupePaths = null;
  }

  function _ensureDupeMap() {
    if (!_dupeMap) _buildDuplicateMap();
  }

  function _getDupeCount() {
    _ensureDupeMap();
    return Object.keys(_dupeMap).length;
  }

  function openDupePanel() {
    _ensureDupeMap();
    var backdrop = document.getElementById('dupe-panel-backdrop');
    if (!backdrop) return;
    var body = document.getElementById('dupe-panel-body');
    if (!body) return;
    var keys = Object.keys(_dupeMap);
    if (keys.length === 0) {
      body.innerHTML = '<div style="text-align:center;color:var(--sub);padding:2rem 0">Keine Duplikate gefunden.</div>';
    } else {
      var html = '';
      keys.forEach(function(key) {
        var indices = _dupeMap[key];
        var firstTitle = allItems[indices[0]] ? (allItems[indices[0]].title || key) : key;
        html += '<div class="dupe-group">';
        html += '<div class="dupe-group-header">' + IC_DUPLICATE +
          '<span>' + escHtml(firstTitle) + '</span>' +
          '<span class="dupe-group-count">(' + indices.length + 'x)</span></div>';
        indices.forEach(function(idx) {
          var t = allItems[idx];
          if (!t) return;
          var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
          var folder = '';
          var sl = (t.relative_path || '').lastIndexOf('/');
          if (sl > 0) folder = t.relative_path.substring(0, sl);
          html += '<div class="dupe-group-item" data-all-index="' + idx + '">' +
            '<img src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
            '<div class="dupe-group-item-info">' +
              '<div class="dupe-group-item-title">' + escHtml(t.title || t.relative_path) + '</div>' +
              '<div class="dupe-group-item-path">' + escHtml(folder || t.relative_path) + '</div>' +
            '</div>' +
            '<button class="dupe-trash-btn" data-all-index="' + idx + '" title="In den Papierkorb verschieben">' + IC_TRASH + '</button>' +
            '</div>';
        });
        html += '</div>';
      });
      body.innerHTML = html;
      /* Wire up trash buttons */
      body.querySelectorAll('.dupe-trash-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          var ai = Number(btn.dataset.allIndex);
          _deleteDuplicateFile(ai);
        });
      });
      /* Wire up clicks to play */
      body.querySelectorAll('.dupe-group-item').forEach(function(el) {
        el.addEventListener('click', function() {
          var ai = Number(el.dataset.allIndex);
          var t = allItems[ai];
          if (!t) return;
          closeDupePanel();
          /* Navigate to folder and play */
          var sl = (t.relative_path || '').lastIndexOf('/');
          if (sl > 0) {
            var folder = t.relative_path.substring(0, sl);
            var items = itemsUnder(folder);
            showPlaylist(items, folder);
            var localIdx = -1;
            for (var j = 0; j < filteredItems.length; j++) {
              if (filteredItems[j].relative_path === t.relative_path) { localIdx = j; break; }
            }
            if (localIdx >= 0) playTrack(localIdx);
          }
        });
      });
    }
    /* Update subtitle */
    var sub = document.getElementById('dupe-panel-subtitle');
    if (sub) sub.textContent = keys.length + ' Duplikat-Gruppe' + (keys.length !== 1 ? 'n' : '') +
      ' (' + (_dupePaths ? _dupePaths.size : 0) + ' Dateien)';
    backdrop.removeAttribute('hidden');
  }

  function closeDupePanel() {
    var backdrop = document.getElementById('dupe-panel-backdrop');
    if (backdrop) backdrop.setAttribute('hidden', '');
  }

  function playDuplicates() {
    _ensureDupeMap();
    var keys = Object.keys(_dupeMap);
    if (!keys.length) { showToast('Keine Duplikate gefunden'); return; }
    /* Collect all items from dupe groups, grouped by key for natural listening order */
    var dupeItems = [];
    keys.forEach(function(key) {
      _dupeMap[key].forEach(function(idx) {
        var t = allItems[idx];
        if (t) dupeItems.push(t);
      });
    });
    if (!dupeItems.length) return;
    closeDupePanel();
    /* Show as virtual playlist */
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__duplicates__';
    currentPath = '';
    playlistItems = dupeItems;
    headerTitle.textContent = 'Duplikate (' + keys.length + ' Gruppen)';
    backBtn.style.display = 'inline-block';
    playAllBtn.style.display = 'none';
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    filterBar.classList.add('fb-scroll-hidden');
    playerBar.classList.remove('view-hidden');
    _hideGlobalSearch();
    _initFilterBarScrollReveal();
    searchInput.value = '';
    currentIndex = -1;
    renderBreadcrumb();
    applyFilter();
    if (shuffleMode) rebuildShuffleQueue(0);
  }

  function _deleteDuplicateFile(allIndex) {
    var t = allItems[allIndex];
    if (!t) return;
    var name = t.title || t.relative_path;
    if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
    /* Check if this track is the currently playing one */
    var playingFilteredIdx = -1;
    if (currentIndex >= 0 && currentIndex < filteredItems.length &&
        filteredItems[currentIndex].relative_path === t.relative_path) {
      playingFilteredIdx = currentIndex;
    }
    var wasBefore = false;
    if (playingFilteredIdx < 0 && currentIndex >= 0) {
      for (var fi = 0; fi < currentIndex && fi < filteredItems.length; fi++) {
        if (filteredItems[fi].relative_path === t.relative_path) { wasBefore = true; break; }
      }
    }
    fetch(DELETE_API_PATH, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: t.relative_path})
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Fehler'); });
      return r.json();
    }).then(function() {
      /* Remove item from allItems */
      allItems.splice(allIndex, 1);
      _invalidateDupeMap();
      _invalidateFolderCache();
      /* Adjust currentIndex */
      if (wasBefore) {
        currentIndex = Math.max(0, currentIndex - 1);
      }
      showToast('Datei gel\\u00f6scht: ' + name);
      /* Re-render the dupe panel with updated data */
      openDupePanel();
      /* If the playing track was deleted, advance to next */
      if (playingFilteredIdx >= 0 && filteredItems.length > 0) {
        var ni = Math.min(currentIndex, filteredItems.length - 1);
        playTrack(ni);
      }
    }).catch(function(err) {
      showToast('L\\u00f6schen fehlgeschlagen: ' + (err.message || err));
    });
  }

  function _deleteTrackFromList(filteredIdx) {
    var t = filteredItems[filteredIdx];
    if (!t) return;
    var name = t.title || t.relative_path;
    if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
    var wasCurrentlyPlaying = (filteredIdx === currentIndex);
    var wasBefore = (currentIndex >= 0 && filteredIdx < currentIndex);
    fetch(DELETE_API_PATH, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: t.relative_path})
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Fehler'); });
      return r.json();
    }).then(function() {
      allItems = allItems.filter(function(it) { return it.relative_path !== t.relative_path; });
      _invalidateDupeMap();
      _invalidateFolderCache();
      /* Adjust currentIndex so the player stays on the right track */
      if (wasBefore) {
        currentIndex = Math.max(0, currentIndex - 1);
      } else if (wasCurrentlyPlaying) {
        /* Will point to the next song (which shifted into our slot) */
        if (currentIndex >= filteredItems.length - 1) currentIndex = Math.max(0, currentIndex - 1);
      }
      showToast('Datei gel\\u00f6scht: ' + name);
      if (inPlaylist) {
        var items = itemsUnder(currentPath);
        if (items.length) { playlistItems = items; applyFilter(); }
        else { showFolderView(); }
      } else { showFolderView(); }
      /* If the playing track was deleted, advance to the next one */
      if (wasCurrentlyPlaying && filteredItems.length > 0) {
        playTrack(Math.min(currentIndex, filteredItems.length - 1));
      }
    }).catch(function(err) {
      showToast('L\\u00f6schen fehlgeschlagen: ' + (err.message || err));
    });
  }

  /* ── File mover (move to folder) ── */
  var _MOVE_RECENT_KEY = 'ht-move-recent';
  var _allFoldersCache = null;

  function _getRecentMoveTargets() {
    try { return JSON.parse(localStorage.getItem(_MOVE_RECENT_KEY) || '[]').slice(0, 4); }
    catch(e) { return []; }
  }

  function _saveRecentMoveTarget(folder) {
    var recent = _getRecentMoveTargets().filter(function(f) { return f !== folder; });
    recent.unshift(folder);
    if (recent.length > 4) recent = recent.slice(0, 4);
    try { localStorage.setItem(_MOVE_RECENT_KEY, JSON.stringify(recent)); } catch(e) {}
  }

  function _getAllFolders() {
    if (_allFoldersCache) return _allFoldersCache;
    var set = {};
    allItems.forEach(function(it) {
      var sl = it.relative_path.indexOf('/');
      if (sl > 0) set[it.relative_path.substring(0, sl)] = true;
    });
    _allFoldersCache = Object.keys(set).sort(function(a, b) { return a.localeCompare(b); });
    return _allFoldersCache;
  }

  function _invalidateFolderCache() { _allFoldersCache = null; }

  function _currentFolderOf(item) {
    var rp = item.relative_path || '';
    var sl = rp.indexOf('/');
    return sl > 0 ? rp.substring(0, sl) : '';
  }

  function renderMoveWidget(t, idx) {
    var curFolder = _currentFolderOf(t);
    var recent = _getRecentMoveTargets();
    var allF = _getAllFolders();
    /* Build 4 quick-pick folders: MRU first, fill with allFolders */
    var picks = recent.slice(0, 4);
    if (picks.length < 4) {
      var seen = {};
      picks.forEach(function(p) { seen[p] = true; });
      for (var fi = 0; fi < allF.length && picks.length < 4; fi++) {
        if (!seen[allF[fi]]) { picks.push(allF[fi]); seen[allF[fi]] = true; }
      }
    }
    var html = '<span class="track-move-widget" data-index="' + idx + '">';
    /* 2x2 quick-pick grid — always 4 buttons */
    html += '<span class="move-quick-grid">';
    for (var i = 0; i < Math.min(4, picks.length); i++) {
      var isCur = picks[i] === curFolder;
      html += '<button class="move-quick-btn' + (isCur ? ' is-current' : '') +
        '" data-target="' + escHtml(picks[i]) +
        '" data-index="' + idx + '" title="Verschieben nach: ' + escHtml(picks[i]) + '">' +
        escHtml(picks[i]) + '</button>';
    }
    html += '</span>';
    /* Dropdown with all folders */
    html += '<select class="move-folder-select" data-index="' + idx + '">';
    html += '<option value="">Ordner\u2026</option>';
    allF.forEach(function(f) {
      html += '<option value="' + escHtml(f) + '"' + (f === curFolder ? ' disabled' : '') + '>' + escHtml(f) + '</option>';
    });
    html += '</select>';
    html += '</span>';
    return html;
  }

  function moveFileToFolder(idx, targetFolder) {
    var t = filteredItems[idx];
    if (!t) return;
    var curFolder = _currentFolderOf(t);
    if (targetFolder === curFolder) { showToast('Datei ist bereits in diesem Ordner'); return; }
    fetch(MOVE_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, target_folder: targetFolder })
    })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || 'Move failed'); });
      return r.json();
    })
    .then(function(d) {
      if (!d || !d.ok) return;
      _saveRecentMoveTarget(targetFolder);
      /* Update allItems in-place */
      for (var i = 0; i < allItems.length; i++) {
        if (allItems[i].relative_path === t.relative_path) {
          allItems[i] = Object.assign({}, allItems[i], {
            relative_path: d.new_path,
            stream_url: allItems[i].stream_url.replace(encodeURIComponent(t.relative_path), encodeURIComponent(d.new_path)),
            artist: targetFolder
          });
          break;
        }
      }
      _invalidateDupeMap();
      _invalidateFolderCache();
      /* Show a ghost at the item's current position: dimmed + target hint.
         The ghost stays visible until the user navigates away or changes filters.
         This lets the user verify and—if needed—correct a wrong move before
         the list refreshes. */
      var ghostItems = filteredItems.slice();
      ghostItems[idx] = Object.assign({}, t, { _movedTo: targetFolder });
      renderTracks(ghostItems);
      showToast('Verschoben nach ' + targetFolder);
    })
    .catch(function(err) { showToast('Fehler: ' + (err.message || 'Verschieben fehlgeschlagen')); });
  }

  /* ── playback ── */
  /* Background playback for video — three layers of defence:
     ─────────────────────────────────────────────────────────
     PROBLEM: Mobile browsers (especially iOS Safari) pause <video>
     elements **before** the visibilitychange event fires.  So checking
     `!player.paused` inside that handler is already too late — the
     video is paused.  And `requestPictureInPicture()` requires a
     user-gesture, so calling it from visibilitychange is rejected.

     STRATEGY:
     1. **`wasPlaying` flag** — set on `playing` event, cleared only by
        intentional user-pause.  The browser's auto-pause does NOT
        clear it.  visibilitychange checks `wasPlaying` instead of
        `!player.paused`.
     2. **Hidden <audio> with `muted:true`** — plays the same source
        silently alongside the video.  Because it is already actively
        playing (started from user-gesture), iOS keeps it alive when
        backgrounded.  On visibilitychange we unmute it so audio
        continues seamlessly.
        NOTE: iOS ignores `volume` (always 1), so we MUST use `muted`
        to prevent double-audio in the foreground.
     3. **`autopictureinpicture` attribute** — Safari/WebKit honours
        this and enters PiP automatically when the page backgrounds.
        No user-gesture needed.  The manual PiP button works on all
        browsers that support the API. */
  var bgAudio = null;
  var bgSyncTimer = null;
  var isVideoPlayer = player.tagName === 'VIDEO';
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var pipActive = false;
  var wasPlaying = false;
  var btnPip = document.getElementById('btn-pip');

  /* Track intentional playback state — survives browser auto-pause */
  player.addEventListener('playing', function() { wasPlaying = true; });

  /* Show PiP button only when the browser supports it for this player */
  var pipSupported = isVideoPlayer && (
    document.pictureInPictureEnabled ||
    (typeof player.webkitSupportsPresentationMode === 'function' &&
     player.webkitSupportsPresentationMode('picture-in-picture'))
  );
  if (pipSupported && btnPip) btnPip.hidden = false;

  /* Enable Safari's automatic PiP on page background */
  if (isVideoPlayer) {
    player.setAttribute('autopictureinpicture', '');
  }

  function requestPiP() {
    if (!pipSupported || pipActive) return Promise.resolve();
    if (player.requestPictureInPicture) {
      return player.requestPictureInPicture().then(function() {
        pipActive = true;
        if (btnPip) btnPip.classList.add('active');
      }).catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('picture-in-picture');
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
      return Promise.resolve();
    }
    return Promise.resolve();
  }

  function exitPiP() {
    if (!pipActive) return;
    if (document.exitPictureInPicture && document.pictureInPictureElement) {
      document.exitPictureInPicture().catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('inline');
    }
    pipActive = false;
    if (btnPip) btnPip.classList.remove('active');
  }

  /* Track PiP state changes from native controls */
  if (isVideoPlayer) {
    player.addEventListener('enterpictureinpicture', function() {
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
    });
    player.addEventListener('leavepictureinpicture', function() {
      pipActive = false;
      if (btnPip) btnPip.classList.remove('active');
      /* If user closed PiP but wasPlaying, resume inline */
      if (wasPlaying && !document.hidden) {
        player.play().catch(function() {});
      }
    });
  }

  /* Manual PiP toggle button */
  if (btnPip) {
    btnPip.addEventListener('click', function() {
      if (pipActive) { exitPiP(); } else { requestPiP(); }
    });
  }

  /* Fullscreen button — uses native fullscreen or iOS webkitEnterFullscreen */
  var btnFs = document.getElementById('btn-fs');
  var fsSupported = isVideoPlayer && (
    document.fullscreenEnabled || document.webkitFullscreenEnabled ||
    typeof player.webkitEnterFullscreen === 'function'
  );
  if (fsSupported && btnFs) btnFs.hidden = false;
  if (btnFs) {
    btnFs.addEventListener('click', function() {
      if (player.requestFullscreen) {
        player.requestFullscreen().catch(function() {});
      } else if (player.webkitRequestFullscreen) {
        player.webkitRequestFullscreen();
      }
    });
  }

  function ensureBgAudio() {
    if (bgAudio) return bgAudio;
    bgAudio = document.createElement('audio');
    bgAudio.style.display = 'none';
    bgAudio.preload = 'auto';
    bgAudio.playsInline = true;
    bgAudio.muted = true;
    document.body.appendChild(bgAudio);
    /* When bg audio track ends, advance to next */
    bgAudio.addEventListener('ended', function() {
      playNextItem();
    });
    return bgAudio;
  }

  /* Is bg audio currently the active (unmuted) source? */
  function bgAudioIsActive() {
    return bgAudio && !bgAudio.muted && !bgAudio.paused;
  }

  /* Start the hidden <audio> muted, mirroring the video source.
     The play() call happens inside user-initiated playback so the
     browser allows it.  Because the element is already in a playing
     state, unmuting it later in visibilitychange works instantly. */
  function startBgMirror() {
    if (!isVideoPlayer) return;
    var bg = ensureBgAudio();
    if (bg.src !== player.src) {
      bg.src = player.src;
    }
    bg.currentTime = player.currentTime;
    bg.muted = true;
    bg.play().catch(function() {});
    /* keep bg audio roughly in sync while video plays */
    stopBgSync();
    bgSyncTimer = setInterval(function() {
      if (!bgAudio || !bgAudio.muted) return;
      if (!player.paused && Math.abs(bgAudio.currentTime - player.currentTime) > 0.5) {
        bgAudio.currentTime = player.currentTime;
      }
    }, 2000);
  }

  function stopBgSync() {
    if (bgSyncTimer) { clearInterval(bgSyncTimer); bgSyncTimer = null; }
  }

  /* ── Visibility change — the core background handler ──
     Uses `wasPlaying` instead of `!player.paused` because the browser
     has already paused the video by the time this fires on mobile. */
  document.addEventListener('visibilitychange', function() {
    if (!isVideoPlayer) return;
    if (document.hidden && wasPlaying) {
      /* App going to background — explicitly pause the video to prevent
         double audio on desktop (desktop browsers do NOT auto-pause video).
         On mobile, the browser already paused it so this is a no-op. */
      player.pause();
      if (bgAudio && !bgAudio.paused) {
        bgAudio.currentTime = player.currentTime;
        bgAudio.muted = false;
      }
      /* Signal to OS that playback is ongoing */
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'playing';
      }
    } else if (!document.hidden && wasPlaying) {
      /* App coming back to foreground */
      if (pipActive) exitPiP();
      if (bgAudio && !bgAudio.muted) {
        /* Sync video to where bg audio continued, resume video */
        player.currentTime = bgAudio.currentTime;
        player.play().catch(function() {});
        bgAudio.muted = true;
      } else if (player.paused) {
        /* No bg audio ran — just resume the video */
        player.play().catch(function() {});
      }
    }
  });

  /* Return whichever element is currently driving playback */
  function activeMedia() {
    if (bgAudioIsActive()) return bgAudio;
    return player;
  }

  /* Media Session API — lock screen controls & background playback signal */
  function updateMediaSession(t) {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title,
      artist: t.artist || '',
      album: ITEM_NOUN === 'video' ? 'hometools video' : 'hometools audio',
      artwork: [{ src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
                { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }]
    });
    navigator.mediaSession.setActionHandler('play', function() {
      var m = activeMedia();
      m.play();
      wasPlaying = true;
    });
    navigator.mediaSession.setActionHandler('pause', function() {
      /* Lockscreen pause = intentional user pause */
      wasPlaying = false;
      var m = activeMedia();
      m.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    });
    navigator.mediaSession.setActionHandler('previoustrack', function() {
      playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
    });
    navigator.mediaSession.setActionHandler('nexttrack', function() {
      playNextItem();
    });
    try {
      navigator.mediaSession.setActionHandler('seekto', function(details) {
        var m = activeMedia();
        m.currentTime = details.seekTime;
      });
    } catch(e) {}
  }

  function playItem(t, index) {
    currentIndex = typeof index === 'number' ? index : -1;
    currentStreamUrl = t.stream_url || '';

    /* Sync shuffle queue position to the chosen index */
    if (shuffleMode && shuffleQueue.length && currentIndex >= 0) {
      var qpos = shuffleQueue.indexOf(currentIndex);
      if (qpos >= 0) shufflePos = qpos;
      else { shuffleQueue.unshift(currentIndex); shufflePos = 0; }
    }

    /* Reset bg audio for new track */
    stopBgSync();
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; bgAudio.removeAttribute('src'); }
    _xfadeCleanup();
    player.volume = 1;
    wasPlaying = false;
    revokeOfflineUrl();

    function onPlaySuccess() {
      btnPlay.innerHTML = IC_PAUSE;
      startBgMirror();
    }

    function retryAfterCanPlay() {
      player.addEventListener('canplay', function() {
        player.play().then(onPlaySuccess).catch(function(e) {
          console.error('playTrack retry also failed:', e);
          btnPlay.innerHTML = IC_PLAY;
        });
      }, { once: true });
    }

    function beginPlayback(playback) {
      player.src = playback.url;
      player.load();
      player.play().then(onPlaySuccess).catch(function(err) {
        if (playback.offline) {
          console.warn('Offline playback failed, falling back to stream:', err);
          revokeOfflineUrl();
          player.src = playback.fallbackUrl;
          player.load();
          player.play().then(onPlaySuccess).catch(function(fallbackErr) {
            console.warn('Stream fallback play() failed, waiting for canplay:', fallbackErr);
            retryAfterCanPlay();
          });
          return;
        }
        console.warn('playTrack play() failed, waiting for canplay:', err);
        retryAfterCanPlay();
      });
      generateWaveform(playback.url);
    }

    playerTitle.textContent = t.title;
    playerArtist.textContent = t.artist || t.relative_path;
    if (t.thumbnail_url) {
      playerThumb.src = t.thumbnail_lg_url || t.thumbnail_url;
      playerThumb.style.display = '';
    } else {
      playerThumb.src = FILE_PLACEHOLDER;
      playerThumb.style.display = '';
    }
    btnPlay.innerHTML = IC_PAUSE;
    playerBar.classList.remove('view-hidden');
    /* In video mode: open the overlay and sync the mini-bar title/thumb */
    if (isVideoMode) {
      openVideoOverlay();
      _syncMiniBar(t);
      if (videoOverlayTitleText) videoOverlayTitleText.textContent = t.title || '';
    }
    /* Show video player element before playback starts — the CSS sets
       #player { display:none }, so we must override with inline block */
    if (player.tagName === 'VIDEO') player.style.display = 'block';
    markActive();
    updateMediaSession(t);
    renderPlayerRating(t.rating || 0);
    refreshMetadata(t);
    /* Auto-update lyrics panel if currently open */
    if (LYRICS_ENABLED && _lyricsOpen) openLyricsPanel(t.relative_path || '', t.title);

    /* playback progress: track current item and try to resume */
    clearTimeout(_progressTimer);
    _progressRelPath = t.relative_path || '';
    if (AUTO_RESUME_ENABLED) loadAndSeekProgress(_progressRelPath);

    /* load sprite sheet for video scrubber preview */
    loadSpriteData(t.relative_path || '');

    playOfflineOrStream(t.stream_url)
      .then(beginPlayback)
      .catch(function() {
        beginPlayback({ url: t.stream_url, offline: false, fallbackUrl: t.stream_url });
      });
  }

  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    playItem(filteredItems[index], index);
  }

  function refreshMetadata(t) {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var metaUrl = base + '/metadata?path=' + encodeURIComponent(t.relative_path);
    fetch(metaUrl)
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta) return;
        var changed = false;
        if (meta.title && meta.title !== t.title) {
          t.title = meta.title;
          playerTitle.textContent = meta.title;
          changed = true;
        }
        if (meta.artist && meta.artist !== t.artist) {
          t.artist = meta.artist;
          playerArtist.textContent = meta.artist;
          changed = true;
        }
        if (typeof meta.rating === 'number') {
          t.rating = meta.rating;
          renderPlayerRating(meta.rating);
        }
        if (changed) {
          updateMediaSession(t);
          renderTracks(filteredItems);
          markActive();
        }
      })
      .catch(function() {});
  }

  function togglePlay() {
    if (currentIndex < 0 && filteredItems.length) { playTrack(0); return; }
    if (player.paused) {
      /* If bg audio was driving playback (came back from background), sync first */
      if (bgAudio && !bgAudio.muted) {
        player.currentTime = bgAudio.currentTime;
        bgAudio.muted = true;
      }
      player.play().then(function() { startBgMirror(); }).catch(function() {});
      btnPlay.innerHTML = IC_PAUSE;
    } else {
      /* Intentional user pause — clear wasPlaying */
      wasPlaying = false;
      player.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
      stopBgSync();
      btnPlay.innerHTML = IC_PLAY;
    }
  }

  /* ── Shuffle logic ── */
  /* Fisher-Yates shuffle of an array in place */
  function fisherYates(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }

  /* Build a weighted shuffle queue: items with higher rating appear more often.
     Rating 0 → weight 1, Rating 5 → weight 6. Items with no rating → weight 1. */
  function buildWeightedQueue(items) {
    var pool = [];
    items.forEach(function(t, idx) {
      var w = Math.max(1, Math.round((t.rating || 0) + 1));
      for (var i = 0; i < w; i++) pool.push(idx);
    });
    return fisherYates(pool);
  }

  /* Build a simple uniform shuffle queue */
  function buildNormalQueue(items) {
    var indices = items.map(function(_, i) { return i; });
    return fisherYates(indices);
  }

  /* Rebuild shuffle queue — called whenever filteredItems or shuffleMode changes */
  function rebuildShuffleQueue(startIndex) {
    if (!shuffleMode || !filteredItems.length) { shuffleQueue = []; shufflePos = -1; return; }
    var rawQueue = shuffleMode === 'weighted'
      ? buildWeightedQueue(filteredItems)
      : buildNormalQueue(filteredItems);
    shuffleQueue = rawQueue; /* already filteredItems indices */
    /* Put startIndex first so current track leads */
    if (typeof startIndex === 'number' && startIndex >= 0) {
      var pos = shuffleQueue.indexOf(startIndex);
      if (pos > 0) {
        shuffleQueue.splice(pos, 1);
        shuffleQueue.unshift(startIndex);
      }
    }
    shufflePos = 0;
  }

  /* Next index respecting shuffle state */
  function nextIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos + 1) % shuffleQueue.length;
      /* Replenish weighted queue when exhausted */
      if (shufflePos === 0 && shuffleMode === 'weighted') {
        shuffleQueue = buildWeightedQueue(filteredItems);
      }
      return shuffleQueue[shufflePos];
    }
    /* Sequential */
    var ni = currentIndex + 1;
    if (ni >= filteredItems.length) return repeatMode === 'all' ? 0 : -1;
    return ni;
  }

  /* First playable index — kept for API compat, returns 0 */
  function _firstPlayableIndex() { return 0; }

  /* Prev index respecting shuffle state */
  function prevIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos - 1 + shuffleQueue.length) % shuffleQueue.length;
      return shuffleQueue[shufflePos];
    }
    /* Sequential */
    var pi = currentIndex - 1;
    if (pi < 0) {
      if (repeatMode === 'all') return filteredItems.length - 1;
      return 0;
    }
    return pi;
  }

  /* Toggle shuffle mode: off → normal → weighted → off */
  function cycleShuffle() {
    if (!shuffleMode) {
      shuffleMode = 'normal';
    } else if (shuffleMode === 'normal') {
      shuffleMode = 'weighted';
    } else {
      shuffleMode = false;
    }
    localStorage.setItem('ht-shuffle-mode', shuffleMode || '');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
  }

  /* Activate weighted shuffle directly (long-press) */
  function activateWeightedShuffle() {
    shuffleMode = 'weighted';
    localStorage.setItem('ht-shuffle-mode', 'weighted');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    showToast('Gewichteter Shuffle aktiv (nach Bewertung)');
  }

  function updateShuffleBtn() {
    if (!btnShuffle) return;
    btnShuffle.classList.toggle('shuffle-active', !!shuffleMode);
    btnShuffle.classList.toggle('shuffle-weighted', shuffleMode === 'weighted');
    btnShuffle.title = shuffleMode === 'weighted'
      ? 'Shuffle (gewichtet nach Bewertung) — Long Press für Aus'
      : shuffleMode === 'normal'
        ? 'Shuffle (zufällig) — Klick für gewichtet, Long Press für Aus'
        : 'Shuffle aktivieren';
  }

  /* ── Repeat mode: off → all → one → off ── */
  function cycleRepeat() {
    if (!repeatMode) {
      repeatMode = 'all';
    } else if (repeatMode === 'all') {
      repeatMode = 'one';
    } else {
      repeatMode = false;
    }
    localStorage.setItem('ht-repeat-mode', repeatMode || '');
    updateRepeatBtn();
  }

  function updateRepeatBtn() {
    if (!btnRepeat) return;
    btnRepeat.classList.toggle('repeat-active', !!repeatMode);
    btnRepeat.classList.toggle('repeat-one', repeatMode === 'one');
    btnRepeat.innerHTML = repeatMode === 'one' ? IC_REPEAT_ONE : IC_REPEAT;
    btnRepeat.title = repeatMode === 'one'
      ? 'Einzeltitel wiederholen — Klick für Aus'
      : repeatMode === 'all'
        ? 'Alle wiederholen — Klick für Einzeltitel'
        : 'Wiederholen aktivieren';
  }

  /* ── Rating stars (audio-only write, display-only for video) ── */
  var playerRatingEl = document.getElementById('player-rating');

  function renderPlayerRating(stars) {
    if (!playerRatingEl) return;
    var rounded = Math.round(stars || 0);
    playerRatingEl.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var btn = document.createElement('button');
      btn.className = 'player-rating-star' + (i <= rounded ? ' active' : '');
      btn.innerHTML = i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      btn.dataset.star = i;
      btn.title = i + (i === 1 ? ' Stern' : ' Sterne');
      if (!RATING_WRITE_ENABLED) btn.style.pointerEvents = 'none';
      playerRatingEl.appendChild(btn);
    }
    playerRatingEl.removeAttribute('hidden');
  }

  function setRating(stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[currentIndex];
    if (!t) return;
    var prevRating = t.rating || 0;
    fetch(RATING_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, rating: stars })
    })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.ok) return;
        t.rating = d.rating;
        renderPlayerRating(d.rating);
        /* rebuild weighted shuffle queue so new rating is reflected immediately */
        if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        /* show toast with undo option if entry_id was returned */
        if (d.entry_id) {
          showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
        } else {
          showToast(stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben');
        }
      })
      .catch(function() {});
  }

  function showRatingToastWithUndo(stars, prevStars, entryId, t) {
    var toast = document.getElementById('toast');
    if (!toast) { showToast(stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben'); return; }
    var label = stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben';
    /* build toast via DOM — avoids quote-escaping in onclick attribute */
    toast.innerHTML = '';
    var span = document.createElement('span');
    span.textContent = label;
    toast.appendChild(span);
    var undoBtn = document.createElement('button');
    undoBtn.textContent = 'Rueckgaengig';
    undoBtn.style.cssText = 'margin-left:0.5rem;background:none;border:1px solid #888;'
      + 'color:inherit;border-radius:4px;padding:1px 8px;cursor:pointer;font-size:0.8rem;';
    undoBtn.addEventListener('click', function() { undoRating(undoBtn, entryId, prevStars); });
    toast.appendChild(undoBtn);
    toast.classList.add('show');
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 5000);
  }

  function undoRating(btn, entryId, prevStars) {
    btn.disabled = true; btn.textContent = '…';
    fetch(AUDIT_UNDO_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId })
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var t2 = filteredItems[currentIndex];
        if (d.ok && t2) {
          t2.rating = prevStars;
          renderPlayerRating(prevStars);
          if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        }
        var toast = document.getElementById('toast');
        if (toast) {
          toast.innerHTML = d.ok ? 'Rückgängig gemacht ✓' : ('Fehler: ' + (d.detail || '?'));
          clearTimeout(toast._hideTimer);
          toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 2500);
        }
      })
      .catch(function() { showToast('Netzwerkfehler beim Rückgängig'); });
  }

  if (playerRatingEl) {
    /* hover preview */
    playerRatingEl.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var n = parseInt(btn.dataset.star, 10);
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    playerRatingEl.addEventListener('mouseleave', function() {
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    /* click to rate */
    playerRatingEl.addEventListener('click', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      setRating(parseInt(btn.dataset.star, 10));
    });
  }


  if (SHUFFLE_ENABLED) {
    var _savedShuffle = localStorage.getItem('ht-shuffle-mode');
    if (_savedShuffle === 'normal' || _savedShuffle === 'weighted') {
      shuffleMode = _savedShuffle;
    }
    updateShuffleBtn();
  }

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function() { playTrack(prevIndex()); });
  btnNext.addEventListener('click', playNextItem);

  /* ── Shuffle button: click = cycle modes, long-press (600 ms) = weighted ── */
  if (SHUFFLE_ENABLED && btnShuffle) {
    var _shuffleLongPressed = false;
    var _shuffleLongPressTimer = null;
    function _startShuffleLongPress() {
      _shuffleLongPressed = false;
      _shuffleLongPressTimer = setTimeout(function() {
        _shuffleLongPressed = true;
        activateWeightedShuffle();
      }, 600);
    }
    function _cancelShuffleLongPress() { clearTimeout(_shuffleLongPressTimer); }
    btnShuffle.addEventListener('mousedown', _startShuffleLongPress);
    btnShuffle.addEventListener('mouseup', _cancelShuffleLongPress);
    btnShuffle.addEventListener('mouseleave', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchstart', function(e) {
      e.preventDefault();
      _startShuffleLongPress();
    }, { passive: false });
    btnShuffle.addEventListener('touchend', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchcancel', _cancelShuffleLongPress);
    btnShuffle.addEventListener('click', function() {
      if (!_shuffleLongPressed) cycleShuffle();
      _shuffleLongPressed = false;
    });
  }

  /* ── Repeat button: click = cycle modes (off → all → one → off) ── */
  if (REPEAT_ENABLED) {
    var _savedRepeat = localStorage.getItem('ht-repeat-mode');
    if (_savedRepeat === 'all' || _savedRepeat === 'one') {
      repeatMode = _savedRepeat;
    }
    updateRepeatBtn();
  }
  if (REPEAT_ENABLED && btnRepeat) {
    btnRepeat.addEventListener('click', cycleRepeat);
  }

  /* ── Crossfade (audio only) ── */
  var _xfadeAudio = null;   /* second <audio> element for crossfade target */
  var _xfading = false;     /* true while a crossfade is in progress */
  var _xfadeTimer = null;   /* setInterval for volume ramp */
  var _xfadeNextItem = null;/* the item being crossfaded into */
  var _xfadeNextIndex = -1; /* filteredItems index of the crossfade target */

  function _xfadeCleanup() {
    if (_xfadeTimer) { clearInterval(_xfadeTimer); _xfadeTimer = null; }
    if (_xfadeAudio) { _xfadeAudio.pause(); _xfadeAudio.removeAttribute('src'); }
    _xfading = false;
    _xfadeNextItem = null;
    _xfadeNextIndex = -1;
  }

  function _resolveNextForCrossfade() {
    /* Determine the next item WITHOUT consuming queue or advancing state */
    if (_userQueue.length > 0) {
      return { item: _userQueue[0], index: -1, fromQueue: true };
    }
    if (!filteredItems.length) return null;
    var ni = nextIndex();
    if (ni < 0 || ni >= filteredItems.length) return null;
    return { item: filteredItems[ni], index: ni, fromQueue: false };
  }

  function _startCrossfade() {
    if (_xfading) return;
    var next = _resolveNextForCrossfade();
    if (!next || !next.item || !next.item.stream_url) return;
    _xfading = true;
    _xfadeNextItem = next.item;
    _xfadeNextIndex = next.index;

    /* Create or reuse the xfade audio element */
    if (!_xfadeAudio) {
      _xfadeAudio = document.createElement('audio');
      _xfadeAudio.style.display = 'none';
      _xfadeAudio.preload = 'auto';
      document.body.appendChild(_xfadeAudio);
    }
    _xfadeAudio.volume = 0;
    _xfadeAudio.src = next.item.stream_url;
    _xfadeAudio.load();
    _xfadeAudio.play().catch(function() { _xfadeCleanup(); });

    /* Ramp volumes: fade out current, fade in next */
    var steps = 20; /* 50ms intervals over CROSSFADE_DURATION */
    var interval = (CROSSFADE_DURATION * 1000) / steps;
    var step = 0;
    _xfadeTimer = setInterval(function() {
      step++;
      var progress = Math.min(step / steps, 1);
      /* Ease curve: sine ease-in-out */
      var ease = 0.5 - 0.5 * Math.cos(Math.PI * progress);
      player.volume = Math.max(0, 1 - ease);
      _xfadeAudio.volume = Math.min(1, ease);
      if (step >= steps) {
        clearInterval(_xfadeTimer);
        _xfadeTimer = null;
        _finishCrossfade();
      }
    }, interval);
  }

  function _finishCrossfade() {
    if (!_xfadeNextItem) { _xfadeCleanup(); return; }
    /* Save progress for the outgoing track */
    saveProgressNow();
    clearProgressFor(_progressRelPath);

    /* Advance the actual playback state */
    var nextItem = _xfadeNextItem;
    var fromQueue = _xfadeNextIndex === -1 && _userQueue.length > 0;

    /* Stop the xfade audio — main player takes over */
    var xfSrc = _xfadeAudio.src;
    var xfTime = _xfadeAudio.currentTime;
    _xfadeAudio.pause();

    _xfading = false;
    _xfadeNextItem = null;

    if (fromQueue) {
      /* Consume from queue */
      playFromQueue(0);
    } else {
      playTrack(_xfadeNextIndex >= 0 ? _xfadeNextIndex : nextIndex());
    }
    _xfadeNextIndex = -1;

    /* Restore volume to 1 for the main player */
    player.volume = 1;
  }

  player.addEventListener('ended', function() {
    clearProgressFor(_progressRelPath);
    if (_xfading) {
      /* Crossfade already handled transition — just finish it */
      _finishCrossfade();
      return;
    }
    playNextItem();
  });
  player.addEventListener('pause', function() {
    /* Don't change state when the browser auto-paused for background,
       or when bg audio has taken over playback */
    if (document.hidden) return;
    if (bgAudioIsActive()) return;
    /* User-initiated pause (custom button OR native controls) */
    wasPlaying = false;
    if (_xfading) { _xfadeCleanup(); player.volume = 1; }
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    stopBgSync();
    if (!player.ended) btnPlay.innerHTML = IC_PLAY;
    saveProgressNow();
  });
  player.addEventListener('play',  function() { btnPlay.innerHTML = IC_PAUSE; });
  player.addEventListener('timeupdate', function() {
    if (!isFinite(player.duration)) return;
    progressBar.max = player.duration; progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
    drawWaveform(player.currentTime / player.duration);
    saveProgressDebounced();
    /* Crossfade trigger: start fading when remaining time <= CROSSFADE_DURATION
       Skip crossfade for repeat-one (track restarts itself) */
    if (CROSSFADE_DURATION > 0 && !_xfading && !isVideoPlayer && repeatMode !== 'one') {
      var remaining = player.duration - player.currentTime;
      if (remaining > 0 && remaining <= CROSSFADE_DURATION && player.duration > CROSSFADE_DURATION + 5) {
        _startCrossfade();
      }
    }
  });
  player.addEventListener('loadedmetadata', function() {
    timeDur.textContent = fmtTime(player.duration); progressBar.max = player.duration;
  });
  progressBar.addEventListener('input', function() { player.currentTime = progressBar.value; });

  /* bg audio events — keep UI in sync when playing in background */
  if (isVideoPlayer) {
    setInterval(function() {
      if (bgAudio && !bgAudio.muted && document.hidden) {
        if (isFinite(bgAudio.duration)) {
          progressBar.max = bgAudio.duration;
          progressBar.value = bgAudio.currentTime;
          timeCur.textContent = fmtTime(bgAudio.currentTime);
          drawWaveform(bgAudio.currentTime / bgAudio.duration);
        }
      }
    }, 1000);
  }

  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);

  /* Logo-Icon click → always navigate back to root */
  logoHomeBtn.addEventListener('click', function() {
    currentPath = '';
    showFolderView();
  });

  /* Show video player element when something starts playing */
  if (isVideoPlayer) {
    player.addEventListener('loadeddata', function() {
      player.style.display = 'block';
    });
  }

  /* ── Favoriten — speichern & teilen ── */
  var _savedFavorites = {};

  function loadFavorites() {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    fetch(base + '/shortcuts')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        _savedFavorites = {};
        if (data && Array.isArray(data.items)) {
          data.items.forEach(function(s) { _savedFavorites[s.id] = true; });
        }
        updateFavoriteButtons();
        /* If favorites filter is active, re-apply so newly loaded state is reflected */
        if (filterFav && inPlaylist) applyFilter();
      })
      .catch(function() {});
  }

  function updateFavoriteButtons() {
    document.querySelectorAll('.track-pin-btn').forEach(function(btn) {
      var rp = btn.dataset.relativePath;
      if (_savedFavorites[rp]) {
        btn.classList.add('pinned');
        btn.title = 'Favorit entfernen';
      } else {
        btn.classList.remove('pinned');
        btn.title = 'Favorit';
      }
    });
  }

  /* ── metadata edit modal ── */
  var _editModalRating = 0; /* selected rating inside the edit modal */

  function renderEditModalRating(stars) {
    var container = document.getElementById('edit-modal-rating');
    if (!container) return;
    var rounded = Math.round(stars || 0);
    _editModalRating = rounded;
    container.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'edit-modal-rating-star' + (i <= rounded ? ' active' : '');
      btn.innerHTML = i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      btn.dataset.star = String(i);
      btn.title = i + (i === 1 ? ' Stern' : ' Sterne');
      container.appendChild(btn);
    }
  }

  (function _initEditModalRatingEvents() {
    var container = document.getElementById('edit-modal-rating');
    if (!container) return;
    container.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.edit-modal-rating-star');
      if (!btn) return;
      var n = parseInt(btn.dataset.star, 10);
      container.querySelectorAll('.edit-modal-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    container.addEventListener('mouseleave', function() {
      container.querySelectorAll('.edit-modal-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    container.addEventListener('click', function(e) {
      var btn = e.target.closest('.edit-modal-rating-star');
      if (!btn) return;
      var n = parseInt(btn.dataset.star, 10);
      /* Toggle off if clicking the same star */
      renderEditModalRating(n === _editModalRating ? 0 : n);
    });
  })();

  function openEditModal(idx) {
    if (!METADATA_EDIT_ENABLED) return;
    var t = filteredItems[idx];
    if (!t) return;
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (!backdrop) return;
    document.getElementById('edit-modal-title-input').value = t.title || '';
    document.getElementById('edit-modal-artist-input').value = t.artist || '';
    document.getElementById('edit-modal-album-input').value = '';
    document.getElementById('edit-modal-path').value = t.relative_path || '';
    document.getElementById('edit-modal-idx').value = String(idx);
    /* Rating stars — only if rating write is enabled */
    var ratingField = document.getElementById('edit-modal-rating-field');
    if (RATING_WRITE_ENABLED) {
      if (ratingField) ratingField.style.display = '';
      renderEditModalRating(t.rating || 0);
    } else {
      if (ratingField) ratingField.style.display = 'none';
    }
    backdrop.removeAttribute('hidden');
    document.body.classList.add('modal-open');
    document.getElementById('edit-modal-title-input').focus();
  }

  function closeEditModal() {
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (backdrop) backdrop.setAttribute('hidden', '');
    document.body.classList.remove('modal-open');
  }

  function submitEditModal() {
    var path = document.getElementById('edit-modal-path').value;
    var idx = parseInt(document.getElementById('edit-modal-idx').value, 10);
    var title = document.getElementById('edit-modal-title-input').value.trim();
    var artist = document.getElementById('edit-modal-artist-input').value.trim();
    var album = document.getElementById('edit-modal-album-input').value.trim();
    var saveBtn = document.getElementById('edit-modal-save-btn');
    if (!path) return;
    if (saveBtn) saveBtn.disabled = true;

    /* Determine if rating changed */
    var t = filteredItems[idx];
    var oldRating = t ? Math.round(t.rating || 0) : 0;
    var newRating = _editModalRating;
    var ratingChanged = RATING_WRITE_ENABLED && (newRating !== oldRating);

    /* Save metadata (title/artist/album) */
    var metaPromise = fetch(METADATA_EDIT_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path, title: title, artist: artist, album: album || null })
    }).then(function(r) { return r.json(); });

    /* Save rating if changed */
    var ratingPromise = ratingChanged
      ? fetch(RATING_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: path, rating: newRating })
        }).then(function(r) { return r.ok ? r.json() : null; })
      : Promise.resolve(null);

    Promise.all([metaPromise, ratingPromise])
      .then(function(results) {
        var d = results[0];
        var rd = results[1];
        if (saveBtn) saveBtn.disabled = false;
        if (d.ok) {
          /* Update in-memory items so the list reflects changes immediately */
          var updates = { title: title, artist: artist };
          if (rd && rd.ok) updates.rating = rd.rating;
          if (filteredItems[idx]) {
            filteredItems[idx] = Object.assign({}, filteredItems[idx], updates);
          }
          for (var i = 0; i < allItems.length; i++) {
            if (allItems[i].relative_path === path) {
              allItems[i] = Object.assign({}, allItems[i], updates);
              break;
            }
          }
          closeEditModal();
          renderTracks(filteredItems);
          /* Update player display if this is the currently playing track */
          if (idx === currentIndex) {
            if (playerTitle) playerTitle.textContent = title;
            if (playerArtist) playerArtist.textContent = artist;
            if (rd && rd.ok) renderPlayerRating(rd.rating);
          }
          /* Rebuild weighted shuffle queue if rating changed */
          if (rd && rd.ok && shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
          showToast('Gespeichert \u2713');
        } else {
          showToast('Fehler beim Speichern');
        }
      })
      .catch(function() {
        if (saveBtn) saveBtn.disabled = false;
        showToast('Netzwerkfehler beim Speichern');
      });
  }

  function toggleFavorite(item, btn) {
    if (!item || !item.relative_path) return;
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var isPinned = _savedFavorites[item.relative_path];

    if (isPinned) {
      /* Remove favorite */
      fetch(base + '/shortcuts?id=' + encodeURIComponent(item.relative_path), { method: 'DELETE' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function() {
          delete _savedFavorites[item.relative_path];
          if (btn) { btn.classList.remove('pinned'); btn.title = 'Favorit'; }
          showToast('Favorit entfernt');
        })
        .catch(function() {});
    } else {
      /* Add favorite */
      fetch(base + '/shortcuts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.relative_path,
          title: item.title || item.relative_path,
          icon: '/thumb?path=' + encodeURIComponent(item.relative_path)
        })
      })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function() {
        _savedFavorites[item.relative_path] = true;
        if (btn) { btn.classList.add('pinned'); btn.title = 'Favorit entfernen'; }
        showToast('Als Favorit gespeichert');
        /* On mobile: additionally offer share sheet for home screen shortcut */
        if (navigator.share && ('ontouchstart' in window || navigator.maxTouchPoints > 0)) {
          var deepUrl = window.location.origin + '/?id=' + encodeURIComponent(item.relative_path);
          setTimeout(function() {
            navigator.share({
              title: item.title || 'Favorit',
              text: item.title || '',
              url: deepUrl
            }).catch(function() {});
          }, 600);
        }
      })
      .catch(function() { showToast('Favorit konnte nicht gespeichert werden'); });
    }
  }

  function showToast(msg) {
    var t = document.getElementById('ht-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'ht-toast';
      t.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;font-size:14px;max-width:90%;text-align:center;transition:opacity .3s';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    t.style.display = 'block';
    clearTimeout(t._timer);
    t._timer = setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.style.display = 'none'; }, 300); }, 3500);
  }

  viewToggle.addEventListener('click', function() {
    if (_anyToolActive()) return; /* locked while tools are active */
    if (viewMode === 'list') viewMode = 'grid';
    else viewMode = 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    if (inPlaylist) {
      applyViewMode();
      renderTracks(filteredItems);
    } else {
      showFolderView();
    }
  });
  searchInput.addEventListener('input', applyFilter);
  sortField.addEventListener('change', applyFilter);
  if (filterRatingBtn) {
    filterRatingBtn.addEventListener('click', function() {
      /* cycle 0 → 1 → 2 → 3 → 4 → 5 → 0 */
      filterRating = (filterRating + 1) % 6;
      localStorage.setItem('ht-filter-rating', String(filterRating));
      updateFilterChips();
      applyFilter();
    });
  }
  if (filterFavBtn) {
    filterFavBtn.addEventListener('click', function() {
      filterFav = !filterFav;
      localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0');
      updateFilterChips();
      applyFilter();
    });
  }
  if (filterGenreBtn) {
    filterGenreBtn.addEventListener('click', function() {
      /* Collect genres from current playlist, cycle through them */
      var genres = {};
      (playlistItems || []).forEach(function(t) {
        if (t.genre) genres[t.genre] = true;
      });
      var genreList = Object.keys(genres).sort();
      if (!genreList.length) return;
      var idx = filterGenre ? genreList.indexOf(filterGenre) : -1;
      filterGenre = (idx + 1 < genreList.length) ? genreList[idx + 1] : '';
      localStorage.setItem('ht-filter-genre', filterGenre);
      updateFilterChips();
      applyFilter();
    });
  }
  if (filterHiddenBtn) {
    filterHiddenBtn.addEventListener('click', function() {
      showHidden = !showHidden;
      localStorage.setItem('ht-show-hidden', showHidden ? '1' : '0');
      updateFilterChips();
      applyFilter();
    });
  }
  updateFilterChips();

  /* ── init ── */
  if (METADATA_EDIT_ENABLED) {
    var _editCancelBtn = document.getElementById('edit-modal-cancel-btn');
    var _editSaveBtn   = document.getElementById('edit-modal-save-btn');
    var _editBackdrop  = document.getElementById('edit-modal-backdrop');
    if (_editCancelBtn) _editCancelBtn.addEventListener('click', closeEditModal);
    if (_editSaveBtn)   _editSaveBtn.addEventListener('click', submitEditModal);
    /* Close on backdrop click (outside the panel) */
    if (_editBackdrop) {
      _editBackdrop.addEventListener('click', function(e) {
        if (e.target === _editBackdrop) closeEditModal();
      });
    }
    /* Submit on Enter inside inputs, Escape to close */
    document.addEventListener('keydown', function(e) {
      var backdrop = document.getElementById('edit-modal-backdrop');
      if (!backdrop || backdrop.hasAttribute('hidden')) return;
      if (e.key === 'Escape') { e.preventDefault(); closeEditModal(); }
      if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); submitEditModal(); }
    });
  }

  if (!OFFLINE_ENABLED) {
    if (downloadedPill) {
      downloadedPill.textContent = 'Safe Mode';
      downloadedPill.classList.add('is-offline');
    }
  } else if (typeof indexedDB !== 'undefined') {
    initDownloadDB().catch(function(err) {
      console.warn('IndexedDB not available:', err);
    }).then(function() {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    });
  } else {
    refreshOfflineLibrary();
  }
  applyViewMode();

  /* ── Deep Linking: ?id=relative/path auto-navigates & plays ── */
  var _deepLinkId = (new URLSearchParams(window.location.search)).get('id');

  function handleDeepLink() {
    if (!_deepLinkId || !allItems.length) return;
    var target = allItems.find(function(it) { return it.relative_path === _deepLinkId; });
    if (!target) { _deepLinkId = null; return; }
    /* Navigate to the item's parent folder */
    var slash = _deepLinkId.lastIndexOf('/');
    currentPath = slash > 0 ? _deepLinkId.substring(0, slash) : '';
    /* Gather siblings in that folder */
    var c = contentsAt(currentPath);
    var siblings = c.files.length ? c.files : itemsUnder(currentPath);
    var idx = siblings.findIndex(function(it) { return it.relative_path === _deepLinkId; });
    if (idx < 0) { idx = 0; }
    showPlaylist(siblings, true, idx);
    /* Clean the URL so reload doesn't re-trigger deep link */
    var cleanUrl = window.location.pathname;
    history.replaceState(null, '', cleanUrl);
    _deepLinkId = null;
  }

  /* ── User Playlists ── */
  var _userPlaylists = [];
  var _playlistAddPath = '';
  var _currentPlaylistId = '';

  /* ── Favorites custom order (server-side + localStorage fallback) ── */
  function _loadFavoritesOrder() {
    try {
      var raw = localStorage.getItem('ht-favorites-order');
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFavoritesOrder(paths) {
    try { localStorage.setItem('ht-favorites-order', JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: '__favorites__', items: paths })
    }).catch(function() {});
  }
  function _loadFavoritesOrderAsync(cb) {
    fetch(FOLDER_ORDER_API_PATH + '?path=__favorites__')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem('ht-favorites-order', JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFavoritesOrder());
        }
      }).catch(function() { cb(_loadFavoritesOrder()); });
  }
  function _sortFavoritesByOrder(favItems) {
    var order = _loadFavoritesOrder();
    if (!order.length) return favItems;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return favItems.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  /* ── Folder custom order (server-side + localStorage fallback) ── */
  function _folderOrderKey(folderPath) {
    return 'ht-folder-order-' + (folderPath || '__root__');
  }
  function _loadFolderOrder(folderPath) {
    try {
      var raw = localStorage.getItem(_folderOrderKey(folderPath));
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFolderOrder(folderPath, paths) {
    try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath || '__root__', items: paths })
    }).catch(function() {});
  }
  function _loadFolderOrderAsync(folderPath, cb) {
    var key = folderPath || '__root__';
    fetch(FOLDER_ORDER_API_PATH + '?path=' + encodeURIComponent(key))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFolderOrder(folderPath));
        }
      }).catch(function() { cb(_loadFolderOrder(folderPath)); });
  }
  function _sortByFolderOrder(folderPath, items) {
    var order = _loadFolderOrder(folderPath);
    if (!order.length) return items;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return items.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  var _playlistRevision = 0;
  var _playlistSyncTimer = null;
  var _PLAYLIST_SYNC_INTERVAL = """
        + str(playlist_sync_interval_ms)
        + """; /* ms */

  function loadUserPlaylists() {
    if (!PLAYLISTS_ENABLED) return Promise.resolve([]);
    return fetch(PLAYLISTS_API_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        updatePlaylistPill();
        return _userPlaylists;
      })
      .catch(function() { return []; });
  }

  function _startPlaylistSync() {
    if (!PLAYLISTS_ENABLED) return;
    _stopPlaylistSync();
    _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    /* Pause when tab hidden, resume when visible */
    document.addEventListener('visibilitychange', _onPlaylistVisibility);
  }
  function _stopPlaylistSync() {
    if (_playlistSyncTimer) { clearInterval(_playlistSyncTimer); _playlistSyncTimer = null; }
  }
  function _onPlaylistVisibility() {
    if (document.hidden) {
      _stopPlaylistSync();
    } else {
      /* Resume polling and do an immediate check */
      _stopPlaylistSync();
      _pollPlaylistVersion();
      _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    }
  }
  function _pollPlaylistVersion() {
    fetch(PLAYLISTS_VERSION_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        if (typeof d.revision === 'number' && d.revision > _playlistRevision) {
          loadUserPlaylists().then(function() {
            /* If we're currently looking at the folder view, re-render to show updated playlist cards */
            if (!inPlaylist && currentPath === '') showFolderView();
          });
        }
      }).catch(function() { /* offline — ignore */ });
  }

  function updatePlaylistPill() { /* pill removed — no-op */ }

  /* ── optimistic UI helpers ── */
  function _snapshotPlaylists() {
    return JSON.parse(JSON.stringify(_userPlaylists));
  }
  function _restorePlaylists(snap) {
    _userPlaylists = snap;
    updatePlaylistPill();
  }

  /* ── playlist library panel (removed — playlists as pseudo-folders) ── */
  function openPlaylistLibrary() { /* removed */ }
  function closePlaylistLibrary() { /* removed */ }
  function renderPlaylistLibrary() { /* removed */ }

  function _resolvePlaylistItems(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl || !pl.items || pl.items.length === 0) return null;
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    if (resolved.length === 0) return null;
    return { pl: pl, resolved: resolved };
  }

  function showUserPlaylistView(plId) {
    /* Show playlist content without auto-playing (browse mode) */
    if (plId === '__favorites__') {
      var favItems = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
      if (favItems.length === 0) { showToast('Keine Favoriten vorhanden'); return; }
      _currentPlaylistId = '__favorites__';
      playlistItems = _sortFavoritesByOrder(favItems);
      inPlaylist = true;
      currentPath = '';
      var hdr = document.getElementById('header-title');
      if (hdr) hdr.textContent = 'Favoriten';
      backBtn.style.display = 'inline-block';
      folderGrid.classList.add('view-hidden');
      trackView.classList.remove('view-hidden');
      filterBar.classList.remove('view-hidden');
      filterBar.classList.add('fb-scroll-hidden');
      playerBar.classList.remove('view-hidden');
      _hideGlobalSearch();
      _initFilterBarScrollReveal();
      searchInput.value = '';
      renderBreadcrumb();
      applyFilter();
      /* Pre-warm: fetch server-side favorites order and re-sort if different */
      _loadFavoritesOrderAsync(function(serverOrder) {
        if (!serverOrder.length) return;
        if (_currentPlaylistId !== '__favorites__') return;
        var localOrder = _loadFavoritesOrder();
        if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
        playlistItems = _sortFavoritesByOrder(favItems);
        applyFilter();
      });
      return;
    }
    var data = _resolvePlaylistItems(plId);
    if (!data) { showToast('Keine Titel in dieser Playlist gefunden'); return; }
    _currentPlaylistId = plId;
    playlistItems = data.resolved;
    inPlaylist = true;
    currentPath = '';
    var hdr = document.getElementById('header-title');
    if (hdr) hdr.textContent = data.pl.name;
    backBtn.style.display = 'inline-block';
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    filterBar.classList.add('fb-scroll-hidden');
    playerBar.classList.remove('view-hidden');
    _hideGlobalSearch();
    _initFilterBarScrollReveal();
    searchInput.value = '';
    renderBreadcrumb();
    applyFilter();
  }

  function playUserPlaylist(plId) {
    if (plId === '__favorites__') {
      var favItems = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
      if (favItems.length === 0) { showToast('Keine Favoriten vorhanden'); return; }
      _currentPlaylistId = '__favorites__';
      var sorted = _sortFavoritesByOrder(favItems);
      playlistItems = sorted;
      filteredItems = sorted;
      inPlaylist = true;
      currentPath = '';
      var hdr = document.getElementById('header-title');
      if (hdr) hdr.textContent = 'Favoriten';
      renderTracks(favItems, true);
      playTrack(0);
      return;
    }
    var data = _resolvePlaylistItems(plId);
    if (!data) { showToast('Keine Titel in dieser Playlist gefunden'); return; }
    _currentPlaylistId = plId;
    playlistItems = data.resolved;
    filteredItems = data.resolved;
    inPlaylist = true;
    currentPath = '';
    var hdr = document.getElementById('header-title');
    if (hdr) hdr.textContent = data.pl.name;
    renderTracks(data.resolved, true);
    playTrack(0);
  }

  function deleteUserPlaylist(plId) {
    /* TODO: Nach Entwicklungsphase → Nachfrage + Archivierung statt L\u00f6schung */
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    var name = pl ? pl.name : 'Playlist';
    if (!confirm('Playlist "' + name + '" wirklich l\u00f6schen?')) return;
    /* Optimistic: remove locally first */
    var snap = _snapshotPlaylists();
    _userPlaylists = _userPlaylists.filter(function(p) { return p.id !== plId; });
    if (!currentPath && !inPlaylist) showFolderView();
    fetch(PLAYLISTS_API_PATH + '?id=' + encodeURIComponent(plId), { method: 'DELETE' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        showToast('Playlist gel\u00f6scht');
        if (!currentPath && !inPlaylist) showFolderView();
      })
      .catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim L\u00f6schen \u2014 r\u00fcckg\u00e4ngig');
        if (!currentPath && !inPlaylist) showFolderView();
      });
  }

  /* ── add-to-playlist modal ── */
  function openPlaylistModal(relativePath) {
    _playlistAddPath = relativePath;
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (!backdrop) return;
    backdrop.hidden = false;
    document.body.classList.add('modal-open');
    renderPlaylistModalList();
  }

  function closePlaylistModal() {
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove('modal-open');
    _playlistAddPath = '';
  }

  function renderPlaylistModalList() {
    var listEl = document.getElementById('playlist-modal-list');
    if (!listEl) return;
    if (_userPlaylists.length === 0) {
      listEl.innerHTML = '<li style="padding:0.5rem;color:var(--sub);font-size:0.85rem">Noch keine Playlists. Erstelle eine neue!</li>';
      return;
    }
    listEl.innerHTML = _userPlaylists.map(function(pl) {
      var cnt = (pl.items || []).length;
      return '<li class="playlist-modal-item" data-id="' + escHtml(pl.id) + '">' +
        '<span class="playlist-modal-item-name">' + escHtml(pl.name) + '</span>' +
        '<span class="playlist-modal-item-count">' + cnt + ' Titel</span></li>';
    }).join('');
    listEl.querySelectorAll('.playlist-modal-item').forEach(function(el) {
      el.addEventListener('click', function() {
        addToPlaylist(el.dataset.id, _playlistAddPath);
      });
    });
  }

  function addToPlaylist(plId, relativePath) {
    /* Optimistic: add item locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (localPl && (localPl.items || []).indexOf(relativePath) < 0) {
      localPl.items = (localPl.items || []).slice();
      localPl.items.push(relativePath);
    }
    updatePlaylistPill();
    closePlaylistModal();
    showToast('Zur Playlist hinzugef\\u00fcgt');
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: plId, relative_path: relativePath })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === plId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
        }
        updatePlaylistPill();
      }).catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim Hinzuf\\u00fcgen \\u2014 r\\u00fcckg\\u00e4ngig');
      });
  }

  function createAndAddToPlaylist(name, relativePath) {
    fetch(PLAYLISTS_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          _userPlaylists.unshift(d.playlist);
          updatePlaylistPill();
          addToPlaylist(d.playlist.id, relativePath);
        }
      }).catch(function() { showToast('Fehler beim Erstellen'); });
  }

  function movePlaylistItem(relativePath, direction) {
    if (!_currentPlaylistId) return;
    /* Optimistic: swap locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var li = litems.indexOf(relativePath);
      if (li >= 0) {
        var ni = direction === 'up' ? li - 1 : li + 1;
        if (ni >= 0 && ni < litems.length) {
          var tmp = litems[li]; litems[li] = litems[ni]; litems[ni] = tmp;
          localPl.items = litems;
          _applyPlaylistUpdate(localPl);
        }
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, direction: direction })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function reorderPlaylistItem(relativePath, toIndex) {
    if (!_currentPlaylistId) return;

    /* Favorites: client-side reorder via localStorage */
    if (_currentPlaylistId === '__favorites__') {
      var paths = playlistItems.map(function(it) { return it.relative_path; });
      var oldIdx = paths.indexOf(relativePath);
      if (oldIdx < 0) return;
      paths.splice(oldIdx, 1);
      var clamped = Math.max(0, Math.min(toIndex, paths.length));
      paths.splice(clamped, 0, relativePath);
      _saveFavoritesOrder(paths);
      /* rebuild playlistItems in new order */
      var itemMap = {};
      playlistItems.forEach(function(it) { itemMap[it.relative_path] = it; });
      var reordered = paths.map(function(rp) { return itemMap[rp]; }).filter(Boolean);
      var playingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = reordered;
      filteredItems = reordered;
      if (playingPath) {
        var newIdx = reordered.findIndex(function(it) { return it.relative_path === playingPath; });
        if (newIdx >= 0) currentIndex = newIdx;
      }
      renderTracks(reordered, true);
      return;
    }

    /* Folder: client-side reorder via localStorage */
    if (_currentPlaylistId === '__folder__') {
      var fpaths = playlistItems.map(function(it) { return it.relative_path; });
      var fOldIdx = fpaths.indexOf(relativePath);
      if (fOldIdx < 0) return;
      fpaths.splice(fOldIdx, 1);
      var fClamped = Math.max(0, Math.min(toIndex, fpaths.length));
      fpaths.splice(fClamped, 0, relativePath);
      _saveFolderOrder(currentPath, fpaths);
      var fItemMap = {};
      playlistItems.forEach(function(it) { fItemMap[it.relative_path] = it; });
      var fReordered = fpaths.map(function(rp) { return fItemMap[rp]; }).filter(Boolean);
      var fPlayingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = fReordered;
      filteredItems = fReordered;
      if (fPlayingPath) {
        var fNewIdx = fReordered.findIndex(function(it) { return it.relative_path === fPlayingPath; });
        if (fNewIdx >= 0) currentIndex = fNewIdx;
      }
      renderTracks(fReordered, true);
      return;
    }

    /* Server-backed playlist: optimistic local reorder first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var lOld = litems.indexOf(relativePath);
      if (lOld >= 0) {
        litems.splice(lOld, 1);
        var lClamped = Math.max(0, Math.min(toIndex, litems.length));
        litems.splice(lClamped, 0, relativePath);
        localPl.items = litems;
        _applyPlaylistUpdate(localPl);
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, to_index: toIndex })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function _applyPlaylistUpdate(pl) {
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    var playingPath = currentIndex >= 0 && filteredItems[currentIndex] ? filteredItems[currentIndex].relative_path : null;
    playlistItems = resolved;
    filteredItems = resolved;
    if (playingPath) {
      var newIdx = resolved.findIndex(function(it) { return it.relative_path === playingPath; });
      if (newIdx >= 0) currentIndex = newIdx;
    }
    renderTracks(resolved, true);
    updatePlaylistPill();
  }

  /* ── Drag-and-drop reorder for playlist view ── */
  var _dndCleanup = null;

  function destroyPlaylistDragDrop() {
    if (_dndCleanup) { _dndCleanup(); _dndCleanup = null; }
  }

  function initPlaylistDragDrop() {
    destroyPlaylistDragDrop();

    var trackList = document.getElementById('track-list');
    if (!trackList) return;
    var items = trackList.querySelectorAll('.track-item:not(.missing-episode)');
    if (items.length < 2) return;

    var _dragItem = null;
    var _dragPath = '';
    var _dragFromIdx = -1;
    var _ghost = null;
    var _dropTarget = null;
    var _dropAbove = true;
    var _longPressTimer = null;
    var _touchStartY = 0;
    var _touchStartX = 0;
    var _dragActive = false;
    var _pendingDrag = null;
    var LONG_PRESS_MS = 500;
    var MOVE_THRESHOLD = 10;

    function getTrackItem(el) {
      while (el && el !== trackList) {
        if (el.classList && el.classList.contains('track-item')) return el;
        el = el.parentElement;
      }
      return null;
    }

    function createGhost(item, x, y) {
      var g = document.createElement('div');
      g.className = 'playlist-drag-ghost';
      var img = item.querySelector('.track-thumb');
      var titleEl = item.querySelector('.track-title-text') || item.querySelector('.track-title');
      if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
      g.innerHTML += '<span>' + (titleEl ? titleEl.textContent : '') + '</span>';
      g.style.left = (x - 20) + 'px';
      g.style.top = (y - 20) + 'px';
      document.body.appendChild(g);
      return g;
    }

    function moveGhost(x, y) {
      if (!_ghost) return;
      _ghost.style.left = (x - 20) + 'px';
      _ghost.style.top = (y - 20) + 'px';
    }

    function clearDragClasses() {
      trackList.querySelectorAll('.drag-over-above,.drag-over-below,.dragging').forEach(function(el) {
        el.classList.remove('drag-over-above', 'drag-over-below', 'dragging');
      });
    }

    function clearDropIndicator() {
      if (_dropTarget) {
        _dropTarget.classList.remove('drag-over-above', 'drag-over-below');
        _dropTarget = null;
      }
    }

    function updateDropTarget(x, y) {
      if (_ghost) _ghost.style.display = 'none';
      var el = document.elementFromPoint(x, y);
      if (_ghost) _ghost.style.display = '';
      var target = el ? getTrackItem(el) : null;

      if (!target) {
        if (_dragItem) {
          var dragRect = _dragItem.getBoundingClientRect();
          if (dragRect.height > 0 &&
              x >= dragRect.left && x <= dragRect.right &&
              y >= dragRect.top && y <= dragRect.bottom) {
            clearDropIndicator();
            return;
          }
        }
        var tlRect = trackList.getBoundingClientRect();
        if (x >= tlRect.left && x <= tlRect.right &&
            y >= tlRect.top && y <= tlRect.bottom) {
          var visibleItems = trackList.querySelectorAll(
            '.track-item:not(.missing-episode):not(.dragging)');
          if (visibleItems.length > 0) {
            var lastItem = visibleItems[visibleItems.length - 1];
            if (_dropTarget !== lastItem) clearDropIndicator();
            _dropTarget = lastItem;
            _dropAbove = false;
            lastItem.classList.remove('drag-over-above');
            lastItem.classList.add('drag-over-below');
            return;
          }
        }
        clearDropIndicator();
        return;
      }

      if (target === _dragItem) { clearDropIndicator(); return; }

      var rect = target.getBoundingClientRect();
      var mid = rect.top + rect.height / 2;
      var above = y < mid;

      if (!above) {
        var nextSib = target.nextElementSibling;
        while (nextSib && (!nextSib.classList.contains('track-item') ||
               nextSib.classList.contains('missing-episode') ||
               nextSib === _dragItem)) {
          nextSib = nextSib.nextElementSibling;
        }
        if (nextSib && nextSib.classList.contains('track-item')) {
          target = nextSib;
          above = true;
        }
      }

      _dropAbove = above;

      var candidateIdx = Number(target.dataset.index);
      var candidateTo = above ? candidateIdx : candidateIdx + 1;
      if (_dragFromIdx < candidateTo) candidateTo--;
      if (candidateTo === _dragFromIdx) { clearDropIndicator(); return; }

      if (_dropTarget !== target) clearDropIndicator();
      _dropTarget = target;
      target.classList.toggle('drag-over-above', above);
      target.classList.toggle('drag-over-below', !above);
    }

    function startDrag(item, x, y) {
      _dragActive = true;
      _dragItem = item;
      _dragPath = '';
      var idx = Number(item.dataset.index);
      if (filteredItems[idx]) {
        _dragPath = filteredItems[idx].relative_path;
        _dragFromIdx = idx;
      }
      item.classList.add('dragging');
      document.body.classList.add('playlist-dragging');
      _ghost = createGhost(item, x, y);
    }

    function endDrag() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      if (!_dragActive) return;
      _dragActive = false;
      if (_ghost) { _ghost.remove(); _ghost = null; }
      document.body.classList.remove('playlist-dragging');

      if (_dropTarget && _dragPath) {
        var targetIdx = Number(_dropTarget.dataset.index);
        var toIndex = _dropAbove ? targetIdx : targetIdx + 1;
        if (_dragFromIdx < toIndex) toIndex--;
        if (toIndex !== _dragFromIdx && toIndex >= 0) {
          reorderPlaylistItem(_dragPath, toIndex);
        }
      }
      clearDragClasses();
      _dragItem = null;
      _dropTarget = null;
    }

    /* --- Named handlers for proper cleanup --- */
    function onMouseDown(e) {
      if (e.button !== 0) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn,.track-queue-btn,.track-inline-rating-star,.track-title-text,.track-artist')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _pendingDrag = { item: item, x: e.clientX, y: e.clientY };
    }
    function onMouseMove(e) {
      if (_pendingDrag && !_dragActive) {
        var pdx = Math.abs(e.clientX - _pendingDrag.x);
        var pdy = Math.abs(e.clientY - _pendingDrag.y);
        if (pdx > MOVE_THRESHOLD || pdy > MOVE_THRESHOLD) {
          startDrag(_pendingDrag.item, e.clientX, e.clientY);
          _pendingDrag = null;
        } else {
          return;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      moveGhost(e.clientX, e.clientY);
      updateDropTarget(e.clientX, e.clientY);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (e.clientY < rect.top + scrollZone) trackList.scrollTop -= 8;
      if (e.clientY > rect.bottom - scrollZone) trackList.scrollTop += 8;
    }
    function onMouseUp() { _pendingDrag = null; endDrag(); }

    function onTouchStart(e) {
      if (e.touches.length !== 1) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn,.track-queue-btn,.track-inline-rating-star,.track-title-text,.track-artist')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
      _longPressTimer = setTimeout(function() {
        _longPressTimer = null;
        startDrag(item, _touchStartX, _touchStartY);
        if (navigator.vibrate) navigator.vibrate(30);
      }, LONG_PRESS_MS);
    }
    function onTouchMove(e) {
      if (_longPressTimer) {
        var dx = Math.abs(e.touches[0].clientX - _touchStartX);
        var dy = Math.abs(e.touches[0].clientY - _touchStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          clearTimeout(_longPressTimer);
          _longPressTimer = null;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      var tx = e.touches[0].clientX;
      var ty = e.touches[0].clientY;
      moveGhost(tx, ty);
      updateDropTarget(tx, ty);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (ty < rect.top + scrollZone) trackList.scrollTop -= 6;
      if (ty > rect.bottom - scrollZone) trackList.scrollTop += 6;
    }
    function onTouchEnd() { endDrag(); }
    function onTouchCancel() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      endDrag();
    }

    /* --- Attach listeners --- */
    trackList.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    trackList.addEventListener('touchstart', onTouchStart, { passive: true });
    trackList.addEventListener('touchmove', onTouchMove, { passive: false });
    trackList.addEventListener('touchend', onTouchEnd, { passive: true });
    trackList.addEventListener('touchcancel', onTouchCancel, { passive: true });

    /* --- Cleanup function --- */
    _dndCleanup = function() {
      trackList.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      trackList.removeEventListener('touchstart', onTouchStart);
      trackList.removeEventListener('touchmove', onTouchMove);
      trackList.removeEventListener('touchend', onTouchEnd);
      trackList.removeEventListener('touchcancel', onTouchCancel);
      if (_dragActive) {
        _dragActive = false;
        if (_ghost) { _ghost.remove(); _ghost = null; }
        document.body.classList.remove('playlist-dragging');
      }
      clearDragClasses();
    };
  }

  /* ── playlist event wiring ── */
  (function() {
    if (!PLAYLISTS_ENABLED) return;
    var modalClose = document.getElementById('playlist-modal-close-btn');
    if (modalClose) modalClose.addEventListener('click', closePlaylistModal);
    var modalBackdrop = document.getElementById('playlist-modal-backdrop');
    if (modalBackdrop) modalBackdrop.addEventListener('click', function(e) { if (e.target === modalBackdrop) closePlaylistModal(); });
    var newBtn = document.getElementById('playlist-modal-new-btn');
    var newInput = document.getElementById('playlist-modal-new-name');
    if (newBtn && newInput) {
      newBtn.addEventListener('click', function() {
        var n = newInput.value.trim();
        if (!n) return;
        createAndAddToPlaylist(n, _playlistAddPath);
        newInput.value = '';
      });
      newInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { newBtn.click(); }
      });
    }
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        var mb = document.getElementById('playlist-modal-backdrop');
        if (mb && !mb.hidden) closePlaylistModal();
      }
    });
  }());

  /* ── Touch swipe gestures (mobile navigation) ── */
  (function() {
    var _swipeStartX = 0;
    var _swipeStartY = 0;
    var _swipeStartT = 0;
    var _swipeActive = false;
    var SWIPE_MIN_DIST = 60;   /* px minimum horizontal distance */
    var SWIPE_MAX_VERT = 80;   /* px max vertical deviation */
    var SWIPE_MAX_TIME = 400;  /* ms max duration */

    function swipeTarget(el) {
      /* Don't intercept swipes on range inputs (progress bar, volume) */
      while (el) {
        if (el.tagName === 'INPUT' && el.type === 'range') return null;
        if (el.tagName === 'CANVAS') return null;
        if (el.classList && el.classList.contains('edit-modal-backdrop')) return null;
        if (el.classList && el.classList.contains('lyrics-panel')) return null;
        if (el.classList && el.classList.contains('queue-panel')) return null;
        if (el.classList && el.classList.contains('offline-library')) return null;
        if (el.classList && el.classList.contains('playlist-modal-backdrop')) return null;
        el = el.parentElement;
      }
      return true;
    }

    document.addEventListener('touchstart', function(e) {
      if (!swipeTarget(e.target)) return;
      if (e.touches.length !== 1) return;
      _swipeStartX = e.touches[0].clientX;
      _swipeStartY = e.touches[0].clientY;
      _swipeStartT = Date.now();
      _swipeActive = true;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
      if (!_swipeActive) return;
      _swipeActive = false;
      if (e.changedTouches.length !== 1) return;
      var dx = e.changedTouches[0].clientX - _swipeStartX;
      var dy = e.changedTouches[0].clientY - _swipeStartY;
      var dt = Date.now() - _swipeStartT;
      if (dt > SWIPE_MAX_TIME) return;
      if (Math.abs(dy) > SWIPE_MAX_VERT) return;
      if (Math.abs(dx) < SWIPE_MIN_DIST) return;

      /* Swipe right = go back (folder view or playlist view) */
      if (dx > 0) {
        if (inPlaylist) { goBack(); }
        else if (currentPath) { goBack(); }
      }
    }, { passive: true });
  }());

  loadInitialCatalog().then(function() {
    handleDeepLink();
    loadFavorites();
    loadUserPlaylists().then(function() {
      /* Re-render root folder view to show playlist pseudo-folder cards */
      if (!currentPath && !inPlaylist) showFolderView();
      _startPlaylistSync();
    });
  });
}());
"""
    )
