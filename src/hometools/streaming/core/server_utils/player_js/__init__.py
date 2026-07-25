"""player_js subpackage: themed JS fragments concatenated by render_player_js().

Split from the former monolithic ``_player_js.py`` (>8900 lines) into one
module per feature area so agent-assisted edits touch smaller files. The
browser-side JS is one big closure (IIFE); this split is purely at the
Python level and changes no runtime behaviour.
"""

from __future__ import annotations

from ._core import render_core_js
from ._drag_drop_init import render_drag_drop_init_js
from ._folder_browse import render_folder_browse_js
from ._library_tools import render_library_tools_js
from ._playlists import render_playlists_js
from ._queue import render_queue_js
from ._search_filter import render_search_filter_js
from ._smart_playlists import render_smart_playlists_js
from ._track_render import render_track_render_js

__all__ = [
    "render_core_js",
    "render_drag_drop_init_js",
    "render_folder_browse_js",
    "render_library_tools_js",
    "render_playlists_js",
    "render_queue_js",
    "render_search_filter_js",
    "render_smart_playlists_js",
    "render_track_render_js",
]
