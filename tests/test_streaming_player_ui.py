"""Tests for the configurable player bar (classic and waveform modes)."""

import re as _re
from pathlib import Path

from hometools.streaming.core.server_utils import render_base_css, render_media_page, render_player_js

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page(media="audio", style="classic"):
    return render_media_page(
        title="Test",
        emoji="",
        items_json="[]",
        media_element_tag=media,
        api_path="/api/test",
        item_noun="track" if media == "audio" else "video",
        player_bar_style=style,
    )


def _js(style="classic"):
    return render_player_js(player_bar_style=style)


def _webui_src(filename):
    """Read a ported TypeScript source from the Vite/TS migration scaffold
    (`src/hometools/streaming/core/webui/src/`) — used by tests that assert
    on functions/logic already ported out of the Python-generated JS (see
    `webui/README.md` → "Opportunistic migration rule")."""
    path = Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / filename
    return path.read_text(encoding="utf-8")


def _extract_ht_config(page):
    """Parse the `#ht-config` JSON blob out of a rendered page.

    Shared helper for Vite/TS migration Phase 3 tests that need to verify
    a runtime config value rather than a Python-interpolated JS literal
    (see docs/IMPLEMENTATION_PLAN.md "Vite/TypeScript migration").
    """
    import json

    m = _re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', page, _re.S)
    assert m, "ht-config script tag missing"
    return json.loads(m.group(1))


# ---------------------------------------------------------------------------
# CSS: both modes have their styles
# ---------------------------------------------------------------------------


def test_css_contains_classic_player_bar():
    css = render_base_css()
    assert ".player-bar.classic" in css


def test_css_contains_waveform_player_bar():
    css = render_base_css()
    assert ".player-bar.waveform" in css


def test_css_classic_is_single_row():
    css = render_base_css()
    assert ".player-bar.classic" in css
    assert "align-items: center" in css


def test_css_classic_progress_wraps_on_small_screens():
    """progress-wrap must use flex-wrap and a non-zero flex-basis so it wraps below
    controls when the screen is too narrow to fit everything in one row."""
    css = render_base_css()
    assert "flex-wrap: wrap" in css  # bar allows wrapping
    assert "1 1 160px" in css  # progress-wrap basis triggers wrap threshold
    assert "min-height" in css  # bar grows instead of clipping


def test_css_waveform_is_column_layout():
    css = render_base_css()
    assert "flex-direction: column" in css


def test_css_contains_progress_track():
    css = render_base_css()
    assert ".progress-track" in css


def test_css_contains_waveform_canvas():
    css = render_base_css()
    assert ".waveform-canvas" in css


def test_css_contains_thumb_preview():
    css = render_base_css()
    assert ".thumb-preview" in css


def test_css_queue_panel_is_fixed_overlay_above_player_bar():
    css = render_base_css()
    assert ".queue-panel" in css
    assert "position: fixed;" in css
    assert "left: 0; right: 0;" in css
    # clip-path hides it, .visible reveals it
    assert "clip-path: inset(100% 0 0 0)" in css
    assert ".queue-panel.visible" in css


def test_css_queue_drag_handle_present():
    """Queue panel must include a drag-handle for user-resizable height."""
    css = render_base_css()
    assert ".queue-drag-handle" in css
    assert "cursor: grab" in css
    assert ".queue-drag-handle-bar" in css


def test_queue_drag_handle_html_present():
    """Queue panel HTML must contain the drag-handle element."""
    page = render_media_page(
        title="Test",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        item_noun="track",
    )
    assert 'id="queue-drag-handle"' in page
    assert "queue-drag-handle-bar" in page


def test_queue_resize_js_persists_height():
    """JS must contain localStorage persistence for queue height."""
    js = render_player_js()
    assert "hometools_queue_height" in js
    assert "localStorage.setItem" in js
    assert "localStorage.getItem" in js


def test_queue_panel_bottom_set_dynamically_by_js():
    """openQueuePanel must measure player-bar height and set bottom + max-height."""
    js = render_player_js()
    assert "function _syncQueueBottom()" in js
    assert ".offsetHeight" in js
    assert "style.bottom" in js
    assert "style.maxHeight" in js
    assert "_syncQueueBottom();" in js


def test_css_contains_classic_range_styling():
    css = render_base_css()
    assert ".player-bar.classic input[type=range]" in css


# ---------------------------------------------------------------------------
# HTML: classic mode (default)
# ---------------------------------------------------------------------------


def test_classic_html_has_classic_class():
    page = _page(style="classic")
    assert "player-bar classic" in page


def test_classic_html_has_inline_range():
    page = _page(style="classic")
    assert 'id="progress-bar"' in page
    # Classic mode now has waveform-canvas for canvas-based progress drawing (pre-waveform placeholder)
    assert 'id="waveform-canvas"' in page
    # Classic mode now has progress-track for sprite sheet preview support
    assert 'id="progress-track"' in page


def test_classic_html_has_controls():
    page = _page(style="classic")
    assert 'id="btn-play"' in page
    assert 'id="btn-prev"' in page
    assert 'id="btn-next"' in page


def test_classic_html_has_time_labels():
    page = _page(style="classic")
    assert 'id="time-cur"' in page
    assert 'id="time-dur"' in page


def test_classic_html_audio_element():
    page = _page(media="audio", style="classic")
    assert "<audio" in page


def test_classic_html_video_element():
    page = _page(media="video", style="classic")
    assert "<video" in page


# ---------------------------------------------------------------------------
# HTML: waveform mode
# ---------------------------------------------------------------------------


def test_waveform_html_has_waveform_class():
    page = _page(style="waveform")
    assert "player-bar waveform" in page


def test_waveform_html_has_player_bar_top():
    page = _page(style="waveform")
    assert 'class="player-bar-top"' in page


def test_waveform_html_has_progress_track():
    page = _page(style="waveform")
    assert 'id="progress-track"' in page


def test_waveform_html_has_canvas():
    page = _page(style="waveform")
    assert 'id="waveform-canvas"' in page


def test_waveform_html_has_thumb_preview():
    page = _page(style="waveform")
    assert 'id="thumb-preview"' in page
    assert 'id="thumb-canvas"' in page
    assert 'id="thumb-time"' in page


def test_waveform_html_controls_before_progress():
    page = _page(style="waveform")
    top_pos = page.index('class="player-bar-top"')
    wrap_pos = page.index('class="progress-wrap"')
    assert top_pos < wrap_pos


def test_waveform_html_video_page():
    page = _page(media="video", style="waveform")
    assert 'id="progress-track"' in page
    assert 'id="waveform-canvas"' in page
    assert "<video" in page


# ---------------------------------------------------------------------------
# JS: classic mode
# ---------------------------------------------------------------------------


def test_classic_js_has_no_waveform_data():
    js = _js(style="classic")
    # Classic mode uses server-side cached waveform (no client-side AudioContext decoding)
    assert "decodeAudioData" not in js
    # Classic mode DOES use waveformAbort to cancel in-flight waveform fetches
    assert "waveformAbort" in js
    # Classic mode fetches waveform from the server API, not the audio file itself
    assert "WAVEFORM_API_PATH" in js


def test_classic_js_has_no_thumb_video():
    js = _js(style="classic")
    assert "thumbVideo" not in js
    # Classic mode now has sprite-based mousemove for video scrubber preview
    assert "spriteData" in js
    assert "mousemove" in js


def test_classic_js_has_stub_functions():
    js = _js(style="classic")
    assert "generateWaveform" in js
    assert "drawWaveform" in js


def test_classic_js_has_core_player():
    js = _js(style="classic")
    assert "playTrack" in js
    assert "fmtTime" in js
    assert "progressBar" in js


# ---------------------------------------------------------------------------
# JS: waveform mode
# ---------------------------------------------------------------------------


def test_waveform_js_has_audio_mode_detection():
    js = _js(style="waveform")
    assert "isAudioMode" in js
    assert "isVideoMode" in js


def test_waveform_js_has_generate_waveform():
    js = _js(style="waveform")
    assert "generateWaveform" in js
    assert "decodeAudioData" in js
    assert "AbortController" in js


def test_waveform_js_has_draw_waveform():
    js = _js(style="waveform")
    assert "drawWaveform" in js
    assert "slotW" in js


def test_waveform_js_has_waveform_data():
    js = _js(style="waveform")
    assert "waveformData" in js


def test_waveform_js_has_thumb_video():
    js = _js(style="waveform")
    # thumbVideo replaced by sprite sheet approach
    assert "spriteData" in js
    assert "spriteImg" in js
    assert "mousemove" in js
    assert "mouseleave" in js
    assert "drawImage" in js


def test_waveform_js_has_video_mode_class():
    js = _js(style="waveform")
    assert "video-mode" in js


def test_waveform_js_calls_generate_on_play():
    js = _js(style="waveform")
    # generateWaveform now accepts (url, relativePath) — url used in waveform mode
    assert "generateWaveform(playback.url, t.relative_path)" in js


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_config_get_player_bar_style():
    from hometools.config import get_player_bar_style

    style = get_player_bar_style()
    assert style in ("classic", "waveform")


def test_render_media_page_accepts_style_param():
    for style in ("classic", "waveform"):
        page = _page(style=style)
        assert 'id="progress-bar"' in page
        assert 'id="btn-play"' in page
        assert 'id="folder-grid"' in page


# ---------------------------------------------------------------------------
# PiP (Picture-in-Picture) support
# ---------------------------------------------------------------------------


def test_pip_button_in_classic_html():
    page = _page(media="video", style="classic")
    assert 'id="btn-pip"' in page
    assert "pip-btn" in page


def test_pip_button_in_waveform_html():
    page = _page(media="video", style="waveform")
    assert 'id="btn-pip"' in page
    assert "pip-btn" in page


def test_pip_button_in_audio_page():
    """Audio pages also get the button (hidden by JS when not a video player)."""
    page = _page(media="audio", style="classic")
    assert 'id="btn-pip"' in page


def test_pip_js_has_request_and_exit():
    js = _js(style="classic")
    assert "requestPiP" in js
    assert "exitPiP" in js


def test_pip_js_has_pip_supported_detection():
    js = _js(style="classic")
    assert "pictureInPictureEnabled" in js
    assert "webkitSupportsPresentationMode" in js


def test_pip_js_has_visibility_change_pip():
    js = _js(style="classic")
    assert "visibilitychange" in js
    assert "pipActive" in js


def test_pip_js_has_enter_leave_events():
    js = _js(style="waveform")
    assert "enterpictureinpicture" in js
    assert "leavepictureinpicture" in js


def test_pip_css_styling():
    css = render_base_css()
    assert ".ctrl-btn.pip-btn" in css


def test_bg_audio_runs_for_all_video_players():
    """bgAudio mirror is no longer restricted to iOS only."""
    js = _js(style="classic")
    assert "if (!isVideoPlayer) return;" in js
    # The old iOS-only guard should be gone
    assert "if (!isVideoPlayer || !isIOS) return;" not in js


# ---------------------------------------------------------------------------
# Background playback: wasPlaying flag + volume approach
# ---------------------------------------------------------------------------


def test_js_has_was_playing_flag():
    """The wasPlaying flag must exist and be set on 'playing' event."""
    js = _js(style="classic")
    assert "wasPlaying" in js
    assert "wasPlaying = true" in js
    assert "wasPlaying = false" in js


def test_js_uses_muted_not_volume():
    """bgAudio must use muted (not volume) because iOS ignores volume changes."""
    js = _js(style="classic")
    assert "bgAudio.muted = true" in js or "bg.muted = true" in js
    assert "bgAudio.muted = false" in js
    # Must NOT use volume approach (read-only on iOS → double audio)
    assert "bgAudio.volume = 0" not in js
    assert "bgAudio.volume = 1" not in js


def test_js_visibility_checks_was_playing():
    """visibilitychange must check wasPlaying, not player.paused."""
    js = _js(style="classic")
    assert "document.hidden && wasPlaying" in js


def test_js_has_bg_audio_is_active():
    """Helper function bgAudioIsActive must exist."""
    js = _js(style="classic")
    assert "bgAudioIsActive" in js


def test_video_has_autopictureinpicture_attribute():
    """Video pages should have autopictureinpicture on the element."""
    page = _page(media="video", style="waveform")
    assert "autopictureinpicture" in page


def test_video_has_no_native_controls():
    """Video element must NOT have native controls — custom player-bar is used instead.
    Native controls were removed to fix the overlay height bug (the browser's control
    bar took space inside the video element, causing the video to appear small)."""
    page = _page(media="video", style="classic")
    assert '<video id="player" preload="auto" playsinline autopictureinpicture>' in page
    assert "controls" not in page.split('<video id="player"', 1)[1].split(">", 1)[0]


def test_audio_element_has_no_controls():
    """Audio element should NOT have controls or autopictureinpicture."""
    page = _page(media="audio", style="classic")
    assert '<audio id="player" preload="auto" playsinline>' in page
    assert '<audio id="player" preload="auto" playsinline controls' not in page


def test_video_page_no_apple_web_app_capable():
    """Video pages must NOT set apple-mobile-web-app-capable (blocks PiP on iOS)."""
    page = _page(media="video", style="classic")
    assert "apple-mobile-web-app-capable" not in page


def test_audio_page_has_apple_web_app_capable():
    """Audio pages should keep apple-mobile-web-app-capable for standalone mode."""
    page = _page(media="audio", style="classic")
    assert "apple-mobile-web-app-capable" in page


def test_js_has_fullscreen_logic():
    js = _js(style="classic")
    assert "requestFullscreen" in js
    assert "webkitEnterFullscreen" in js
    assert "fullscreenEnabled" in js


def test_js_sets_media_session_playback_state():
    """When going to background, playbackState should be set to 'playing'."""
    js = _js(style="classic")
    assert "mediaSession.playbackState" in js


def test_pause_handler_checks_document_hidden():
    """The pause handler must not react when browser auto-pauses (hidden)."""
    js = _js(style="classic")
    assert "document.hidden" in js


def test_pause_handler_clears_was_playing():
    """The pause event must clear wasPlaying so tab-switch does not resume."""
    js = _js(style="classic")
    # The pause handler should set wasPlaying = false when visible (user-initiated)
    assert "wasPlaying = false" in js
    # Must also stop bgAudio and sync timer
    assert "bgAudio.pause()" in js or "bgAudio.muted = true" in js


def test_pause_handler_stops_bg_audio():
    """A user pause (native controls) must also stop bgAudio and sync timer."""
    js = _js(style="classic")
    assert "stopBgSync()" in js


def test_visibility_hidden_pauses_video():
    """Going hidden must pause the video to prevent double audio on desktop."""
    js = _js(style="classic")
    # The visibilitychange handler should call player.pause() when going hidden
    assert "player.pause()" in js


# ---------------------------------------------------------------------------
# playTrack robustness & metadata refresh
# ---------------------------------------------------------------------------


def test_js_play_track_calls_load():
    """playTrack must call player.load() before play() for reliable playback."""
    js = _js(style="classic")
    assert "player.load()" in js


def test_js_play_track_has_canplay_retry():
    """If play() fails, playTrack should retry on canplay event."""
    js = _js(style="classic")
    assert "canplay" in js
    assert "once: true" in js


def test_js_has_refresh_metadata_function():
    """refreshMetadata function should exist and call the metadata API."""
    js = _js(style="classic")
    assert "refreshMetadata" in js
    assert "/metadata?path=" in js


def test_js_play_track_calls_refresh_metadata():
    """playTrack should call refreshMetadata to update track info on play."""
    js = _js(style="classic")
    assert "refreshMetadata(t)" in js


def test_js_has_api_path_variable():
    """The API_PATH variable should be injected into the JavaScript."""
    js = _js(style="classic")
    assert "API_PATH" in js


def test_js_loads_initial_catalog_async():
    """The shell should fetch the catalog asynchronously after initial page render."""
    js = _js(style="classic")
    assert "function loadInitialCatalog" in js
    assert "fetch(API_PATH, { cache: 'no-store' })" in js
    assert "Loading library" in js
    assert "Initial catalog fetch started" in js
    assert "Initial catalog response received after" in js


def test_js_retries_initial_catalog_while_server_is_loading():
    """The client should poll again when the server reports a loading state."""
    js = _js(style="classic")
    assert "scheduleInitialCatalogRetry" in js
    assert "data && data.loading" in js
    assert "fetch(API_PATH, { cache: 'no-store' })" in js


def test_js_shows_indexing_toast_for_refreshing_state():
    """When data.refreshing is set, the UI should show an indexing toast, not a full-screen loader."""
    js = _js(style="classic")
    assert "showIndexingToast" in js
    assert "hideIndexingToast" in js
    assert "scheduleBackgroundRefresh" in js
    assert "data.refreshing" in js
    assert "ht-indexing-toast" in js


def test_js_loading_state_shows_message_in_folder_grid():
    js = _js(style="classic")
    assert "Loading library" in js
    assert "empty-hint" in js


def test_service_worker_uses_network_first_for_documents():
    """HTML navigations should prefer fresh network responses to avoid stale shell pages."""
    from hometools.streaming.core.server_utils import render_pwa_service_worker

    sw = render_pwa_service_worker()
    assert "event.request.mode === 'navigate'" in sw
    assert "Offline — page not cached" in sw


# ---------------------------------------------------------------------------
# Shuffle mode — audio-only feature, implemented in core
# ---------------------------------------------------------------------------


def _audio_page_with_shuffle():
    """Audio page with shuffle enabled (as the audio server enables it)."""
    return render_media_page(
        title="Test",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
        item_noun="track",
        enable_shuffle=True,
    )


def test_shuffle_btn_present_in_audio_page_with_shuffle_enabled():
    """Shuffle button must appear in the audio player bar when enable_shuffle=True."""
    page = _audio_page_with_shuffle()
    assert 'id="btn-shuffle"' in page


def test_shuffle_btn_absent_in_default_audio_page():
    """Shuffle button must NOT appear when enable_shuffle=False (default)."""
    page = _page(media="audio")
    assert 'id="btn-shuffle"' not in page


def test_shuffle_btn_absent_in_video_page():
    """Shuffle button must NOT appear in the video page (enable_shuffle defaults to False)."""
    page = _page(media="video")
    assert 'id="btn-shuffle"' not in page


def test_shuffle_js_reads_enabled_flag_from_runtime_config():
    """SHUFFLE_ENABLED must be sourced from the runtime #ht-config blob
    (Vite/TS migration Phase 3), not a Python-interpolated literal — the
    actual true/false value is asserted at the #ht-config JSON level, see
    TestHtConfigJson.test_ht_config_reflects_feature_flags.
    """
    js = _js()
    assert "SHUFFLE_ENABLED = !!CFG.enableShuffle" in js


def test_shuffle_js_has_core_functions():
    """Shuffle logic functions must always be present (not gated by a flag —
    only the runtime SHUFFLE_ENABLED boolean toggles UI behavior)."""
    js = _js()
    assert "fisherYates" in js
    assert "buildWeightedQueue" in js
    assert "buildNormalQueue" in js
    assert "rebuildShuffleQueue" in js
    assert "cycleShuffle" in js
    assert "activateWeightedShuffle" in js
    assert "updateShuffleBtn" in js


def test_shuffle_js_has_next_prev_index():
    """nextIndex / prevIndex must exist and respect shuffle state."""
    js = _js()
    assert "function nextIndex" in js
    assert "function prevIndex" in js
    assert "shuffleQueue" in js
    assert "shufflePos" in js


def test_shuffle_js_restores_from_localstorage():
    """Shuffle preference must be loaded from localStorage on startup."""
    js = _js()
    assert "ht-shuffle-mode" in js
    assert "localStorage.getItem" in js


def test_shuffle_js_has_long_press_binding():
    """Shuffle button must support long-press for weighted shuffle mode."""
    js = _js()
    assert "_startShuffleLongPress" in js
    assert "touchstart" in js
    assert "activateWeightedShuffle" in js


def test_shuffle_css_has_active_styles():
    """CSS must include styles for both shuffle active states."""
    from hometools.streaming.core.server_utils import render_base_css

    css = render_base_css()
    assert "shuffle-active" in css
    assert "shuffle-weighted" in css


def test_shuffle_btn_in_both_player_bar_styles():
    """Shuffle button must appear in both classic and waveform player bars."""
    for style in ("classic", "waveform"):
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/audio/tracks",
            item_noun="track",
            player_bar_style=style,
            enable_shuffle=True,
        )
        assert 'id="btn-shuffle"' in page, f"Missing shuffle button in {style} player bar"


def test_audio_server_enables_shuffle():
    """The audio server must enable shuffle in its rendered HTML."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-shuffle"' in html
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableShuffle"] is True


def test_video_server_does_not_enable_shuffle():
    """The video server must NOT include the shuffle button."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-shuffle"' not in html
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableShuffle"] is False


# ---------------------------------------------------------------------------
# Repeat mode
# ---------------------------------------------------------------------------


def test_repeat_btn_present_when_enabled():
    """Repeat button must appear in the HTML when enable_repeat=True."""
    page = render_media_page(
        title="Test",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        item_noun="track",
        enable_repeat=True,
    )
    assert 'id="btn-repeat"' in page


def test_repeat_btn_absent_when_disabled():
    """Repeat button must NOT appear when enable_repeat=False (default)."""
    page = _page()
    assert 'id="btn-repeat"' not in page


def test_repeat_js_reads_enabled_flag_from_runtime_config():
    """REPEAT_ENABLED must be sourced from the runtime #ht-config blob
    (Vite/TS migration Phase 3), not a Python-interpolated literal — the
    actual true/false value is asserted at the #ht-config JSON level, see
    TestHtConfigJson.test_ht_config_reflects_feature_flags.
    """
    js = _js()
    assert "REPEAT_ENABLED = !!CFG.enableRepeat" in js


def test_repeat_js_has_core_functions():
    """Repeat logic functions must always be present (not gated by a flag —
    only the runtime REPEAT_ENABLED boolean toggles UI behavior)."""
    js = _js()
    assert "cycleRepeat" in js
    assert "updateRepeatBtn" in js
    assert "repeatMode" in js
    assert "IC_REPEAT_ONE" in js
    assert "IC_REPEAT" in js


def test_repeat_js_restores_from_localstorage():
    """Repeat preference must be loaded from localStorage on startup."""
    js = _js()
    assert "ht-repeat-mode" in js


def test_repeat_css_has_active_styles():
    """CSS must include styles for repeat active states."""
    css = render_base_css()
    assert "repeat-active" in css
    assert "repeat-one" in css


def test_repeat_btn_in_both_player_bar_styles():
    """Repeat button must appear in both classic and waveform player bars."""
    for style in ("classic", "waveform"):
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/audio/tracks",
            item_noun="track",
            player_bar_style=style,
            enable_repeat=True,
        )
        assert 'id="btn-repeat"' in page, f"Missing repeat button in {style} player bar"


def test_audio_server_enables_repeat():
    """The audio server must enable repeat in its rendered HTML."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-repeat"' in html
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableRepeat"] is True


def test_video_server_enables_repeat():
    """The video server must enable repeat in its rendered HTML."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-repeat"' in html
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableRepeat"] is True


def test_repeat_one_suppresses_crossfade():
    """When repeat mode is 'one', the crossfade trigger must be skipped."""
    js = render_player_js()
    assert "repeatMode !== 'one'" in js


def test_repeat_nextindex_returns_minus_one_when_off():
    """nextIndex must contain logic to return -1 (stop) when repeat is off at end of list."""
    js = render_player_js()
    assert "repeat" in js.lower()
    # When repeat is 'all' → wrap to first playable; when off → return -1
    assert "return repeatMode === 'all' ? 0 : -1" in js


def test_play_next_item_handles_repeat_one():
    """playNextItem must restart current track when repeat mode is 'one'."""
    js = render_player_js()
    assert "repeatMode === 'one'" in js
    assert "player.currentTime = 0" in js


def test_shuffle_queue_rebuild_in_render_tracks():
    """JS must rebuild the shuffle queue when filteredItems changes (applyFilter)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    # rebuildShuffleQueue must be called inside renderTracks
    # filteredItems is set to realTracks (debug-mode aware) instead of plain tracks
    assert "filteredItems = realTracks" in js
    assert "rebuildShuffleQueue" in js


def test_queue_next_logic_is_centralized_in_play_next_item():
    """All Next triggers must use the same queue-first helper."""
    js = render_player_js()
    assert "function playNextItem()" in js
    assert "btnNext.addEventListener('click', playNextItem);" in js
    assert "navigator.mediaSession.setActionHandler('nexttrack', function() {" in js
    assert "bgAudio.addEventListener('ended', function() {" in js
    assert "playNextItem();" in js


def test_queue_dom_refs_requery_detached_nodes():
    """Queue DOM resolver must refresh detached references to avoid invisible panels."""
    js = render_player_js()
    assert "function _domNodeMissingOrDetached(el)" in js
    assert "!el.isConnected" in js
    assert "function openQueuePanel()" in js
    assert "_ensureQueueDom();" in js


def test_queue_panel_outside_player_bar():
    """Queue panel must NOT be a child of .player-bar (stacking context trap)."""
    for style in ("classic", "waveform"):
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/test",
            item_noun="track",
            player_bar_style=style,
        )
        # queue-panel must appear BEFORE the player-bar in the HTML
        queue_pos = page.index('id="queue-panel"')
        bar_pos = page.index('class="player-bar')
        assert queue_pos < bar_pos, f"Queue panel must be outside (before) player-bar in {style} mode"


# ---------------------------------------------------------------------------
# Rating write — audio-only feature, star buttons in player
# ---------------------------------------------------------------------------


def _audio_page_with_rating():
    return render_media_page(
        title="Test",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
        item_noun="track",
        enable_rating_write=True,
    )


def test_rating_stars_present_in_player_html():
    """Player bar must contain the rating container when enable_rating_write=True."""
    page = _audio_page_with_rating()
    assert 'id="player-rating"' in page


def test_rating_stars_hidden_by_default_in_html():
    """Rating container must start hidden (filled by JS on track select)."""
    page = _audio_page_with_rating()
    assert 'id="player-rating" hidden' in page


def test_rating_stars_absent_when_disabled():
    """Rating container must still be present (always rendered for simplicity)."""
    page = _page(media="audio")
    # Even without enable_rating_write the element is rendered (JS disables interaction)
    assert 'id="player-rating"' in page


def test_rating_write_js_flag_true():
    """RATING_WRITE_ENABLED must be sourced from the runtime #ht-config blob
    (Vite/TS migration Phase 3) — the actual true/false value is asserted at
    the #ht-config JSON level (see test_audio_server_enables_rating_write /
    test_video_server_does_not_enable_rating_write below)."""
    js = render_player_js()
    assert "RATING_WRITE_ENABLED = !!CFG.enableRatingWrite" in js


def test_rating_write_js_flag_false_by_default():
    """Same runtime-config note as test_rating_write_js_flag_true."""
    js = _js()
    assert "RATING_WRITE_ENABLED = !!CFG.enableRatingWrite" in js


def test_rating_api_path_injected():
    """RATING_API_PATH is derived at runtime via _apiBase() (Phase 3)."""
    js = render_player_js()
    assert "RATING_API_PATH = _apiBase() + '/rating'" in js


def test_rating_js_has_render_and_set_functions():
    """renderPlayerRating and setRating JS functions must exist."""
    js = render_player_js()
    assert "renderPlayerRating" in js
    assert "setRating" in js


def test_rating_js_calls_fetch_rating_api():
    """setRating must call fetch with RATING_API_PATH and POST method."""
    js = render_player_js()
    assert "fetch(RATING_API_PATH" in js
    assert "'POST'" in js


def test_rating_js_calls_render_on_play():
    """renderPlayerRating must be called inside playItem when a track is selected."""
    js = render_player_js()
    assert "renderPlayerRating" in js


def test_rating_js_updates_after_metadata_refresh():
    """After refreshMetadata, renderPlayerRating should be called with updated value."""
    js = render_player_js()
    assert "renderPlayerRating(meta.rating)" in js


def test_rating_css_has_star_styles():
    """CSS must contain styles for rating stars in the player."""
    css = render_base_css()
    assert ".player-rating" in css
    assert ".player-rating-star" in css


def test_rating_css_has_active_and_hover_states():
    """CSS must include active and hover states for rating stars."""
    css = render_base_css()
    assert ".player-rating-star.active" in css
    assert ".player-rating-star.hover" in css


def test_rating_toggle_to_zero_via_player_bar():
    """Clicking the already-active star must pass 0 to setRating (toggle off)."""
    js = render_player_js()
    # The click handler must compute `current` from filteredItems and call setRating(0) on match
    assert "clicked === current ? 0 : clicked" in js


def test_rating_toggle_to_zero_via_inline_stars():
    """Clicking the already-active inline star must pass 0 to setInlineRating (toggle off)."""
    js = render_player_js()
    assert "_clicked === _cur ? 0 : _clicked" in js


def test_set_rating_patches_all_items():
    """setRating success callback must call _patchAllItemsRating to keep allItems in sync."""
    js = render_player_js()
    assert "_patchAllItemsRating" in js


def test_set_rating_updates_track_rating_bar():
    """setRating success callback must call _updateTrackRatingBar to refresh the DOM."""
    js = render_player_js()
    assert "_updateTrackRatingBar" in js


def test_undo_rating_patches_all_items():
    """undoRating success callback must call _patchAllItemsRating."""
    js = render_player_js()
    # _patchAllItemsRating called in both setRating and undoRating
    assert js.count("_patchAllItemsRating") >= 2


def test_rating_toast_zero_stars_label():
    """setRating with 0 stars must produce 'Bewertung entfernt' label (not '0 Sterne vergeben')."""
    js = render_player_js()
    assert "Bewertung entfernt" in js


def test_rating_star_tooltip_hints_toggle():
    """The currently-set star should show a 'remove' hint in its tooltip."""
    js = render_player_js()
    assert "Bewertung entfernen" in js
    assert "nochmals klicken" in js


# ---------------------------------------------------------------------------
# Edit-modal rating stars
# ---------------------------------------------------------------------------


def test_edit_modal_rating_css_present():
    """CSS must include styles for rating stars inside the edit modal."""
    css = render_base_css()
    assert ".edit-modal-rating" in css
    assert ".edit-modal-rating-star" in css
    assert ".edit-modal-rating-star.active" in css


def test_edit_modal_rating_html_present():
    """Edit modal HTML must contain the rating container when metadata edit is enabled."""
    page = render_media_page(
        title="T",
        emoji="E",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/audio/tracks",
        item_noun="track",
        enable_metadata_edit=True,
    )
    assert 'id="edit-modal-rating"' in page
    assert 'id="edit-modal-rating-field"' in page


def test_edit_modal_rating_js_render_function():
    """JS must contain renderEditModalRating function."""
    js = render_player_js()
    assert "renderEditModalRating" in js
    assert "_editModalRating" in js


def test_edit_modal_rating_submit_sends_rating():
    """submitEditModal must include rating API call when rating changes."""
    js = render_player_js()
    assert "RATING_API_PATH" in js
    assert "ratingChanged" in js
    assert "Promise.all" in js


def test_audio_server_has_rating_endpoint():
    """The audio server must expose POST /api/audio/rating."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    # Valid call (non-existent path → 404 from resolve, not 405)
    resp = client.post("/api/audio/rating", json={"path": "no/such/file.mp3", "rating": 3.0})
    assert resp.status_code != 405  # endpoint exists

    # Missing path → 400
    resp = client.post("/api/audio/rating", json={"rating": 3.0})
    assert resp.status_code == 400

    # Out-of-range rating → 400
    resp = client.post("/api/audio/rating", json={"path": "x.mp3", "rating": 99})
    assert resp.status_code == 400


def test_audio_server_enables_rating_write():
    """The audio server's #ht-config must have enableRatingWrite: true."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableRatingWrite"] is True


def test_video_server_does_not_enable_rating_write():
    """The video server's #ht-config must have enableRatingWrite: false."""
    import json
    import re

    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    m = re.search(r'<script id="ht-config" type="application/json">(.*?)</script>', html, re.S)
    assert m
    assert json.loads(m.group(1))["enableRatingWrite"] is False


def test_rating_in_both_player_bar_styles():
    """Rating container must appear in both classic and waveform player bars."""
    for style in ("classic", "waveform"):
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/audio/tracks",
            item_noun="track",
            player_bar_style=style,
            enable_rating_write=True,
        )
        assert 'id="player-rating"' in page, f"Missing rating container in {style} player bar"


# ---------------------------------------------------------------------------
# Bug fix: player visibility must use player.currentSrc, not currentIndex < 0
# ---------------------------------------------------------------------------


def test_player_visibility_uses_currentSrc_not_currentIndex():
    """showFolderView must hide player only when player.currentSrc is falsy.

    Using currentIndex < 0 caused the player to disappear after navigating
    to the offline library (which resets currentIndex) and then going Home.
    """
    js = _js()
    # Must NOT use the old broken condition
    assert "if (currentIndex < 0) playerBar.classList.add('view-hidden')" not in js
    # Must use the correct currentSrc check
    assert "if (!player.currentSrc) playerBar.classList.add('view-hidden')" in js


def test_player_currentSrc_check_in_all_folder_functions():
    """All folder-view functions must use player.currentSrc to guard player visibility."""
    js = _js()
    # Count occurrences: showFolderView (2x), showLoadingState (1x), showCatalogLoadError (1x)
    count = js.count("if (!player.currentSrc) playerBar.classList.add('view-hidden')")
    assert count >= 4, f"Expected >=4 occurrences, got {count}"


# ---------------------------------------------------------------------------
# History / Audit button in header
# ---------------------------------------------------------------------------


def test_audit_button_in_header():
    """Header must contain a link to the /audit control panel."""
    page = _page()
    assert 'href="/audit"' in page


def test_audit_button_has_title():
    """Audit button must have a descriptive title attribute."""
    page = _page()
    assert "Änderungsverlauf" in page


def test_audit_button_present_on_both_servers():
    """Both audio and video pages must have the /audit link."""
    for media in ("audio", "video"):
        page = _page(media=media)
        assert 'href="/audit"' in page, f"Missing audit link on {media} page"


def test_svg_history_constant_defined():
    """SVG_HISTORY must be defined in server_utils."""
    from hometools.streaming.core.server_utils import SVG_HISTORY

    assert SVG_HISTORY
    assert "<svg" in SVG_HISTORY
    assert "circle" in SVG_HISTORY  # clock has a circle


# ---------------------------------------------------------------------------
# Genre filter chip tests
# ---------------------------------------------------------------------------


def test_genre_filter_chip_in_html():
    """The combined "Filtern" popover trigger (Bewertung+Favorit+Genre —
    see docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2)
    must be present in the rendered HTML."""
    from hometools.streaming.core.server_utils import render_media_page

    html = render_media_page(
        title="Test",
        emoji="\U0001f3b5",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
    )
    assert 'id="filter-combined"' in html


def test_genre_filter_js_variable():
    """The JS must declare filterGenre variable and persist in localStorage,
    and wire the combined filter-popover trigger."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "filterCombinedBtn" in js
    assert "filterGenre" in js
    assert "ht-filter-genre" in js


def test_genre_filter_apply_logic():
    """applyFilter must filter by genre when filterGenre is set."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "t.genre === filterGenre" in js


def test_combined_filter_popover_present():
    """Bewertung + Favorit + Genre must live in ONE combined "Filtern"
    popover instead of three separate chip buttons — see
    docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2.
    The old per-filter chip IDs (filter-rating/filter-fav/filter-genre)
    must be gone; "Ausgeblendet" stays its own toggle-slot chip."""
    from hometools.streaming.core.server_utils import render_media_page, render_player_js

    html = render_media_page(
        title="Test",
        emoji="\U0001f3b5",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
    )
    assert 'id="filter-combined"' in html
    assert 'id="filter-hidden"' in html
    assert 'id="filter-rating"' not in html
    assert 'id="filter-fav"' not in html
    assert 'id="filter-genre"' not in html

    js = render_player_js()
    assert "function _toggleFilterPopover(" in js
    assert "function _closeFilterPopover(" in js
    assert "ht-filter-popover" in js
    # Reset must clear all three quick-filters, not just one.
    reset_fn = js.split("function _wireFilterPopoverBody(", 1)[1]
    reset_body = reset_fn.split("#filter-popover-reset", 1)[1]
    assert "filterRating = 0" in reset_body
    assert "filterFav = false" in reset_body
    assert "filterGenre = ''" in reset_body


def test_genre_field_on_media_item():
    """MediaItem must have a genre field."""
    from hometools.streaming.core.models import MediaItem

    item = MediaItem(
        relative_path="a/b.mp3",
        title="Test",
        artist="Artist",
        stream_url="/stream",
        media_type="audio",
        genre="Rock",
    )
    assert item.genre == "Rock"
    d = item.to_dict()
    assert d["genre"] == "Rock"


def test_genre_field_defaults_empty():
    """MediaItem.genre must default to empty string."""
    from hometools.streaming.core.models import MediaItem

    item = MediaItem(
        relative_path="a/b.mp3",
        title="Test",
        artist="Artist",
        stream_url="/stream",
        media_type="audio",
    )
    assert item.genre == ""


# ---------------------------------------------------------------------------
# Swipe gesture tests
# ---------------------------------------------------------------------------


def test_swipe_gesture_code_present():
    """Touch swipe gesture handlers must be present in the generated JS."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "Touch swipe gestures" in js
    assert "touchstart" in js
    assert "touchend" in js
    assert "SWIPE_MIN_DIST" in js


def test_swipe_gesture_skips_range_inputs():
    """Swipe handler must not intercept touch events on range inputs (progress bar)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "type === 'range'" in js or "el.type === 'range'" in js


def test_swipe_no_next_prev_track():
    """Swipe must NOT trigger next/prev track — only buttons do that."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    # Extract only the swipe gesture IIFE section
    start = js.index("Touch swipe gestures")
    end = js.index("}());", start)
    swipe_section = js[start:end]
    assert "nextIndex()" not in swipe_section
    assert "prevIndex()" not in swipe_section


def test_swipe_right_calls_go_back():
    """Swipe right must call goBack (back navigation only)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "goBack()" in js


# ---------------------------------------------------------------------------
# Playlist sync interval injection
# ---------------------------------------------------------------------------


def test_sync_interval_reads_from_runtime_config():
    """_PLAYLIST_SYNC_INTERVAL is now sourced from CFG.playlistSyncIntervalMs
    (Vite/TS migration Phase 3) instead of a Python-interpolated literal —
    the actual numeric value is asserted at the #ht-config JSON level."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "_PLAYLIST_SYNC_INTERVAL = CFG.playlistSyncIntervalMs" in js


def test_sync_interval_custom_injected():
    """Custom playlist_sync_interval_ms reaches the #ht-config JSON blob."""
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="T",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        playlist_sync_interval_ms=60000,
    )
    cfg = _extract_ht_config(page)
    assert cfg["playlistSyncIntervalMs"] == 60000


# ---------------------------------------------------------------------------
# Optimistic UI helpers
# ---------------------------------------------------------------------------


def test_optimistic_snapshot_helpers_in_js():
    """Optimistic UI helpers _snapshotPlaylists / _restorePlaylists must be present."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "_snapshotPlaylists" in js
    assert "_restorePlaylists" in js


def test_optimistic_rollback_toast_in_delete():
    """deleteUserPlaylist must show a rollback toast on error."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "r\\u00fcckg\\u00e4ngig" in js or "rückg" in js


# ---------------------------------------------------------------------------
# MIN_RATING_THRESHOLD injection
# ---------------------------------------------------------------------------


def test_min_rating_threshold_reads_from_runtime_config():
    """MIN_RATING_THRESHOLD is now sourced from CFG.minRating (Phase 3)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    assert "MIN_RATING_THRESHOLD = CFG.minRating" in js


def test_min_rating_threshold_custom_injected():
    """Custom min_rating reaches the #ht-config JSON blob."""
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="T",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        min_rating=2,
    )
    cfg = _extract_ht_config(page)
    assert cfg["minRating"] == 2


def test_min_rating_filter_logic_in_apply_filter():
    """applyFilter must use _effectiveThreshold (derived from MIN_RATING_THRESHOLD) to filter tracks.

    Semantics (2026-05): filter is opt-in via showHidden toggle, uses < comparison (exclusive).
    Tracks with rating >= threshold are always kept.  Unrated (0) are always kept.
    Example: threshold=2 → hide only 1★, keep 2★ 3★ 4★ 5★ and unrated.
             threshold=3 → hide 1★ 2★, keep 3★ 4★ 5★ and unrated.
    """
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js()
    # Must contain the filter that hides rated-but-low tracks while keeping unrated
    assert "MIN_RATING_THRESHOLD" in js
    # Semantics: exclusive < comparison, so threshold-star songs are NOT hidden
    assert "r === 0 || r >= _effectiveThreshold" in js


# ---------------------------------------------------------------------------
# Crossfade
# ---------------------------------------------------------------------------


def test_crossfade_duration_reads_from_runtime_config():
    """CROSSFADE_DURATION is now sourced from CFG.crossfadeDuration (Phase 3)."""
    js = render_player_js()
    assert "CROSSFADE_DURATION = CFG.crossfadeDuration" in js


def test_crossfade_duration_custom_injected():
    """Custom crossfade_duration reaches the #ht-config JSON blob."""
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="T",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        crossfade_duration=5,
    )
    cfg = _extract_ht_config(page)
    assert cfg["crossfadeDuration"] == 5


def test_crossfade_js_has_xfade_functions():
    """Crossfade JS must contain the core functions."""
    js = render_player_js()
    assert "_startCrossfade" in js
    assert "_finishCrossfade" in js
    assert "_xfadeCleanup" in js
    assert "_xfadeAudio" in js


def test_crossfade_trigger_in_timeupdate():
    """timeupdate handler must check CROSSFADE_DURATION and trigger crossfade."""
    js = render_player_js()
    assert "CROSSFADE_DURATION > 0" in js
    assert "_startCrossfade()" in js


def test_crossfade_config_function():
    """get_crossfade_duration must return 0 by default."""
    from hometools.config import get_crossfade_duration

    # Should return 0 by default (unless env var is set)
    val = get_crossfade_duration()
    assert isinstance(val, int)
    assert 0 <= val <= 12


def test_crossfade_config_clamped(monkeypatch):
    """get_crossfade_duration must clamp to 0-12 range."""
    from hometools.config import get_crossfade_duration

    monkeypatch.setenv("HOMETOOLS_CROSSFADE_DURATION", "99")
    assert get_crossfade_duration() == 12

    monkeypatch.setenv("HOMETOOLS_CROSSFADE_DURATION", "-5")
    assert get_crossfade_duration() == 0


def test_audio_server_passes_crossfade_duration():
    """Audio server HTML must include CROSSFADE_DURATION."""
    from hometools.streaming.audio.server import render_audio_index_html

    html = render_audio_index_html([])
    assert "CROSSFADE_DURATION" in html


# ---------------------------------------------------------------------------
# Global Search
# ---------------------------------------------------------------------------


def test_global_search_function_exists():
    """The JS must contain the globalSearch function."""
    js = render_player_js()
    assert "function globalSearch" in js
    assert "function initGlobalSearch" in js
    assert "function exitGlobalSearch" in js
    assert "function navigateToSearchResult" in js
    assert "function renderSearchResults" in js


def test_global_search_respects_min_rating():
    """globalSearch must respect the effective hidden threshold (_effectiveThreshold).

    Only filters when !showHidden (opt-in), using < comparison (exclusive).
    """
    js = render_player_js()
    assert "MIN_RATING_THRESHOLD" in js
    # The globalSearch function filters via _effectiveThreshold with < semantics
    assert "r < _effectiveThreshold" in js


def test_folder_filter_bar_in_html():
    """The HTML must contain the folder-filter-bar element."""
    from hometools.streaming.core.server_utils import render_media_page

    html = render_media_page(
        title="T",
        emoji="X",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/t",
        item_noun="track",
    )
    assert 'id="folder-filter-bar"' in html


def test_global_search_shows_folder_path():
    """Search results must show the folder path for context."""
    js = render_player_js()
    assert "search-result-folder" in js


def test_global_search_debounce():
    """Global search input should be debounced."""
    js = render_player_js()
    assert "_globalSearchDebounce" in js


# ---------------------------------------------------------------------------
# Header global search consistency across all track-list entry points
# (docs/IMPLEMENTATION_PLAN.md -> "UI-Template-Vereinheitlichung" Phase 2:
# the header-level #global-search-input must behave identically regardless
# of which function opened the track list — folder-leaf playlist, user
# playlist, smart playlist or the duplicates view all reuse the same rule).
# ---------------------------------------------------------------------------


def test_enter_track_list_view_hides_global_search():
    """_enterTrackListView() — the shared toolbar/header entry point every
    track-list view (folder-leaf playlist, user/smart playlist, favorites,
    duplicates) delegates to — must hide the header global search bar."""
    js = render_player_js()
    assert "function _enterTrackListView(opts)" in js
    fn = js.split("function _enterTrackListView(opts)", 1)[1]
    body = fn.split("function showPlaylist(", 1)[0]
    assert "_hideGlobalSearch();" in body


def test_show_playlist_uses_shared_track_list_entry_point():
    """showPlaylist() (leaf-folder playlist) must delegate its header/toolbar
    setup to _enterTrackListView() instead of re-inlining the class toggles
    — previously it hand-rolled its own subset, which is exactly what let
    the header drift out of sync between folder browsing and playlist
    views (missing global-search-hide, stale fb-scroll-hidden, ...)."""
    js = render_player_js()
    playlist_fn = js.split("function showPlaylist(", 1)[1]
    body = playlist_fn.split("function _restoreLastEpisode", 1)[0]
    assert "_enterTrackListView({" in body
    assert "folderGrid.classList.add('view-hidden')" not in body


def test_folder_grid_view_shows_global_search_only_when_catalog_loaded():
    """The folder-grid branches of showFolderView() (empty library + normal)
    must (re)show the global search bar when the catalog is loaded, and
    hide it otherwise — this must NOT run for the leaf-folder branch,
    which now delegates hiding to _enterTrackListView() via showPlaylist()."""
    js = render_player_js()
    folder_view_fn = js.split("function showFolderView(", 1)[1]
    body = folder_view_fn.split("function showPlaylist(", 1)[0]
    assert body.count("if (allItems.length > 0) initGlobalSearch(); else _hideGlobalSearch();") == 2


def test_smart_and_user_playlist_view_uses_shared_track_list_entry_point():
    """showUserPlaylistView() (favorites/all-titles/custom/smart playlists —
    same code path for every playlist type) must delegate to
    _enterTrackListView() for all three branches, matching
    showPlaylist()/playDuplicates()."""
    js = render_player_js()
    assert "function showUserPlaylistView(plId)" in js
    view_fn = js.split("function showUserPlaylistView(plId)", 1)[1]
    body = view_fn.split("function playUserPlaylist(", 1)[0]
    assert body.count("_enterTrackListView({") == 3  # __alltitles__, __favorites__, custom/smart


def test_play_duplicates_uses_shared_track_list_entry_point():
    """playDuplicates() must delegate to _enterTrackListView() too, with a
    collapsed filter bar (dupe list keeps its own compact layout)."""
    js = render_player_js()
    assert "function playDuplicates()" in js
    fn = js.split("function playDuplicates()", 1)[1]
    body = fn.split("function _deleteDuplicateFile(", 1)[0]
    assert "_enterTrackListView({" in body
    assert "collapseFilterBar: true" in body


def test_enter_track_list_view_refreshes_view_toggle():
    """_enterTrackListView() must call applyViewMode() so the header's
    view-toggle button (list/table icon) is refreshed for every track-list
    view — previously only showFolderView() did this, so the button kept
    showing whatever the folder-grid had set when entering a playlist,
    smart playlist or the duplicates view directly."""
    js = render_player_js()
    fn = js.split("function _enterTrackListView(opts)", 1)[1]
    body = fn.split("function showPlaylist(", 1)[0]
    assert "applyViewMode();" in body


# ---------------------------------------------------------------------------
# Language tags & cleanFolderName
# ---------------------------------------------------------------------------


def test_js_has_clean_folder_name():
    """cleanFolderName is ported to webui/src/breadcrumb.ts, bridged onto
    window (see main.ts) — the legacy Python-generated JS calls the bare
    identifier, it no longer defines the function itself."""
    ts = _webui_src("breadcrumb.ts")
    assert "export function cleanFolderName" in ts
    js = _js()
    assert "function cleanFolderName" not in js
    assert "window.cleanFolderName = cleanFolderName" in _webui_src("main.ts")


def test_js_has_lang_badges_html():
    """JS must contain the langBadgesHtml function."""
    js = _js()
    assert "function langBadgesHtml" in js


def test_js_has_lang_to_flag_map():
    """JS must contain the LANG_TO_FLAG mapping with at least de and en."""
    js = _js()
    assert "LANG_TO_FLAG" in js
    assert "'de'" in js
    assert "'en'" in js


def test_js_has_detect_lang_from_name():
    """JS must contain the detectLangFromName helper."""
    js = _js()
    assert "function detectLangFromName" in js


def test_js_clean_folder_name_strips_hash():
    """cleanFolderName in contentsAt should strip # prefix from displayName."""
    js = _js()
    # The cleanFolderName function should strip # at start
    assert "charAt(0) === '#'" in js


def test_js_clean_folder_name_strips_lang_tag():
    """cleanFolderName should strip language tags via LANG_TAG_RE (ported
    to webui/src/breadcrumb.ts, no leading underscore there — see that
    module's naming)."""
    ts = _webui_src("breadcrumb.ts")
    assert "LANG_TAG_RE" in ts


def test_js_folder_card_renders_lang_badges():
    """Folder card rendering must include langBadgesHtml call."""
    js = _js()
    assert "langBadgesHtml(f.languages)" in js


def test_js_contents_at_aggregates_languages():
    """contentsAt must collect language codes into folderLangs."""
    js = _js()
    assert "folderLangs" in js


def test_js_leaf_name_uses_clean_folder_name():
    """leafName is ported to webui/src/pathUtils.ts, bridged onto window
    (see main.ts) — it must use cleanFolderName for display, and the
    legacy Python-generated JS no longer defines the function itself."""
    ts = _webui_src("pathUtils.ts")
    assert "export function leafName" in ts
    assert "cleanFolderName(raw)" in ts
    js = _js()
    assert "function leafName" not in js
    assert "window.leafName = leafName" in _webui_src("main.ts")


def test_js_parent_path_ported_to_ts():
    """parentPath (fully pure — no other identifier references) is ported
    to webui/src/pathUtils.ts alongside leafName."""
    ts = _webui_src("pathUtils.ts")
    assert "export function parentPath" in ts
    js = _js()
    assert "function parentPath" not in js
    assert "window.parentPath = parentPath" in _webui_src("main.ts")


def test_core_js_bridges_original_title_onto_window():
    """originalTitle is a `var` scoped to the legacy IIFE, not a real
    global — _core.py must bridge it onto window so the ported
    leafName() (a separate .ts closure) can read it."""
    js = _js()
    assert "window.originalTitle = originalTitle;" in js


def test_js_breadcrumb_uses_clean_folder_name():
    """renderBreadcrumb must delegate to the ported renderBreadcrumbHtml
    (webui/src/breadcrumb.ts) instead of re-inlining segment/label markup
    building — that ported function uses cleanFolderName for folder
    labels internally."""
    js = _js()
    assert "renderBreadcrumbHtml(currentPath, escHtml)" in js
    ts = _webui_src("breadcrumb.ts")
    assert "cleanFolderName(part)" in ts


def test_css_has_lang_badge():
    """CSS must include .lang-badge styling."""
    css = render_base_css()
    assert ".lang-badge" in css


# ---------------------------------------------------------------------------
# Composite Flags & Subtitle Language (Phase 1b)
# ---------------------------------------------------------------------------


def test_js_has_detect_sub_lang_from_name():
    """JS must contain the detectSubLangFromName function."""
    js = _js()
    assert "function detectSubLangFromName" in js


def test_js_has_composite_flag_html():
    """JS must contain the compositeFlagHtml function."""
    js = _js()
    assert "function compositeFlagHtml" in js


def test_js_composite_flag_html_uses_composite_flag_class():
    """compositeFlagHtml must produce HTML with composite-flag class."""
    js = _js()
    assert "composite-flag" in js
    assert "composite-flag-sub" in js


def test_js_has_default_lang_variable():
    """JS must contain the DEFAULT_LANG variable."""
    js = _js()
    assert "DEFAULT_LANG" in js


def test_js_default_lang_injectable():
    """DEFAULT_LANG is now sourced from CFG.defaultLanguage (Phase 3);
    custom default_language reaches the #ht-config JSON blob."""
    from hometools.streaming.core.server_utils import render_media_page

    js = render_player_js()
    assert "DEFAULT_LANG = CFG.defaultLanguage" in js
    page = render_media_page(
        title="T",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        default_language="en",
    )
    cfg = _extract_ht_config(page)
    assert cfg["defaultLanguage"] == "en"


def test_js_default_lang_defaults_to_de():
    """default_language must default to 'de' in the #ht-config JSON blob."""
    from hometools.streaming.core.server_utils import render_media_page

    page = render_media_page(
        title="T",
        emoji="",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
    )
    cfg = _extract_ht_config(page)
    assert cfg["defaultLanguage"] == "de"


def test_css_has_composite_flag():
    """CSS must include .composite-flag styling."""
    css = render_base_css()
    assert ".composite-flag" in css
    assert ".composite-flag-sub" in css


def test_css_has_lang_select_btn():
    """CSS must include .lang-select-btn styling."""
    css = render_base_css()
    assert ".lang-select-btn" in css
    assert ".lang-select-btn:hover" in css


def test_js_contents_at_aggregates_sub_langs():
    """contentsAt must collect subtitle language codes into folderSubLangs."""
    js = _js()
    assert "folderSubLangs" in js or "subLang" in js


def test_js_folder_card_renders_lang_select_btn():
    """Folder card rendering must include lang-select-btn for multi-lang folders."""
    js = _js()
    assert "lang-select-btn" in js


def test_js_lang_select_btn_click_navigates():
    """Clicking a lang-select-btn must navigate into the variant."""
    js = _js()
    assert "data-variant-name" in js
    assert "navigateInto" in js


def test_js_card_click_uses_default_lang():
    """Folder card click must use DEFAULT_LANG to pick variant."""
    js = _js()
    assert "DEFAULT_LANG" in js


def test_js_detect_sub_lang_maps():
    """detectSubLangFromName must contain detection patterns for common subtitle hints."""
    js = _js()
    assert "gersub" in js or "ger" in js


def test_config_get_default_language():
    """get_default_language must return a valid language code."""
    from hometools.config import get_default_language

    lang = get_default_language()
    assert isinstance(lang, str)
    assert len(lang) == 2


def test_config_get_default_language_from_env(monkeypatch):
    """get_default_language must respect HOMETOOLS_DEFAULT_LANGUAGE env var."""
    from hometools.config import get_default_language

    monkeypatch.setenv("HOMETOOLS_DEFAULT_LANGUAGE", "en")
    assert get_default_language() == "en"

    monkeypatch.setenv("HOMETOOLS_DEFAULT_LANGUAGE", "  FR  ")
    assert get_default_language() == "fr"


def test_config_get_default_language_empty_fallback(monkeypatch):
    """get_default_language must fall back to 'de' for empty values."""
    from hometools.config import get_default_language

    monkeypatch.setenv("HOMETOOLS_DEFAULT_LANGUAGE", "")
    assert get_default_language() == "de"

    monkeypatch.setenv("HOMETOOLS_DEFAULT_LANGUAGE", "   ")
    assert get_default_language() == "de"


def test_video_server_passes_default_language():
    """Video server HTML must include DEFAULT_LANG variable."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert "DEFAULT_LANG" in html


# ---------------------------------------------------------------------------
# Duplicate detection: _dupeKey / _normalizeStem
# ---------------------------------------------------------------------------


def _normalize_stem(s: str) -> str:
    """Python port of the JS _normalizeStem function for unit-testing."""
    if not s:
        return ""
    s = s.replace("&amp;", "&")
    s = _re.sub(r"\(\d{1,3}kbit_[A-Za-z]+\)", "", s, flags=_re.IGNORECASE)
    # All (Official ...) blocks
    s = _re.sub(r"\(Official[^)]*\)", "", s, flags=_re.IGNORECASE)
    # Common platform/promo tags
    s = _re.sub(
        r"\((?:Audio|Video|Music\s+Video|Lyric\s+Video|Lyrics|Lyric|Visualizer|Topic|HD|HQ)\)",
        "",
        s,
        flags=_re.IGNORECASE,
    )
    s = _re.sub(r"\(\w*\.[a-zA-Z]{2,5}\)", "", s, flags=_re.IGNORECASE)
    s = _re.sub(r"\w*\.(?:com|net|org|co\.uk|de|vu|ru|pl)", "", s, flags=_re.IGNORECASE)
    # Normalize feat/prod/vs shortcuts (simplified — no lookbehind needed for test)
    s = _re.sub(r"(?<!\w)(?:featuring|feat\.|feat)(?!\w)", "feat. ", s, flags=_re.IGNORECASE)
    s = _re.sub(r"\(\s*\)|\[\s*\]", "", s)
    s = _re.sub(r" {2,}", " ", s)
    return s.strip().lower()


def _dupe_key(title: str, artist: str = "") -> str:
    """Python port of the JS _dupeKey function for unit-testing."""
    raw = title or ""
    cleaned = _normalize_stem(raw)
    # Strip download-duplicate suffixes
    cleaned = _re.sub(r"[\s_-]*\(?(?:copy|kopie)\)?\s*$", "", cleaned, flags=_re.IGNORECASE)
    cleaned = _re.sub(r"[\s_-]+\d{1,2}\s*$", "", cleaned)
    cleaned = _re.sub(r"\s*\(\d{1,2}\)\s*$", "", cleaned)
    cleaned = _re.sub(r"\s*\[\d{1,2}\]\s*$", "", cleaned)
    # Split on common separators
    parts = _re.split(r"feat\.|prod\.|vs\.|\(|\[| - |, | & |\)|\]", cleaned, flags=_re.IGNORECASE)
    # Strip ONLY purely promotional/label markers (NOT version differentiators)
    parts = [_re.sub(r"\bofficial\b|\bexplicit\b|\bclean\b", "", p, flags=_re.IGNORECASE) for p in parts]
    # Strip non-word chars
    parts = [_re.sub(r"[^a-z0-9]", "", p, flags=_re.IGNORECASE) for p in parts]
    # Filter short remnants
    parts = [p for p in parts if len(p) > 2]
    # Deduplicate + sort for stable key
    seen: set[str] = set()
    unique = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    unique.sort()
    title_key = "|".join(unique)
    artist_raw = _re.sub(r"[^a-z0-9]", "", artist.lower(), flags=_re.IGNORECASE)
    if len(artist_raw) > 2:
        title_key = artist_raw + "::" + title_key
    return title_key


class TestDupeKeyVersionsAreDifferent:
    """Version/mix descriptors must produce different keys → no false-positive duplicates."""

    BASE_ARTIST = "$ONO$ CLIQ, Drunken Masters, Jonko2x, Radrik Gee"

    def test_original_vs_remix_not_duplicate(self):
        key1 = _dupe_key("Bauchnabelpiercing", self.BASE_ARTIST)
        key2 = _dupe_key("Bauchnabelpiercing - Remix", self.BASE_ARTIST)
        assert key1 != key2, f"Remix must not equal original: {key1!r} == {key2!r}"

    def test_title_with_remix_suffix_has_remix_in_key(self):
        key = _dupe_key("Song - Remix")
        assert "remix" in key, f"'remix' expected in key, got: {key!r}"

    def test_extended_mix_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Extended Mix)")
        assert key1 != key2

    def test_live_version_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Live)")
        assert key1 != key2

    def test_acoustic_version_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Acoustic)")
        assert key1 != key2

    def test_instrumental_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Instrumental)")
        assert key1 != key2

    def test_radio_edit_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Radio Edit)")
        assert key1 != key2

    def test_remaster_not_duplicate_of_original(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (2020 Remaster)")
        assert key1 != key2

    def test_different_remix_versions_not_duplicate(self):
        key1 = _dupe_key("Song Title - Remix")
        key2 = _dupe_key("Song Title - Extended Remix")
        assert key1 != key2


class TestDupeKeyTrueDuplicatesDetected:
    """Genuine download duplicates must share the same key."""

    def test_copy_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title - Copy")
        assert key1 == key2, f"'- Copy' suffix must collapse to same key: {key1!r} vs {key2!r}"

    def test_numbered_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title_2")
        assert key1 == key2

    def test_parenthesised_number_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (2)")
        assert key1 == key2

    def test_official_video_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Official Video)")
        assert key1 == key2, f"(Official Video) must not change key: {key1!r} vs {key2!r}"

    def test_official_audio_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Official Audio)")
        assert key1 == key2, f"(Official Audio) must not change key: {key1!r} vs {key2!r}"

    def test_official_music_video_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (Official Music Video)")
        assert key1 == key2

    def test_hd_suffix_is_duplicate(self):
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (HD)")
        assert key1 == key2

    def test_different_artists_not_duplicate(self):
        key1 = _dupe_key("Nur Geträumt", "Blümchen")
        key2 = _dupe_key("Nur Geträumt", "Nena")
        assert key1 != key2

    def test_domain_in_filename_is_stripped(self):
        # Simple (domain.com) parenthesised form is handled by _normalizeStem
        key1 = _dupe_key("Song Title")
        key2 = _dupe_key("Song Title (example.com)")
        assert key1 == key2


class TestDupeKeyGeneratedJsIntegrity:
    """Sanity-check the normalizeStem/dupeKey regexes.

    `_normalizeStem`/`_dupeKey` were ported to `webui/src/dupeUtils.ts`
    (Vite/TS migration Phase 5 opportunistic-port slice — see
    docs/IMPLEMENTATION_PLAN.md); they no longer appear in
    `render_player_js()`'s output, so these checks now read the TS source
    directly (same pattern as any other ported-module assertion once the
    Python generator function is deleted)."""

    @staticmethod
    def _dupe_utils_ts() -> str:
        path = Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src" / "dupeUtils.ts"
        return path.read_text(encoding="utf-8")

    def test_js_does_not_strip_remix_aggressively(self):
        """The old aggressive strip list must be gone."""
        ts = self._dupe_utils_ts()
        assert "remix|mix|version" not in ts and "extended|radio|vocal|edit|remix" not in ts, (
            "Old aggressive version-strip regex still present in dupeUtils.ts"
        )

    def test_js_strips_only_promo_markers(self):
        """New strip regex must target only official/explicit/clean."""
        ts = self._dupe_utils_ts()
        assert r"\bofficial\b|\bexplicit\b|\bclean\b" in ts

    def test_js_normalizestem_has_broad_official_pattern(self):
        """normalizeStem must strip ALL (Official ...) blocks, not only (Official*Video)."""
        ts = self._dupe_utils_ts()
        assert r"\(Official[^)]*\)" in ts

    def test_js_normalizestem_strips_audio_video_tags(self):
        """normalizeStem must strip standalone (Audio) and (Video) platform tags."""
        ts = self._dupe_utils_ts()
        assert "Audio|Video|Music" in ts  # part of the new promo-tag pattern


class TestPlayerBugfixes2026_06:
    """Mobile seek, spurious-ended guard, progress flush and PiP-on-mobile fixes."""

    def test_js_has_pointer_based_track_seek(self):
        """Seeking must work via tap/drag on the whole track (touch fix)."""
        js = render_player_js()
        assert "initTrackSeek" in js
        assert "setPointerCapture" in js
        assert "pointerdown" in js

    def test_css_progress_track_disables_touch_scroll(self):
        """progress-track needs touch-action:none so drag isn't stolen by scroll."""
        css = render_base_css()
        assert "touch-action: none" in css

    def test_js_ended_guard_against_spurious_end(self):
        """The ended handler must only advance when playback actually reached the end."""
        js = render_player_js()
        assert "reachedEnd" in js

    def test_js_progress_uses_sendbeacon(self):
        """Progress save must use sendBeacon so it survives backgrounding/unload."""
        js = render_player_js()
        assert "sendBeacon" in js
        assert "pagehide" in js

    def test_js_flushes_progress_before_switching_track(self):
        """playItem must flush the outgoing track's progress before switching."""
        js = render_player_js()
        assert "flush the outgoing track" in js

    def test_js_hides_pip_button_on_touch_devices(self):
        """The custom PiP button must be suppressed on mobile/touch devices."""
        js = render_player_js()
        assert "isTouchDevice" in js
        assert "(pointer: coarse)" in js

    def test_js_missing_episode_placeholder_label(self):
        """Missing-episode placeholders must show a clear 'Folge fehlt' label."""
        js = render_player_js()
        assert "Folge fehlt" in js


# ---------------------------------------------------------------------------
# Catalog cache (localStorage stale-while-revalidate) — regression tests
# Bug: every page reload fetched the full catalog from the server because
#      loadInitialCatalog() always used cache:'no-store' and INITIAL was empty.
#      These tests lock the stale-while-revalidate implementation so it never
#      regresses silently.
# ---------------------------------------------------------------------------


class TestCatalogLocalStorageCache:
    """The JS must persist and restore the catalog from localStorage to avoid
    a full-index fetch on every page reload (stale-while-revalidate pattern)."""

    def _js(self):
        return render_player_js()

    # ── Helper functions must be present ─────────────────────────────────────

    def test_save_catalog_cache_function_defined(self):
        assert "function _saveCatalogCache(" in self._js()

    def test_load_catalog_cache_function_defined(self):
        assert "function _loadCatalogCache(" in self._js()

    def test_clear_catalog_cache_function_defined(self):
        assert "function _clearCatalogCache(" in self._js()

    def test_catalog_cache_key_uses_api_path(self):
        """Key must be derived from API_PATH so audio and video never share a slot."""
        js = self._js()
        assert "_CATALOG_CACHE_KEY" in js
        assert "API_PATH" in js

    def test_catalog_max_age_defined(self):
        assert "_CATALOG_MAX_AGE_MS" in self._js()

    # ── loadInitialCatalog must use the cache ─────────────────────────────────

    def test_load_initial_catalog_checks_cache_before_fetch(self):
        """loadInitialCatalog must call _loadCatalogCache() before going to the network."""
        js = self._js()
        load_fn_start = js.index("function loadInitialCatalog(")
        # _loadCatalogCache must appear inside loadInitialCatalog, before the fetch call
        load_cache_pos = js.index("_loadCatalogCache()", load_fn_start)
        fetch_pos = js.index("fetch(API_PATH", load_fn_start)
        assert load_cache_pos < fetch_pos, "_loadCatalogCache() must be called BEFORE the network fetch inside loadInitialCatalog"

    def test_load_initial_catalog_saves_after_fetch(self):
        """After a successful network fetch, loadInitialCatalog must persist the result."""
        js = self._js()
        load_fn_start = js.index("function loadInitialCatalog(")
        # Find next function definition to bound the search
        next_fn = js.index("\n  function ", load_fn_start + 1)
        fn_body = js[load_fn_start:next_fn]
        assert "_saveCatalogCache(allItems)" in fn_body, "_saveCatalogCache must be called inside loadInitialCatalog after the fetch"

    def test_load_initial_catalog_shows_cached_items_without_loading_state(self):
        """When cache is present, loadInitialCatalog must call showFolderView() immediately."""
        js = self._js()
        load_fn_start = js.index("function loadInitialCatalog(")
        next_fn = js.index("\n  function ", load_fn_start + 1)
        fn_body = js[load_fn_start:next_fn]
        # showFolderView() must appear before the initialCatalogRetryCount increment
        # (i.e. in the cache-hit branch, not the loading branch)
        show_pos = fn_body.index("showFolderView()")
        retry_pos = fn_body.index("initialCatalogRetryCount")
        assert show_pos < retry_pos, "showFolderView() must be called in the cache-hit branch, before the retry counter"

    # ── Cache must be updated on background/manual refresh ───────────────────

    def test_background_refresh_saves_catalog(self):
        """scheduleBackgroundRefresh must persist the updated catalog."""
        js = self._js()
        bg_fn_start = js.index("function scheduleBackgroundRefresh(")
        next_fn = js.index("\n  function ", bg_fn_start + 1)
        fn_body = js[bg_fn_start:next_fn]
        assert "_saveCatalogCache(allItems)" in fn_body, "_saveCatalogCache must be called inside scheduleBackgroundRefresh"

    def test_refresh_poll_saves_catalog(self):
        """_refreshPoll (manual refresh polling) must persist the updated catalog."""
        js = self._js()
        poll_fn_start = js.index("function _refreshPoll(")
        next_fn = js.index("\n  function ", poll_fn_start + 1)
        fn_body = js[poll_fn_start:next_fn]
        assert "_saveCatalogCache(allItems)" in fn_body, "_saveCatalogCache must be called inside _refreshPoll"

    # ── Explicit refresh must clear the cache ─────────────────────────────────

    def test_refresh_catalog_clears_cache(self):
        """User-triggered refreshCatalog must clear the localStorage cache
        so the next load fetches fresh data and doesn't serve stale items."""
        js = self._js()
        refresh_fn_start = js.index("function refreshCatalog(")
        next_fn = js.index("\n  function ", refresh_fn_start + 1)
        fn_body = js[refresh_fn_start:next_fn]
        assert "_clearCatalogCache()" in fn_body, "_clearCatalogCache must be called inside refreshCatalog"

    # ── Load function handles offline gracefully ──────────────────────────────

    def test_cache_hit_handles_offline_server_gracefully(self):
        """When cache is used and the background fetch fails (server offline),
        the cached data must remain visible — no crash or empty state."""
        js = self._js()
        load_fn_start = js.index("function loadInitialCatalog(")
        next_fn = js.index("\n  function ", load_fn_start + 1)
        fn_body = js[load_fn_start:next_fn]
        # Must have a .catch() handler in the background fetch branch
        assert ".catch(function()" in fn_body, "The background refresh fetch inside loadInitialCatalog must have a .catch() handler"

    # ── Parity: both audio and video API paths produce distinct keys ──────────

    def test_cache_key_differs_between_audio_and_video(self):
        """The cache key must be unique per server so that the audio catalog
        never overwrites the video catalog or vice versa.

        _CATALOG_CACHE_KEY is derived at runtime from API_PATH (= CFG.apiPath,
        Vite/TS migration Phase 3) — the JS expression itself is now
        identical for every server, so uniqueness is verified end-to-end via
        the actual #ht-config apiPath values of the two live servers.
        """
        js = render_player_js()
        assert "_CATALOG_CACHE_KEY = 'ht-catalog-' + API_PATH.replace" in js

        audio_page = render_media_page(title="T", emoji="", items_json="[]", media_element_tag="audio", api_path="/api/audio/tracks")
        video_page = render_media_page(title="T", emoji="", items_json="[]", media_element_tag="video", api_path="/api/video/items")
        audio_cfg = _extract_ht_config(audio_page)
        video_cfg = _extract_ht_config(video_page)
        assert audio_cfg["apiPath"] != video_cfg["apiPath"]


# ---------------------------------------------------------------------------
# Track detail/table view (audio only): hover-play, table columns, inline edit
# ---------------------------------------------------------------------------


class TestTrackDetailTableView:
    """Audio-only "table" view toggled from the view-toggle button: shows
    title/artist/duration/genre/rating as columns and allows inline editing
    of title/artist while a tool is active."""

    def test_table_view_toggle_present_in_audio_js(self):
        js = render_player_js()
        assert "_toggleTrackViewMode" in js
        assert "trackViewMode" in js
        assert "IC_TABLE" in js

    def test_table_view_locked_out_for_video(self):
        js = render_player_js()
        # Toggling is a no-op for video (detail/table view is audio-only)
        assert "detail/table view is audio-only" in js

    def test_track_row_has_duration_and_genre_cells(self):
        js = render_player_js()
        assert "track-duration-cell" in js
        assert "track-genre-cell" in js

    def test_table_header_columns(self):
        js = render_player_js()
        assert "track-table-header" in js
        assert "Interpret" in js
        assert "Dauer" in js
        assert "Genre" in js

    def test_inline_edit_save_function_present(self):
        js = render_player_js()
        assert "_saveInlineTableEdit" in js
        assert "contenteditable" in js

    def test_css_defines_table_mode_grid(self):
        css = render_base_css()
        assert ".track-list.table-mode .track-item" in css
        assert ".track-table-header" in css

    def test_hover_play_button_on_track_thumbnail(self):
        js = render_player_js()
        assert "track-play-btn" in js

    def test_folder_hover_play_button_moved_over_cover(self):
        css = render_base_css()
        assert ".folder-play-btn" in css
        # Positioned over the left side of the cover, not bottom-right anymore
        assert "left: 0.6rem" in css


class TestHtConfigJson:
    """``#ht-config`` — Vite/TS migration Phase 2 (additive JSON blob).

    Not yet consumed by ``render_player_js()`` — the flat ``SHUFFLE_ENABLED``
    etc. vars keep working unchanged (see other tests in this file). This
    only locks the parallel JSON contract so future TS modules can rely on
    it (see streaming/core/webui/src/main.ts:PlayerConfig).
    """

    def _config(self, page):
        return _extract_ht_config(page)

    def test_ht_config_present_and_valid_json(self):
        page = _page()
        cfg = self._config(page)
        assert cfg["apiPath"] == "/api/test"
        assert cfg["itemNoun"] == "track"

    def test_ht_config_reflects_feature_flags(self):
        page = render_media_page(
            title="Test",
            emoji="\U0001f3b5",
            items_json="[]",
            media_element_tag="audio",
            api_path="/api/audio/tracks",
            item_noun="track",
            enable_shuffle=True,
            enable_repeat=True,
            min_rating=3,
            crossfade_duration=2,
        )
        cfg = self._config(page)
        assert cfg["enableShuffle"] is True
        assert cfg["enableRepeat"] is True
        assert cfg["minRating"] == 3
        assert cfg["crossfadeDuration"] == 2
        assert cfg["fileEmoji"] == "\U0001f3b5"

    def test_ht_config_language_groups_parsed(self):
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            item_noun="video",
            language_groups_json='{"show": ["de", "en"]}',
        )
        cfg = self._config(page)
        assert cfg["languageGroups"] == {"show": ["de", "en"]}

    def test_ht_config_survives_malformed_language_groups(self):
        """Malformed language_groups_json must not crash page rendering."""
        page = render_media_page(
            title="Test",
            emoji="",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            item_noun="video",
            language_groups_json="not-json",
        )
        cfg = self._config(page)
        assert cfg["languageGroups"] == {}
