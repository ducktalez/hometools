"""Configuration management for hometools.

Loads settings from environment variables / .env file.
Never commit secrets to source control – use .env instead.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set externally


def get_tmdb_api_key() -> str:
    """Return the TMDB API key from the environment."""
    key = os.environ.get("TMDB_API_KEY", "")
    if not key:
        raise RuntimeError(
            "TMDB_API_KEY is not set. "
            "Create a .env file with TMDB_API_KEY=your_key or export it as an environment variable."
        )
    return key


def get_delete_dir() -> Path:
    """Return the soft-delete directory from the environment, with a sensible default."""
    return Path(os.environ.get("HOMETOOLS_DELETE_DIR", Path.home() / "Music" / "DELETE_ME"))
