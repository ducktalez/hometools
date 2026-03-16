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
    assert "generateWaveform(t.stream_url)" in js


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
