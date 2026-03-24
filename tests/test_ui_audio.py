"""Browser UI tests for the audio streaming server.

Run with::

    pytest -m ui                 # headless
    pytest -m ui --headed        # visible browser
    pytest -m ui -k audio        # only audio UI tests

Requires::

    pip install -e ".[ui-test]"
    playwright install chromium
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.ui


# ---------------------------------------------------------------------------
# Page load & shell rendering
# ---------------------------------------------------------------------------


def test_audio_page_loads(page, audio_server_url):
    """The audio home page should render the dark-theme shell."""
    page.goto(audio_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert "hometools" in page.title().lower() or "audio" in page.title().lower()
    # The page should have the main UI containers
    assert page.locator("#folder-grid").count() == 1
    assert page.locator("#track-list").count() == 1
    assert page.locator("#search-input").count() == 1


def test_audio_page_has_player_bar(page, audio_server_url):
    """Player bar with controls should be present."""
    page.goto(audio_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator(".player-bar").count() >= 1
    assert page.locator("#btn-play").count() == 1
    assert page.locator("#btn-prev").count() == 1
    assert page.locator("#btn-next").count() == 1


def test_audio_page_has_audio_element(page, audio_server_url):
    """An <audio> element must exist for playback."""
    page.goto(audio_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("audio").count() >= 1


# ---------------------------------------------------------------------------
# Async catalog loading
# ---------------------------------------------------------------------------


def test_audio_catalog_loads_items(page, audio_server_url):
    """After async fetch, the catalog should contain items from the test library."""
    page.goto(audio_server_url)

    # Wait for the catalog to finish loading (folder grid or track items appear)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # The test library has a "Test Artist" folder and a loose track
    cards = page.locator(".folder-card").count()
    assert cards >= 1, "Expected at least one folder card after catalog load"


def test_audio_track_count_updates(page, audio_server_url):
    """The track count label should update after catalog load."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    count_text = page.locator("#track-count").inner_text()
    # Should show something like "3 tracks" (not "Loading…")
    assert "loading" not in count_text.lower(), f"Track count still loading: {count_text}"


# ---------------------------------------------------------------------------
# Folder navigation
# ---------------------------------------------------------------------------


def test_audio_folder_navigation(page, audio_server_url):
    """Clicking a folder card should navigate into it and show tracks."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card').length > 0",
        timeout=10_000,
    )

    # Click the first folder card
    first_folder = page.locator(".folder-card:not(.file-card)").first
    folder_name = first_folder.locator(".folder-name").inner_text()
    first_folder.click()

    # Should transition to playlist/track view
    page.wait_for_function(
        "document.querySelectorAll('.track-item').length > 0",
        timeout=5_000,
    )

    track_items = page.locator(".track-item").count()
    assert track_items >= 1, f"Expected tracks inside folder '{folder_name}'"


# ---------------------------------------------------------------------------
# Search / Filter
# ---------------------------------------------------------------------------


def test_audio_search_filters_tracks(page, audio_server_url):
    """Typing in the search input should filter the displayed items."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # Navigate into a folder first (to get to track list view)
    folders = page.locator(".folder-card:not(.file-card)")
    if folders.count() > 0:
        folders.first.click()
        page.wait_for_function(
            "document.querySelectorAll('.track-item').length > 0",
            timeout=5_000,
        )

    total_before = page.locator(".track-item").count()
    if total_before < 2:
        pytest.skip("Need at least 2 tracks to test filtering")

    # Search for a specific term
    page.fill("#search-input", "Song One")
    page.wait_for_timeout(300)  # debounce

    total_after = page.locator(".track-item").count()
    assert total_after < total_before, "Search should reduce visible items"
    assert total_after >= 1, "Search should find at least one match"


# ---------------------------------------------------------------------------
# Download buttons
# ---------------------------------------------------------------------------


def test_audio_track_has_download_button(page, audio_server_url):
    """Each track in the list view should have a download button."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # Navigate into a folder to see tracks
    folders = page.locator(".folder-card:not(.file-card)")
    if folders.count() > 0:
        folders.first.click()
        page.wait_for_function(
            "document.querySelectorAll('.track-item').length > 0",
            timeout=5_000,
        )

    dl_buttons = page.locator(".track-dl-btn")
    tracks = page.locator(".track-item")
    assert dl_buttons.count() == tracks.count(), "Every track should have a download button"


def test_audio_download_button_does_not_trigger_playback(page, audio_server_url):
    """Clicking the download button must NOT start playback (stopPropagation)."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # Navigate into a folder to see tracks
    folders = page.locator(".folder-card:not(.file-card)")
    if folders.count() > 0:
        folders.first.click()
        page.wait_for_function(
            "document.querySelectorAll('.track-item').length > 0",
            timeout=5_000,
        )

    # Get the audio element src before clicking download
    src_before = page.evaluate("document.querySelector('audio').src")

    # Click the download button (not the track item)
    dl_btn = page.locator(".track-dl-btn").first
    dl_btn.click()
    page.wait_for_timeout(500)

    # The audio source should NOT have changed
    src_after = page.evaluate("document.querySelector('audio').src")
    assert src_after == src_before, "Download button click should not trigger playback"


# ---------------------------------------------------------------------------
# No JS errors on page load
# ---------------------------------------------------------------------------


def test_audio_page_no_js_errors(page, audio_server_url):
    """The page should load without JavaScript errors."""
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    assert not errors, f"JavaScript errors on page: {errors}"


# ---------------------------------------------------------------------------
# PWA elements
# ---------------------------------------------------------------------------


def test_audio_page_has_manifest_link(page, audio_server_url):
    """The page should have a <link rel='manifest'> for PWA."""
    page.goto(audio_server_url)
    page.wait_for_load_state("domcontentloaded")

    manifest_link = page.locator("link[rel='manifest']")
    assert manifest_link.count() == 1, "Page should have a manifest link"


def test_audio_page_registers_service_worker(page, audio_server_url):
    """The page should register a service worker."""
    page.goto(audio_server_url)

    # Wait for service worker registration
    sw_ready = page.evaluate(
        """() => {
            if (!navigator.serviceWorker) return false;
            return navigator.serviceWorker.ready.then(() => true).catch(() => false);
        }"""
    )
    # Note: Service workers may not work in all test environments
    # This test verifies the registration attempt exists
    sw_code = page.locator("script").all_inner_texts()
    has_sw_register = any("serviceWorker" in t and "register" in t for t in sw_code)
    assert has_sw_register or sw_ready, "Page should attempt service worker registration"


# ---------------------------------------------------------------------------
# IndexedDB initialization
# ---------------------------------------------------------------------------


def test_audio_indexeddb_initialized(page, audio_server_url):
    """IndexedDB 'hometools-downloads' should be opened at version 2."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # Check that the DB was opened successfully
    db_info = page.evaluate(
        """() => new Promise((resolve) => {
            const req = indexedDB.open('hometools-downloads', 2);
            req.onsuccess = () => {
                const db = req.result;
                resolve({
                    name: db.name,
                    version: db.version,
                    stores: Array.from(db.objectStoreNames)
                });
                db.close();
            };
            req.onerror = () => resolve(null);
        })"""
    )

    assert db_info is not None, "IndexedDB should be accessible"
    assert db_info["name"] == "hometools-downloads"
    assert db_info["version"] == 2
    assert "downloads" in db_info["stores"]


# ---------------------------------------------------------------------------
# Offline library UI
# ---------------------------------------------------------------------------


def test_audio_offline_button_exists(page, audio_server_url):
    """The downloaded pill should be present."""
    page.goto(audio_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("#downloaded-pill").count() == 1


def test_audio_offline_panel_opens_on_click(page, audio_server_url):
    """Clicking the downloaded pill should open the offline library panel."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # The offline panel should be hidden initially
    is_hidden = page.evaluate("document.getElementById('offline-library').hidden")
    assert is_hidden, "Offline panel should start hidden"

    # Click the downloaded pill
    page.locator("#downloaded-pill").click()
    page.wait_for_timeout(300)

    is_hidden_after = page.evaluate("document.getElementById('offline-library').hidden")
    assert not is_hidden_after, "Offline panel should be visible after click"


# ---------------------------------------------------------------------------
# View mode toggle
# ---------------------------------------------------------------------------


def test_audio_view_toggle(page, audio_server_url):
    """The view toggle should switch between list and grid mode."""
    page.goto(audio_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # Navigate into a folder to see the track list
    folders = page.locator(".folder-card:not(.file-card)")
    if folders.count() > 0:
        folders.first.click()
        page.wait_for_function(
            "document.querySelectorAll('.track-item').length > 0",
            timeout=5_000,
        )

    view_toggle = page.locator("#view-toggle")
    if view_toggle.count() == 0:
        pytest.skip("View toggle not found")

    # Click to switch view mode
    view_toggle.click()
    page.wait_for_timeout(200)

    # The mode should be stored in localStorage
    mode = page.evaluate("localStorage.getItem('ht-view-mode')")
    assert mode in ("list", "grid"), f"View mode should be list or grid, got: {mode}"
