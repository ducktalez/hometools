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
    assert "waveformData" not in js
    assert "decodeAudioData" not in js


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
        emoji="🎵",
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


def test_shuffle_js_enabled_flag_true():
    """SHUFFLE_ENABLED must be true when enable_shuffle=True."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
    assert "SHUFFLE_ENABLED = true" in js


def test_shuffle_js_enabled_flag_false_by_default():
    """SHUFFLE_ENABLED must be false when enable_shuffle=False (default)."""
    js = _js()
    assert "SHUFFLE_ENABLED = false" in js


def test_shuffle_js_has_core_functions():
    """Shuffle logic functions must be present when enabled."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
    assert "fisherYates" in js
    assert "buildWeightedQueue" in js
    assert "buildNormalQueue" in js
    assert "rebuildShuffleQueue" in js
    assert "cycleShuffle" in js
    assert "activateWeightedShuffle" in js
    assert "updateShuffleBtn" in js


def test_shuffle_js_has_next_prev_index():
    """nextIndex / prevIndex must exist and respect shuffle state."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
    assert "function nextIndex" in js
    assert "function prevIndex" in js
    assert "shuffleQueue" in js
    assert "shufflePos" in js


def test_shuffle_js_restores_from_localstorage():
    """Shuffle preference must be loaded from localStorage on startup."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
    assert "ht-shuffle-mode" in js
    assert "localStorage.getItem" in js


def test_shuffle_js_has_long_press_binding():
    """Shuffle button must support long-press for weighted shuffle mode."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
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
            emoji="🎵",
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
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-shuffle"' in html
    assert "SHUFFLE_ENABLED = true" in html


def test_video_server_does_not_enable_shuffle():
    """The video server must NOT include the shuffle button."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert 'id="btn-shuffle"' not in html
    assert "SHUFFLE_ENABLED = false" in html


def test_shuffle_queue_rebuild_in_render_tracks():
    """JS must rebuild the shuffle queue when filteredItems changes (applyFilter)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track", enable_shuffle=True)
    # rebuildShuffleQueue must be called inside renderTracks
    assert "filteredItems = tracks" in js
    assert "rebuildShuffleQueue" in js


# ---------------------------------------------------------------------------
# Rating write — audio-only feature, star buttons in player
# ---------------------------------------------------------------------------


def _audio_page_with_rating():
    return render_media_page(
        title="Test",
        emoji="🎵",
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
    """RATING_WRITE_ENABLED must be true when enable_rating_write=True."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "RATING_WRITE_ENABLED = true" in js


def test_rating_write_js_flag_false_by_default():
    """RATING_WRITE_ENABLED must be false when enable_rating_write=False."""
    js = _js()
    assert "RATING_WRITE_ENABLED = false" in js


def test_rating_api_path_injected():
    """RATING_API_PATH must be injected and point to /api/audio/rating."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "RATING_API_PATH = '/api/audio/rating'" in js


def test_rating_js_has_render_and_set_functions():
    """renderPlayerRating and setRating JS functions must exist."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "renderPlayerRating" in js
    assert "setRating" in js


def test_rating_js_calls_fetch_rating_api():
    """setRating must call fetch with RATING_API_PATH and POST method."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track", enable_rating_write=True)
    assert "fetch(RATING_API_PATH" in js
    assert "'POST'" in js


def test_rating_js_calls_render_on_play():
    """renderPlayerRating must be called inside playItem when a track is selected."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
    assert "renderPlayerRating" in js


def test_rating_js_updates_after_metadata_refresh():
    """After refreshMetadata, renderPlayerRating should be called with updated value."""
    js = render_player_js(api_path="/api/audio/tracks", item_noun="track")
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
    """The audio server HTML must include RATING_WRITE_ENABLED = true."""
    from fastapi.testclient import TestClient

    from hometools.streaming.audio.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert "RATING_WRITE_ENABLED = true" in html


def test_video_server_does_not_enable_rating_write():
    """The video server must NOT enable rating write."""
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    client = TestClient(create_app())
    html = client.get("/").text
    assert "RATING_WRITE_ENABLED = false" in html


def test_rating_in_both_player_bar_styles():
    """Rating container must appear in both classic and waveform player bars."""
    for style in ("classic", "waveform"):
        page = render_media_page(
            title="Test",
            emoji="🎵",
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
    """The genre filter chip button must be present in the rendered HTML."""
    from hometools.streaming.core.server_utils import render_media_page

    html = render_media_page(
        title="Test",
        emoji="\U0001f3b5",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
    )
    assert 'id="filter-genre"' in html


def test_genre_filter_js_variable():
    """The JS must declare filterGenre variable and persist in localStorage."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track")
    assert "filterGenreBtn" in js
    assert "filterGenre" in js
    assert "ht-filter-genre" in js


def test_genre_filter_apply_logic():
    """applyFilter must filter by genre when filterGenre is set."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track")
    assert "t.genre === filterGenre" in js


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

    js = render_player_js(api_path="/api/test", item_noun="track")
    assert "Touch swipe gestures" in js
    assert "touchstart" in js
    assert "touchend" in js
    assert "SWIPE_MIN_DIST" in js


def test_swipe_gesture_skips_range_inputs():
    """Swipe handler must not intercept touch events on range inputs (progress bar)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track")
    assert "type === 'range'" in js or "el.type === 'range'" in js


def test_swipe_no_next_prev_track():
    """Swipe must NOT trigger next/prev track — only buttons do that."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track")
    # Extract only the swipe gesture IIFE section
    start = js.index("Touch swipe gestures")
    end = js.index("}());", start)
    swipe_section = js[start:end]
    assert "nextIndex()" not in swipe_section
    assert "prevIndex()" not in swipe_section


def test_swipe_right_calls_go_back():
    """Swipe right must call goBack (back navigation only)."""
    from hometools.streaming.core.server_utils import render_player_js

    js = render_player_js(api_path="/api/test", item_noun="track")
    assert "goBack()" in js
