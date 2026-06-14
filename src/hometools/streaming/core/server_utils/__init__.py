"""Shared server utilities — path validation and base CSS/JS for dark-theme media UIs.

INSTRUCTIONS (local):
- ``render_media_page()`` is the SINGLE HTML skeleton for all media types.
  Do NOT duplicate it in audio/video servers. Pass differences as parameters.
- CSS and JS are plain strings (no f-strings) to avoid Python escaping issues.
- ``render_player_js`` reads the ``items`` key from API responses. All API
  endpoints must return ``{ "items": [...] }`` — not ``tracks`` or ``videos``.
- ``resolve_media_path`` validates path traversal + suffix. Always use it
  instead of manual path joins in server endpoints.

This package was split out of a single ~7300-line ``server_utils.py`` module.
All public symbols are re-exported here for backward compatibility.
"""

from __future__ import annotations

import logging

# Re-exports from split sub-modules (backward-compat).
from ._audit import render_audit_panel_html  # noqa: F401
from ._board import render_board_page_html  # noqa: F401
from ._css import render_base_css  # noqa: F401
from ._html import render_media_page  # noqa: F401
from ._library import (  # noqa: F401
    build_index_status_payload,
    check_library_accessible,
    render_error_page,
)
from ._paths import resolve_media_path, safe_resolve  # noqa: F401
from ._player_js import render_player_js  # noqa: F401
from ._pwa import (  # noqa: F401
    render_pwa_head_tags,
    render_pwa_icon_png,
    render_pwa_icon_svg,
    render_pwa_manifest,
    render_pwa_service_worker,
)
from ._svg import *  # noqa: F403

logger = logging.getLogger(__name__)
