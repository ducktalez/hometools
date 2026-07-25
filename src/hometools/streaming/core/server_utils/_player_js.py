"""Player JavaScript generation for the streaming UI."""

from __future__ import annotations

from ._svg import (  # noqa: F401
    SVG_BACK,
    SVG_CAST,
    SVG_CHECK,
    SVG_CLOSE_X,
    SVG_DOTS,
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
    enable_skip_intro: bool = False,
) -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).

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
        waveform_setup_js = (
            """
  /* ── classic mode: cached stereo waveform overlay ── */
  var WAVEFORM_API_PATH = '"""
            + api_path.rsplit("/", 1)[0]
            + """/waveform';

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
        )

    return (
        """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  var ITEM_NOUN = '"""
        + (item_noun)
        + """';
  var FILE_EMOJI = '"""
        + (file_emoji)
        + """';
  var API_PATH = '"""
        + (api_path)
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
  var SKIP_INTRO_ENABLED = """
        + ("true" if enable_skip_intro else "false")
        + """;
  var INTRO_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/intro';
  var RATING_WRITE_ENABLED = """
        + ("true" if enable_rating_write else "false")
        + """;
  var MIN_RATING_THRESHOLD = """
        + (str(min_rating))
        + """;
  /* When ratings are enabled but no explicit threshold is configured,
     treat 1-star tracks as "ausgeblendet" (threshold=2, used with < comparison: r < 2 hides 1★).
     Setting min_rating=0 explicitly disables the feature entirely. */
  var _effectiveThreshold = MIN_RATING_THRESHOLD > 0 ? MIN_RATING_THRESHOLD : (RATING_WRITE_ENABLED ? 2 : 0);
  var DEBUG_FILTER = """
        + ("true" if debug_filter else "false")
        + """;
  var RATING_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/rating';
  var AUDIT_UNDO_PATH = '"""
        + (api_path.rsplit("/", 1)[0].replace("/api/", "/api/"))
        + """/audit/undo';
  var RECENT_ENABLED = """
        + ("true" if enable_recent else "false")
        + """;
  var RECENT_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/recent';
  var AUTO_RESUME_ENABLED = """
        + ("true" if enable_auto_resume else "false")
        + """;
  var CROSSFADE_DURATION = """
        + (str(crossfade_duration))
        + """;
  var METADATA_EDIT_ENABLED = """
        + ("true" if enable_metadata_edit else "false")
        + """;
  var METADATA_EDIT_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/metadata/edit';
  var IC_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  var IC_LYRICS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>';
  var LYRICS_ENABLED = """
        + ("true" if enable_lyrics else "false")
        + """;
  var LYRICS_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/lyrics';
  var PLAYLISTS_ENABLED = """
        + ("true" if enable_playlists else "false")
        + """;
  var PLAYLISTS_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/playlists';
  var PLAYLISTS_VERSION_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/playlists/version';
  var PLAYLISTS_SMART_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/playlists/smart';
  var FOLDER_ORDER_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/folder-order';
  var MOVE_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/move-file';
  var DELETE_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/delete-file';
  var REVEAL_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/reveal';
  var FOLDERS_API_PATH = '"""
        + (api_path.rsplit("/", 1)[0])
        + """/folders';
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
  var AUDIOBOOK_DIRS = """
        + (__import__("json").dumps(__import__("hometools.config", fromlist=["get_audiobook_dirs"]).get_audiobook_dirs()))
        + """;
  var LANG_GROUPS = """
        + (language_groups_json)
        + """;
  var DEFAULT_LANG = '"""
        + (default_language)
        + """';
"""
        + render_core_js(waveform_js=waveform_js)
        + render_queue_js(sprite_preview_js=sprite_preview_js, waveform_setup_js=waveform_setup_js)
        + render_folder_browse_js()
        + render_search_filter_js()
        + render_track_render_js()
        + render_library_tools_js(playlist_sync_interval_ms=playlist_sync_interval_ms)
        + render_playlists_js()
        + render_smart_playlists_js()
        + render_drag_drop_init_js()
    )
