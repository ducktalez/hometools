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


def render_player_js() -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).
    Clicking a folder navigates deeper into the hierarchy.  Leaf folders
    (no sub-folders) are displayed as playlists.  A breadcrumb trail and
    back button allow navigating up.  View preference is stored in
    localStorage.

    All request-varying config (``api_path``, ``enable_shuffle``,
    ``min_rating``, ``language_groups_json``, ...) is now read at runtime
    from the ``#ht-config`` JSON blob (``CFG.*``, rendered by
    ``_html.py::_render_player_config_json``) — see "Vite/TypeScript
    migration" Phase 3 in docs/IMPLEMENTATION_PLAN.md. Long-pressing the
    shuffle button activates weighted shuffle (items with higher ratings
    are more likely to play). Works with offline downloads too.
    """
    # -- waveform/thumbnail element setup -------------------------------------
    waveform_js = """
  var progressTrack  = document.getElementById('progress-track');
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
"""

    # -- sprite sheet preview (always available for video, both modes) ----------
    sprite_preview_js = """
  /* sprite sheet preview (video scrubber thumbnails): webui/src/spritePreview.ts */
  window._initSpritePreview({
    player: player, isVideoMode: isVideoMode,
    track: progressTrack,
    preview: document.getElementById('thumb-preview'),
    canvas: document.getElementById('thumb-canvas'),
    timeEl: document.getElementById('thumb-time'),
    fmtTime: fmtTime
  });
  function loadSpriteData(relativePath) { window._loadSpriteData(relativePath); }
"""

    waveform_setup_js = """
  /* Waveform (cached stereo peaks from the server) ported to webui/src/waveform.ts.
     Wrappers keep the bare names used by _library_tools.py. */
  window._initWaveform({
    canvas: document.getElementById('waveform-canvas'),
    isAudioMode: isAudioMode,
    apiPath: _apiBase() + '/waveform',
    currentFraction: function() { return player.duration > 0 ? player.currentTime / player.duration : 0; },
    resizeFraction: function() { return progressBar && progressBar.max > 0 ? progressBar.value / progressBar.max : 0; }
  });
  function generateWaveform(url, relativePath) { window._generateWaveform(url, relativePath); }
  function drawWaveform(progress) { window._drawWaveform(progress); }
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
