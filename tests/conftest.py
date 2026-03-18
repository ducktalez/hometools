"""Shared fixtures for hometools tests.

UI tests (``@pytest.mark.ui``) require Playwright and a real Uvicorn server.
They are skipped by default (``addopts = "-m 'not ui'"`` in pyproject.toml)
and run explicitly via::

    pytest -m ui               # all UI tests
    pytest -m ui --headed      # with visible browser window

Install once::

    pip install -e ".[ui-test]"
    playwright install chromium
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an unused TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(app, port: int) -> threading.Thread:
    """Start a Uvicorn server in a daemon thread and wait until ready."""
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for the server to accept connections (max 5 s)
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError(f"Server on port {port} did not start in time")

    # Attach server handle for shutdown
    thread.server = server  # type: ignore[attr-defined]
    return thread


# ---------------------------------------------------------------------------
# Session-scoped server fixtures  (only created when ui-marked tests run)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _audio_library(tmp_path_factory):
    """Create a minimal audio library with a few test files."""
    lib = tmp_path_factory.mktemp("audio_lib")
    artist_dir = lib / "Test Artist"
    artist_dir.mkdir()
    (artist_dir / "Test Artist - Song One.mp3").write_bytes(b"\x00" * 64)
    (artist_dir / "Test Artist - Song Two.mp3").write_bytes(b"\x00" * 64)
    (lib / "Loose Track.mp3").write_bytes(b"\x00" * 64)
    return lib


@pytest.fixture(scope="session")
def _video_library(tmp_path_factory):
    """Create a minimal video library with a few test files."""
    lib = tmp_path_factory.mktemp("video_lib")
    folder = lib / "Comedy"
    folder.mkdir()
    (folder / "Funny Movie.mp4").write_bytes(b"\x00" * 64)
    (folder / "Another Film.mp4").write_bytes(b"\x00" * 64)
    (lib / "Standalone.mkv").write_bytes(b"\x00" * 64)
    return lib


@pytest.fixture(scope="session")
def audio_server_url(_audio_library):
    """Start an audio streaming server and return its base URL."""
    from hometools.streaming.audio.server import create_app

    port = _free_port()
    app = create_app(_audio_library)
    thread = _start_server(app, port)
    yield f"http://127.0.0.1:{port}"
    thread.server.should_exit = True  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def video_server_url(_video_library):
    """Start a video streaming server and return its base URL."""
    from hometools.streaming.video.server import create_app

    port = _free_port()
    app = create_app(_video_library)
    thread = _start_server(app, port)
    yield f"http://127.0.0.1:{port}"
    thread.server.should_exit = True  # type: ignore[attr-defined]
