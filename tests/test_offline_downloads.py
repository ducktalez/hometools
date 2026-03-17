"""Tests for offline service worker support (Download UI was removed from player)."""


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
        assert "Offline" in sw

    def test_service_worker_message_handling(self):
        """Service worker must handle caching messages."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "addEventListener('message'" in sw
        assert "CACHE_DOWNLOAD" in sw
        assert "DOWNLOAD_CACHED" in sw


class TestOfflinePlayback:
    """Service worker offline playback support."""

    def test_service_worker_serves_from_indexeddb(self):
        """Service worker must be able to serve cached blobs from IndexedDB."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

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

    def test_service_worker_handles_offline_stream_request(self):
        """Service worker must intercept stream requests and serve offline."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        # Must handle stream paths
        assert "/stream" in sw or "includes('/stream')" in sw

        # Must try network first
        assert "fetch(event.request)" in sw

        # Must fallback to IndexedDB
        assert "serveFromIndexedDB" in sw

