"""Centralized logging setup for hometools."""

import logging
import logging.handlers
import sys
from pathlib import Path


def get_log_dir() -> Path:
    """Return the directory used for server log files.

    Defaults to ``~/hometools-cache/logs``.  The directory is created
    automatically if it does not exist.
    """
    from hometools.config import get_cache_dir

    log_dir = get_cache_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(level=logging.INFO, log_file: str | None = "hometools.log"):
    """Configure logging for the entire hometools package.

    Call once at application startup (e.g. in your CLI entry-point).

    When *log_file* is ``"auto"`` the log is written to
    ``~/hometools-cache/logs/hometools.log`` (rotated daily-ish by size).
    Pass ``None`` to disable file logging entirely.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file == "auto":
        path = get_log_dir() / "hometools.log"
        file_handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handlers.append(file_handler)
    elif log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
