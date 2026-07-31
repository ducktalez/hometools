"""Player JavaScript generation for the streaming UI."""

from __future__ import annotations

from ._svg import (  # noqa: F401
    SVG_BACK,
    SVG_CAST,
    SVG_CHECK,
    SVG_CHEVRONS_DOWN,
    SVG_CHEVRONS_UP,
    SVG_CLOSE_X,
    SVG_DOTS,
    SVG_DOWNLOAD,
    SVG_DUPLICATE,
    SVG_EDIT,
    SVG_EXPAND,
    SVG_FILTER,
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
    SVG_SMART_PLAYLIST,
    SVG_STAR,
    SVG_STAR_EMPTY,
    SVG_TRASH,
)
from .player_js import (
    render_core_js,
    render_drag_drop_init_js,
    render_folder_browse_js,
    render_library_tools_js,
    render_playlists_js,
    render_queue_js,
    render_search_filter_js,
    render_smart_playlists_js,
    render_track_render_js,
)


def render_player_js(
    player_bar_style: str = "classic",
) -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).
    Clicking a folder navigates deeper into the hierarchy.  Leaf folders
    (no sub-folders) are displayed as playlists.  A breadcrumb trail and
    back button allow navigating up.  View preference is stored in
    localStorage.

    *player_bar_style* is the only remaining Python parameter — it's a
    genuinely structural choice (waveform vs. classic emits different JS
    for the progress bar/scrubber), unlike every other former parameter
    here. All request-varying config (``api_path``, ``enable_shuffle``,
    ``min_rating``, ``language_groups_json``, ...) is now read at runtime
    from the ``#ht-config`` JSON blob (``CFG.*``, rendered by
    ``_html.py::_render_player_config_json``) — see "Vite/TypeScript
    migration" Phase 3 in docs/IMPLEMENTATION_PLAN.md. Long-pressing the
    shuffle button activates weighted shuffle (items with higher ratings
    are more likely to play). Works with offline downloads too.
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
  var waveformDataR  = null;   /* peaks_r — null when mono or not yet loaded */
  var waveformAbort  = null;
"""
    else:
        waveform_js = """
  var progressTrack  = document.getElementById('progress-track');
  var waveformCanvas = document.getElementById('waveform-canvas');
  var waveformCtx    = waveformCanvas ? waveformCanvas.getContext('2d') : null;
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
  var waveformData   = null;   /* peaks_l (or legacy mono peaks) */
  var waveformDataR  = null;   /* peaks_r — null when mono or not yet loaded */
  var waveformAbort  = null;
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
  /* ── classic mode: cached stereo waveform overlay ── */
  var WAVEFORM_API_PATH = _apiBase() + '/waveform';

  function generateWaveform(url, relativePath) {
    if (!isAudioMode || !waveformCanvas) return;
    if (waveformAbort) { waveformAbort.abort(); }
    waveformAbort = new AbortController();
    waveformData  = null;
    waveformDataR = null;
    drawWaveform(0);
    if (!relativePath) return;
    fetch(WAVEFORM_API_PATH + '?path=' + encodeURIComponent(relativePath), { signal: waveformAbort.signal })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        if (!data) return;
        if (Array.isArray(data.peaks_l) && data.peaks_l.length) {
          /* Stereo format */
          waveformData  = data.peaks_l;
          waveformDataR = Array.isArray(data.peaks_r) && data.peaks_r.length ? data.peaks_r : null;
        } else if (Array.isArray(data.peaks) && data.peaks.length) {
          /* Legacy mono cache */
          waveformData  = data.peaks;
          waveformDataR = null;
        } else {
          return;
        }
        var prog = player.duration > 0 ? player.currentTime / player.duration : 0;
        drawWaveform(prog);
      })
      .catch(function(e) {
        if (!e || e.name !== 'AbortError') { waveformData = null; waveformDataR = null; }
      });
  }

  function drawWaveform(progress) {
    if (!waveformCanvas || !waveformCtx) return;
    var W = waveformCanvas.offsetWidth || 600;
    var H = waveformCanvas.offsetHeight || 28;
    waveformCanvas.width = W;
    waveformCanvas.height = H;
    waveformCtx.clearRect(0, 0, W, H);
    var accent = getComputedStyle(document.documentElement)
      .getPropertyValue('--accent').trim() || '#1db954';
    var prog    = progress || 0;
    var cy      = H / 2;
    var playedW = W * prog;

    var hasStereo = waveformData && waveformDataR && isAudioMode;
    var hasMono   = waveformData && !waveformDataR && isAudioMode;

    /* Layer 1: base progress indicator */
    if (hasStereo) {
      /* Thin centre line — coloured bars carry the progress info */
      waveformCtx.fillStyle = 'rgba(255,255,255,0.12)';
      waveformCtx.fillRect(0, cy - 0.5, W, 1);
    } else {
      waveformCtx.fillStyle = '#333';
      waveformCtx.fillRect(0, cy - 2.5, W, 5);
      if (playedW > 0) {
        waveformCtx.fillStyle = accent;
        waveformCtx.fillRect(0, cy - 2.5, playedW, 5);
      }
    }

    /* Layer 2: waveform amplitude bars */
    if (hasStereo || hasMono) {
      var SEGS  = waveformData.length;
      var slotW = W / SEGS;
      var gapW  = Math.max(0.5, slotW * 0.15);
      var bW    = Math.max(1, slotW - gapW);
      if (hasStereo) {
        var maxH = cy - 1;
        for (var i = 0; i < SEGS; i++) {
          var x      = i * slotW;
          var played = i < prog * SEGS;
          waveformCtx.globalAlpha = played ? 0.72 : 0.28;
          waveformCtx.fillStyle   = played ? accent : '#999';
          var lh = Math.max(1, waveformData[i]  * maxH);
          waveformCtx.fillRect(x, cy - lh, bW, lh);
          var rh = Math.max(1, waveformDataR[i] * maxH);
          waveformCtx.fillRect(x, cy, bW, rh);
        }
      } else {
        var maxBH = H * 0.88;
        for (var i = 0; i < SEGS; i++) {
          var bh = Math.max(2, waveformData[i] * maxBH);
          var x  = i * slotW;
          var y  = cy - bh / 2;
          waveformCtx.globalAlpha = i < prog * SEGS ? 0.38 : 0.22;
          waveformCtx.fillStyle   = '#fff';
          waveformCtx.fillRect(x, y, bW, bh);
        }
      }
      waveformCtx.globalAlpha = 1;
    }

    /* Layer 3: playhead dot */
    var px = Math.max(6, Math.min(W - 6, playedW));
    waveformCtx.fillStyle = prog > 0 ? '#fff' : 'transparent';
    waveformCtx.beginPath();
    waveformCtx.arc(px, cy, 6, 0, Math.PI * 2);
    waveformCtx.fill();
  }

  /* Initial draw + redraw on resize */
  drawWaveform(0);
  window.addEventListener('resize', function() {
    var p = progressBar && progressBar.max > 0 ? progressBar.value / progressBar.max : 0;
    drawWaveform(p);
  });
"""

    return (
        """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  /* Vite/TS migration Phase 3 (docs/IMPLEMENTATION_PLAN.md): runtime config
     read from the #ht-config JSON blob (_html.py::_render_player_config_json).
     Falls back to {} if the tag is missing (e.g. render_player_js() output
     used standalone in tests without a full render_media_page() document). */
  var _cfgEl = document.getElementById('ht-config');
  var CFG = JSON.parse((_cfgEl && _cfgEl.textContent) || '{}');
  var ITEM_NOUN = CFG.itemNoun || 'track';
  var FILE_EMOJI = CFG.fileEmoji || '';
  var API_PATH = CFG.apiPath || '';
  /* Derive sibling API endpoints from API_PATH (e.g. "/api/audio/tracks" ->
     "/api/audio"), replacing the former Python-side api_path.rsplit("/", 1)[0]
     string concatenation for every *_API_PATH var below. */
  function _apiBase() { return API_PATH.split('/').slice(0, -1).join('/'); }
  var OFFLINE_ENABLED = !!CFG.enableOffline;

  /* Placeholder SVG thumbnails — same dimensions as real thumbs so layout never shifts.
     Simple dark-grey squares with a subtle icon silhouette. */
  var FOLDER_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Cpath d='M30 45h25l7-10h28l0 0H90v40H30z' fill='%23444'/%3E%3C/svg%3E";
  var FILE_PLACEHOLDER  = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Ccircle cx='54' cy='72' r='12' fill='none' stroke='%23444' stroke-width='3'/%3E%3Crect x='63' y='38' width='3' height='34' fill='%23444'/%3E%3Crect x='57' y='38' width='12' height='4' rx='1' fill='%23444'/%3E%3C/svg%3E";

  /* SVG icons for play/pause — cross-platform, no emoji rendering.
     All of these mirror a constant in _svg.py — reference it directly
     (via the SVG_* imports at the top of this module) instead of
     hardcoding a second copy of the markup here.  IC_STAR, IC_STAR_FILLED,
     IC_STAR_EMPTY and IC_EDIT were previously stale hardcoded duplicates
     that silently shadowed updates made in _svg.py — see architecture.md. */
  var IC_PLAY  = '"""
        + (SVG_PLAY.replace("'", "\\'"))
        + """';
  var IC_PAUSE = '"""
        + (SVG_PAUSE.replace("'", "\\'"))
        + """';
  var IC_DL    = '"""
        + (SVG_DOWNLOAD.replace("'", "\\'"))
        + """';
  var IC_CHECK = '"""
        + (SVG_CHECK.replace("'", "\\'"))
        + """';
  var IC_FOLDER_PLAY = '"""
        + (SVG_FOLDER_PLAY.replace("'", "\\'"))
        + """';
  var IC_PIN = '"""
        + (SVG_PIN.replace("'", "\\'"))
        + """';
  var IC_STAR = '"""
        + (SVG_STAR.replace("'", "\\'"))
        + """';
  var IC_SHUFFLE = '"""
        + (SVG_SHUFFLE.replace("'", "\\'"))
        + """';
  var IC_REPEAT = '"""
        + (SVG_REPEAT.replace("'", "\\'"))
        + """';
  var IC_REPEAT_ONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17,1 21,5 17,9"/><path d="M3,11V9a4,4,0,0,1,4-4h14"/><polyline points="7,23 3,19 7,15"/><path d="M21,13v2a4,4,0,0,1-4,4H3"/><text x="12" y="15.5" text-anchor="middle" fill="currentColor" stroke="none" font-size="7" font-weight="bold">1</text></svg>';
  var IC_STAR_FILLED = '"""
        + (SVG_STAR.replace("'", "\\'"))
        + """';
  var IC_STAR_EMPTY  = '"""
        + (SVG_STAR_EMPTY.replace("'", "\\'"))
        + """';
  var IC_EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  var IC_EYE_OFF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  var IC_FILTER = '"""
        + (SVG_FILTER.replace("'", "\\'"))
        + """';
  var SHUFFLE_ENABLED = !!CFG.enableShuffle;
  var REPEAT_ENABLED = !!CFG.enableRepeat;
  var SKIP_INTRO_ENABLED = !!CFG.enableSkipIntro;
  var INTRO_API_PATH = _apiBase() + '/intro';
  var RATING_WRITE_ENABLED = !!CFG.enableRatingWrite;
  var MIN_RATING_THRESHOLD = CFG.minRating || 0;
  /* When ratings are enabled but no explicit threshold is configured,
     treat 1-star tracks as "ausgeblendet" (threshold=2, used with < comparison: r < 2 hides 1★).
     Setting min_rating=0 explicitly disables the feature entirely. */
  var _effectiveThreshold = MIN_RATING_THRESHOLD > 0 ? MIN_RATING_THRESHOLD : (RATING_WRITE_ENABLED ? 2 : 0);
  var DEBUG_FILTER = !!CFG.debugFilter;
  var RATING_API_PATH = _apiBase() + '/rating';
  var AUDIT_UNDO_PATH = _apiBase() + '/audit/undo';
  var RECENT_ENABLED = !!CFG.enableRecent;
  var RECENT_API_PATH = _apiBase() + '/recent';
  var AUTO_RESUME_ENABLED = !!CFG.enableAutoResume;
  var CROSSFADE_DURATION = CFG.crossfadeDuration || 0;
  var METADATA_EDIT_ENABLED = !!CFG.enableMetadataEdit;
  var METADATA_EDIT_PATH = _apiBase() + '/metadata/edit';
  var IC_EDIT = '"""
        + (SVG_EDIT.replace("'", "\\'"))
        + """';
  var IC_LYRICS = '"""
        + (SVG_LYRICS.replace("'", "\\'"))
        + """';
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
  var FOLDERS_API_PATH = _apiBase() + '/folders';
  var IC_PLAYLIST = '"""
        + (SVG_PLAYLIST.replace("'", "\\'"))
        + """';
  var IC_SMART_PLAYLIST = '"""
        + (SVG_SMART_PLAYLIST.replace("'", "\\'"))
        + """';
  var IC_QUEUE = '"""
        + (SVG_QUEUE.replace("'", "\\'"))
        + """';
  var IC_REMOVE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  var IC_TRASH = '"""
        + (SVG_TRASH.replace("'", "\\'"))
        + """';
  var IC_DOTS = '"""
        + (SVG_DOTS.replace("'", "\\'"))
        + """';
  var IC_REFRESH = '"""
        + (SVG_REFRESH.replace("'", "\\'"))
        + """';
  var LANG_TO_FLAG = {
    'de': '"""
        + (SVG_FLAG_DE.replace("'", "\\'"))
        + """',
    'en': '"""
        + (SVG_FLAG_EN.replace("'", "\\'"))
        + """',
    'fr': '"""
        + (SVG_FLAG_FR.replace("'", "\\'"))
        + """',
    'es': '"""
        + (SVG_FLAG_ES.replace("'", "\\'"))
        + """',
    'it': '"""
        + (SVG_FLAG_IT.replace("'", "\\'"))
        + """',
    'ja': '"""
        + (SVG_FLAG_JA.replace("'", "\\'"))
        + """',
    'ko': '"""
        + (SVG_FLAG_KO.replace("'", "\\'"))
        + """',
    'zh': '"""
        + (SVG_FLAG_ZH.replace("'", "\\'"))
        + """',
    'pt': '"""
        + (SVG_FLAG_PT.replace("'", "\\'"))
        + """',
    'ru': '"""
        + (SVG_FLAG_RU.replace("'", "\\'"))
        + """'
  };
  var AUDIOBOOK_DIRS = CFG.audiobookDirs || [];
  var LANG_GROUPS = CFG.languageGroups || {};
  var DEFAULT_LANG = CFG.defaultLanguage || 'de';
  /* BPM pill (audio only) — display/heatmap range, configurable server-side
     (default 0-180, HOMETOOLS_BPM_MIN/HOMETOOLS_BPM_MAX). The "calculate"
     affordance (yellow-glow clickable "?") and the editable/clickable
     known-value pill are additionally gated by the Tools-panel "BPM
     berechnen" toggle (_toolState.bpmCalc) — see
     player_js/_track_render.py / _search_filter.py. */
  var BPM_MIN = CFG.bpmMin || 0;
  var BPM_MAX = CFG.bpmMax || 180;
  var BPM_CALC_API_PATH = _apiBase() + '/bpm/calculate';
  /* BPM-adjust popup (slower/faster/manual — see
     player_js/_track_render.py::_openBpmAdjustMenu). */
  var BPM_ADJUST_API_PATH = _apiBase() + '/bpm/adjust';
  var BPM_SET_API_PATH = _apiBase() + '/bpm/set';
  var IC_CHEVRONS_DOWN = '"""
        + (SVG_CHEVRONS_DOWN.replace("'", "\\'"))
        + """';
  var IC_CHEVRONS_UP = '"""
        + (SVG_CHEVRONS_UP.replace("'", "\\'"))
        + """';
"""
        + render_core_js(waveform_js=waveform_js)
        + render_queue_js(sprite_preview_js=sprite_preview_js, waveform_setup_js=waveform_setup_js)
        + render_folder_browse_js()
        + render_search_filter_js()
        + render_track_render_js()
        + render_library_tools_js()
        + render_playlists_js()
        + render_smart_playlists_js()
        + render_drag_drop_init_js()
    )
