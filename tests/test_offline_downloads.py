"""Tests for offline download feature."""


class TestDownloadUI:
    """Download button appears in both player bar styles."""

    def test_download_button_in_waveform(self):
        """Download button must exist in waveform player bar."""
        from hometools.streaming.core.server_utils import render_media_page

        html = render_media_page(
            title="Videos",
            emoji="🎬",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            item_noun="video",
            player_bar_style="waveform",
        )

        assert 'id="btn-dl"' in html
        assert "initDownloadDB" in html

    def test_download_button_in_classic(self):
        """Download button must exist in classic player bar."""
        from hometools.streaming.core.server_utils import render_media_page

        html = render_media_page(
            title="Videos",
            emoji="🎬",
            items_json="[]",
            media_element_tag="video",
            api_path="/api/video/items",
            item_noun="video",
            player_bar_style="classic",
        )

        assert 'id="btn-dl"' in html
        assert "downloadMedia" in html


class TestServiceWorkerOfflineSupport:
    """Service worker must cache HTML/CSS/JS for offline UI."""

    def test_service_worker_has_offline_cache(self):
        """Service worker must cache static assets."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "CACHE_NAME" in sw
        assert "DOWNLOAD_CACHE" in sw
        assert "destination === 'document'" in sw
        assert "destination === 'script'" in sw
        assert "destination === 'style'" in sw

    def test_service_worker_handles_offline_streams(self):
        """Service worker must handle offline stream requests."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "serveFromIndexedDB" in sw
        assert "Offline — " in sw

    def test_service_worker_message_handling(self):
        """Service worker must handle download caching messages."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "addEventListener('message'" in sw
        assert "CACHE_DOWNLOAD" in sw
        assert "DOWNLOAD_CACHED" in sw


class TestDownloadFeature:
    """Download manager JS code exists and works."""

    def test_js_has_indexeddb_init(self):
        """IndexedDB initialization must exist."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "initDownloadDB" in js
        assert "indexedDB.open" in js
        assert "'hometools-downloads'" in js

    def test_js_has_download_function(self):
        """Download function must exist."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "function downloadMedia" in js
        assert "fetch(streamUrl)" in js
        assert "getReader()" in js

    def test_js_has_download_progress(self):
        """Download progress tracking must exist."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "content-length" in js
        assert "Math.round((received / total) * 100)" in js
        assert "downloading" in js


class TestDownloadCSS:
    """Download button styling."""

    def test_download_button_css_exists(self):
        """Download button CSS must exist."""
        from hometools.streaming.core.server_utils import render_base_css

        css = render_base_css()

        assert ".ctrl-btn.dl-btn" in css
        assert ".ctrl-btn.dl-btn[hidden]" in css
        assert ".ctrl-btn.dl-btn.downloading" in css


class TestOfflinePlayback:
    """Offline playback from IndexedDB."""

    def test_service_worker_serves_from_indexeddb(self):
        """Service worker must be able to serve cached blobs from IndexedDB."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        # Must have function to serve from IndexedDB
        assert "serveFromIndexedDB" in sw
        assert "indexedDB.open" in sw
        assert "store.index('streamUrl')" in sw
        assert "new Response" in sw

    def test_service_worker_sets_correct_headers(self):
        """Service worker response must have correct Content-Type and headers."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "Content-Type" in sw
        assert "Content-Length" in sw
        assert "Accept-Ranges" in sw
        assert "Cache-Control" in sw

    def test_js_checks_if_media_cached(self):
        """Frontend must check if media is cached before playing."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "checkIfMediaCached" in js
        assert "store.index('streamUrl')" in js

    def test_js_creates_blob_url(self):
        """Frontend must create blob URLs for offline playback."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "getOfflineUrl" in js
        assert "URL.createObjectURL" in js

    def test_js_plays_offline_or_stream(self):
        """Frontend must try offline first, then fallback to stream."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "playOfflineOrStream" in js
        assert "Playing from offline cache" in js

    def test_js_handles_online_offline_events(self):
        """Frontend must listen to online/offline events."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "window.addEventListener('online'" in js or "addEventListener('online'" in js
        assert "window.addEventListener('offline'" in js or "addEventListener('offline'" in js
        assert "Back online" in js
        assert "Offline mode" in js

    def test_js_overrides_play_track_for_offline(self):
        """playTrack must be overridden to support offline playback."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        assert "var originalPlayTrack = playTrack" in js
        assert "playOfflineOrStream" in js


class TestOfflineDownloadIntegration:
    """Integration tests for download → offline playback flow."""

    def test_download_flow_complete(self):
        """Full download cycle must be present."""
        from hometools.streaming.core.server_utils import render_player_js

        js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="classic")

        # Download capture
        assert "downloadMedia" in js
        assert "fetch(streamUrl)" in js

        # IndexedDB storage
        assert "store.put" in js

        # Offline retrieval
        assert "checkIfMediaCached" in js

        # Playback
        assert "URL.createObjectURL" in js or "getOfflineUrl" in js

    def test_service_worker_handles_offline_stream_request(self):
        """Service worker must intercept stream requests and serve offline."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        # Must handle /stream paths
        assert "/stream" in sw or "includes('/stream')" in sw

        # Must handle /audio and /video paths
        assert "/audio/" in sw or "includes('/audio/')" in sw
        assert "/video/" in sw or "includes('/video/')" in sw

        # Must try network first
        assert "fetch(event.request)" in sw

        # Must fallback to IndexedDB
        assert "serveFromIndexedDB" in sw
