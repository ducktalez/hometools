"""CSS subpackage: themed fragments concatenated by render_base_css().

Split from the former monolithic ``_css.py`` (>1800 lines) into one
module per UI area so agent-assisted edits touch smaller files.

Fragments leave this package as they are ported to real ``.css`` under
``webui/src/styles/`` (Vite/TS migration) — meta pill is gone already.
"""

from __future__ import annotations

from ._modals import render_modals_css
from ._player_bar import render_player_bar_css
from ._playlist_cards import render_playlist_cards_css
from ._root import render_root_css
from ._table_view import render_table_view_css
from ._tools_panel import render_tools_panel_css
from ._track_list import render_track_list_css
from ._video_overlay import render_video_overlay_css

__all__ = [
    "render_modals_css",
    "render_player_bar_css",
    "render_playlist_cards_css",
    "render_root_css",
    "render_table_view_css",
    "render_tools_panel_css",
    "render_track_list_css",
    "render_video_overlay_css",
]
