"""Centralized logging setup for hometools."""

import logging
import sys


def setup_logging(level=logging.INFO, log_file: str | None = "hometools.log"):
    """Configure logging for the entire hometools package.

    Call once at application startup (e.g. in your CLI entry-point).
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
