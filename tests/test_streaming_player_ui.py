"""Tests for the configurable player bar (classic and waveform modes)."""

from hometools.streaming.core.server_utils import render_base_css, render_media_page, render_player_js

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page(media="audio", style="classic"):
    return render_media_page(
        title="Test",
        emoji="🎵" if media == "audio" else "🎬",
        items_json="[]",
        media_element_tag=media,
        api_path="/api/test",
        item_noun="track" if media == "audio" else "video",
        player_bar_style=style,
    )


def _js(style="classic"):
    return render_player_js(api_path="/api/test", item_noun="track", player_bar_style=style)


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
    assert 'id="waveform-canvas"' not in page
    assert 'id="progress-track"' not in page


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
    assert "waveformData" not in js
    assert "decodeAudioData" not in js


def test_classic_js_has_no_thumb_video():
    js = _js(style="classic")
    assert "thumbVideo" not in js
    assert "mousemove" not in js


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
    assert "thumbVideo" in js
    assert "mousemove" in js
    assert "mouseleave" in js
    assert "drawImage" in js


def test_waveform_js_has_video_mode_class():
    js = _js(style="waveform")
    assert "video-mode" in js


def test_waveform_js_calls_generate_on_play():
    js = _js(style="waveform")
    assert "generateWaveform(playback.url)" in js


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


def test_video_has_controls_attribute():
    """Video element must have native controls for fullscreen button."""
    page = _page(media="video", style="classic")
    assert '<video id="player" preload="auto" playsinline controls autopictureinpicture>' in page


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
