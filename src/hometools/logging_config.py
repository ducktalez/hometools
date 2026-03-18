"""Centralized logging setup for hometools."""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

from hometools.config import get_cache_dir
from hometools.streaming.core.issue_registry import record_issue


def get_log_dir() -> Path:
    """Return the directory used for server log files.

    Defaults to ``~/hometools-cache/logs``.  The directory is created
    automatically if it does not exist.
    """
    log_dir = get_cache_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class OpenIssuesHandler(logging.Handler):
    """Mirror WARNING/ERROR records into the open-issues registry."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            return
        if not record.name.startswith("hometools"):
            return
        if record.name.startswith("hometools.streaming.core.issue_registry"):
            return

        try:
            message = record.getMessage()
            details = {
                "logger": record.name,
                "level": record.levelname,
                "pathname": record.pathname,
                "lineno": record.lineno,
            }
            if record.exc_info:
                formatter = logging.Formatter()
                details["traceback"] = formatter.formatException(record.exc_info)
            issue_key = getattr(record, "issue_key", None)
            source = getattr(record, "issue_source", record.name)
            record_issue(
                get_cache_dir(),
                source=str(source),
                severity=record.levelname,
                message=message,
                issue_key=str(issue_key) if issue_key else None,
                details=details,
            )
        except Exception:
            return


def setup_logging(level=logging.INFO, log_file: str | None = "hometools.log", *, log_name: str = "hometools"):
    """Configure logging for the entire hometools package.

    Call once at application startup (e.g. in your CLI entry-point).

    When *log_file* is ``"auto"`` the log is written to
    ``~/hometools-cache/logs/<log_name>-YYYYMMDD-HHMMSS.log``.
    Pass ``None`` to disable file logging entirely.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout), OpenIssuesHandler()]

    if log_file == "auto":
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_log_name = log_name.replace("/", "-").replace("\\", "-").strip() or "hometools"
        path = get_log_dir() / f"{safe_log_name}-{timestamp}.log"
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
        force=True,
    )
