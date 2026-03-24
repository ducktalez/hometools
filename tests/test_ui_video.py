"""Browser UI tests for the video streaming server.

Run with::

    pytest -m ui                 # headless
    pytest -m ui --headed        # visible browser
    pytest -m ui -k video        # only video UI tests

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


def test_video_page_loads(page, video_server_url):
    """The video home page should render the dark-theme shell."""
    page.goto(video_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("#folder-grid").count() == 1
    assert page.locator("#track-list").count() == 1
    assert page.locator("#search-input").count() == 1


def test_video_page_has_video_element(page, video_server_url):
    """A <video> element must exist for playback."""
    page.goto(video_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("video").count() >= 1


def test_video_page_no_js_errors(page, video_server_url):
    """The page should load without JavaScript errors."""
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    assert not errors, f"JavaScript errors on page: {errors}"


# ---------------------------------------------------------------------------
# Async catalog loading
# ---------------------------------------------------------------------------


def test_video_catalog_loads_items(page, video_server_url):
    """After async fetch, the catalog should contain items from the test library."""
    page.goto(video_server_url)

    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    # The test library has a "Comedy" folder and a standalone video
    cards = page.locator(".folder-card").count()
    assert cards >= 1, "Expected at least one folder/file card after catalog load"


def test_video_track_count_updates(page, video_server_url):
    """The track count label should update after catalog load."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    count_text = page.locator("#track-count").inner_text()
    assert "loading" not in count_text.lower(), f"Track count still loading: {count_text}"


# ---------------------------------------------------------------------------
# Folder navigation
# ---------------------------------------------------------------------------


def test_video_folder_navigation(page, video_server_url):
    """Clicking a folder card should navigate into it and show videos."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card:not(.file-card)').length > 0",
        timeout=10_000,
    )

    first_folder = page.locator(".folder-card:not(.file-card)").first
    first_folder.click()

    page.wait_for_function(
        "document.querySelectorAll('.track-item').length > 0",
        timeout=5_000,
    )

    track_items = page.locator(".track-item").count()
    assert track_items >= 1, "Expected video items inside folder"


def test_video_back_button_returns_to_folders(page, video_server_url):
    """After navigating into a folder, the back button should return to folder view."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card:not(.file-card)').length > 0",
        timeout=10_000,
    )

    folders_before = page.locator(".folder-card").count()

    # Navigate into folder
    page.locator(".folder-card:not(.file-card)").first.click()
    page.wait_for_function(
        "document.querySelectorAll('.track-item').length > 0",
        timeout=5_000,
    )

    # Click back
    back_btn = page.locator("#back-btn")
    back_btn.click()

    page.wait_for_function(
        "document.querySelectorAll('.folder-card').length > 0",
        timeout=5_000,
    )

    folders_after = page.locator(".folder-card").count()
    assert folders_after == folders_before, "Back button should restore folder view"


# ---------------------------------------------------------------------------
# Download buttons
# ---------------------------------------------------------------------------


def test_video_track_has_download_button(page, video_server_url):
    """Each video in the list view should have a download button."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card:not(.file-card)').length > 0",
        timeout=10_000,
    )

    page.locator(".folder-card:not(.file-card)").first.click()
    page.wait_for_function(
        "document.querySelectorAll('.track-item').length > 0",
        timeout=5_000,
    )

    dl_buttons = page.locator(".track-dl-btn")
    tracks = page.locator(".track-item")
    assert dl_buttons.count() == tracks.count(), "Every track should have a download button"


def test_video_download_button_does_not_trigger_playback(page, video_server_url):
    """Clicking the download button must NOT start video playback."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card:not(.file-card)').length > 0",
        timeout=10_000,
    )

    page.locator(".folder-card:not(.file-card)").first.click()
    page.wait_for_function(
        "document.querySelectorAll('.track-item').length > 0",
        timeout=5_000,
    )

    src_before = page.evaluate("document.querySelector('video').src")

    dl_btn = page.locator(".track-dl-btn").first
    dl_btn.click()
    page.wait_for_timeout(500)

    src_after = page.evaluate("document.querySelector('video').src")
    assert src_after == src_before, "Download button click should not trigger playback"


# ---------------------------------------------------------------------------
# PWA elements
# ---------------------------------------------------------------------------


def test_video_page_has_manifest_link(page, video_server_url):
    """The page should have a <link rel='manifest'> for PWA."""
    page.goto(video_server_url)
    page.wait_for_load_state("domcontentloaded")

    manifest_link = page.locator("link[rel='manifest']")
    assert manifest_link.count() == 1


def test_video_indexeddb_initialized(page, video_server_url):
    """IndexedDB 'hometools-downloads' should be opened at version 2."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

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
    assert db_info["version"] == 2
    assert "downloads" in db_info["stores"]


# ---------------------------------------------------------------------------
# Offline library
# ---------------------------------------------------------------------------


def test_video_offline_button_exists(page, video_server_url):
    """The downloaded pill should be present."""
    page.goto(video_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("#downloaded-pill").count() == 1


def test_video_offline_panel_opens_on_click(page, video_server_url):
    """Clicking the downloaded pill should open the offline library panel."""
    page.goto(video_server_url)
    page.wait_for_function(
        "document.querySelectorAll('.folder-card, .track-item').length > 0",
        timeout=10_000,
    )

    is_hidden = page.evaluate("document.getElementById('offline-library').hidden")
    assert is_hidden, "Offline panel should start hidden"

    page.locator("#downloaded-pill").click()
    page.wait_for_timeout(300)

    is_hidden_after = page.evaluate("document.getElementById('offline-library').hidden")
    assert not is_hidden_after, "Offline panel should be visible after click"


# ---------------------------------------------------------------------------
# Audio↔Video parity: both must have same UI structure
# ---------------------------------------------------------------------------


def test_video_has_sort_field(page, video_server_url):
    """The video UI should have a sort dropdown like audio."""
    page.goto(video_server_url)
    page.wait_for_load_state("domcontentloaded")

    assert page.locator("#sort-field").count() == 1
