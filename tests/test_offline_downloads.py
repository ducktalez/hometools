"""Tests for offline download feature — service worker, download list and quota UI."""

from hometools.streaming.core.server_utils import render_base_css, render_media_page, render_player_js


def _js():
    return render_player_js(api_path="/api/test", item_noun="track", player_bar_style="classic")


def _page():
    return render_media_page(
        title="Test",
        emoji="🎵",
        items_json="[]",
        media_element_tag="audio",
        api_path="/api/test",
        item_noun="track",
        player_bar_style="classic",
    )


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
        assert "request.url" in sw

    def test_service_worker_message_handling(self):
        """Service worker must handle caching messages."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "addEventListener('message'" in sw
        assert "CACHE_DOWNLOAD" in sw
        assert "DOWNLOAD_CACHED" in sw
        assert "DOWNLOAD_DELETED" in sw


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

    def test_service_worker_supports_range_requests(self):
        """Offline media responses should support byte ranges for scrubbing/seeking."""
        from hometools.streaming.core.server_utils import render_pwa_service_worker

        sw = render_pwa_service_worker()

        assert "Content-Range" in sw
        assert "status: 206" in sw
        assert "request.headers.get('range')" in sw


class TestTrackDownloadButtons:
    """Download button per track in the list view."""

    def test_js_has_track_dl_btn_in_render(self):
        """Each track item must contain a download button."""
        js = _js()
        assert "track-dl-btn" in js

    def test_js_has_init_download_db(self):
        """initDownloadDB must open IndexedDB for downloads."""
        js = _js()
        assert "function initDownloadDB" in js
        assert "indexedDB.open" in js
        assert "'hometools-downloads'" in js

    def test_js_has_download_track_function(self):
        """downloadTrack must fetch with progress and store blob in IndexedDB."""
        js = _js()
        assert "function downloadTrack" in js
        assert "fetch(streamUrl)" in js
        assert "getReader()" in js
        assert "new Blob" in js

    def test_js_has_delete_track_download_function(self):
        """deleteTrackDownload must remove a cached download from IndexedDB."""
        js = _js()
        assert "function deleteTrackDownload" in js
        assert "deleteDownloadById" in js
        assert ".delete(id)" in js

    def test_js_has_update_all_download_buttons(self):
        """updateAllDownloadButtons must check cached status for all track buttons."""
        js = _js()
        assert "function updateAllDownloadButtons" in js
        assert "track-dl-btn" in js
        assert "cached" in js

    def test_js_dl_btn_click_stops_propagation(self):
        """Download button click must not bubble to track click (play)."""
        js = _js()
        assert "stopPropagation" in js

    def test_js_dl_btn_toggle_behavior(self):
        """Clicking a cached button should delete, clicking uncached should download."""
        js = _js()
        assert "deleteTrackDownload" in js
        assert "downloadTrack" in js
        assert "classList.contains('cached')" in js

    def test_js_init_download_db_called_at_startup(self):
        """initDownloadDB must be called during init."""
        js = _js()
        # The init block should call initDownloadDB
        assert "initDownloadDB()" in js

    def test_js_listens_for_sw_download_messages(self):
        """JS should listen for DOWNLOAD_CACHED messages from service worker."""
        js = _js()
        assert "DOWNLOAD_CACHED" in js
        assert "serviceWorker" in js

    def test_js_track_download_stores_metadata_for_offline_library(self):
        """Downloads should persist enough metadata for the offline list UI."""
        js = _js()
        assert "thumbnailUrl" in js
        assert "relativePath" in js
        assert "mediaType" in js
        assert "artist" in js


class TestOfflineLibraryUI:
    """Offline library modal/list UI."""

    def test_page_has_offline_library_controls(self):
        page = _page()
        assert 'id="offline-btn"' in page
        assert 'id="offline-library"' in page
        assert 'id="offline-download-list"' in page
        assert 'id="offline-sort"' in page

    def test_js_has_offline_library_rendering(self):
        js = _js()
        assert "function refreshOfflineLibrary" in js
        assert "function renderOfflineDownloadList" in js
        assert "Offline-Bibliothek" not in js
        assert "offline-download-item" in js

    def test_js_can_play_from_offline_library(self):
        js = _js()
        assert "function playStoredDownload" in js
        assert "findItemByStreamUrl" in js
        assert "playItem(" in js


class TestStorageQuotaHandling:
    """Quota UI and pruning hooks."""

    def test_js_has_storage_estimate_and_persist(self):
        js = _js()
        assert "navigator.storage.estimate" in js
        assert "navigator.storage.persist" in js
        assert "function requestPersistentStorage" in js

    def test_js_has_soft_limit_and_prune_logic(self):
        js = _js()
        assert "OFFLINE_SOFT_LIMIT" in js
        assert "function pruneOldDownloads" in js
        assert "function ensureStorageBudget" in js
        assert "50 * 1024 * 1024" in js

    def test_js_updates_storage_summary(self):
        js = _js()
        assert "function renderStorageSummary" in js
        assert "offline-storage-summary" in js
        assert "offline-storage-detail" in js


class TestOfflinePlaybackIntegrationHooks:
    """Hooks needed for end-to-end offline playback flow."""

    def test_js_has_explicit_offline_playback_helpers(self):
        js = _js()
        assert "function checkIfMediaCached" in js
        assert "function getOfflineUrl" in js
        assert "function playOfflineOrStream" in js

    def test_js_cleans_up_blob_urls(self):
        js = _js()
        assert "URL.revokeObjectURL" in js
        assert "currentOfflineUrl" in js

    def test_js_has_stream_fallback_when_blob_playback_fails(self):
        js = _js()
        assert "Offline playback failed, falling back to stream" in js
        assert "fallbackUrl" in js

    def test_js_listens_to_online_offline_events(self):
        js = _js()
        assert "window.addEventListener('online'" in js
        assert "window.addEventListener('offline'" in js


class TestTrackDownloadCSS:
    """CSS for track download buttons."""

    def test_css_has_track_dl_btn(self):
        """CSS must style the .track-dl-btn class."""
        css = render_base_css()
        assert ".track-dl-btn" in css

    def test_css_has_cached_state(self):
        """CSS must have a .cached state for downloaded tracks."""
        css = render_base_css()
        assert ".track-dl-btn.cached" in css

    def test_css_has_downloading_state(self):
        """CSS must have a .downloading state with animation."""
        css = render_base_css()
        assert ".track-dl-btn.downloading" in css
        assert "dl-pulse" in css

    def test_css_has_offline_library_styles(self):
        """CSS must style the offline modal/list."""
        css = render_base_css()
        assert ".offline-library" in css
        assert ".offline-panel" in css
        assert ".offline-download-item" in css
