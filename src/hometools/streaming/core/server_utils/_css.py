"""CSS generation for the streaming player UI.

The actual CSS text lives in themed fragments under ``server_utils/css/``
(split from a >1800 line monolith); this module only concatenates them in
a fixed order so ``render_base_css()`` keeps its original public signature.
"""

from __future__ import annotations

from .css import (
    render_modals_css,
    render_player_bar_css,
    render_playlist_cards_css,
    render_root_css,
    render_table_view_css,
    render_tools_panel_css,
    render_track_list_css,
    render_video_overlay_css,
)


def render_base_css() -> str:
    """Return the shared dark-theme CSS used by both audio and video UIs."""
    return (
        render_root_css()
        + render_tools_panel_css()
        + render_track_list_css()
        + render_table_view_css()
        + render_modals_css()
        + render_playlist_cards_css()
        + render_player_bar_css()
        + render_video_overlay_css()
    )
