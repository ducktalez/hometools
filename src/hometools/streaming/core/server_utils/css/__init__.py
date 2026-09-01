"""CSS subpackage: themed fragments concatenated by render_base_css().

Split from the former monolithic ``_css.py`` (>1800 lines) into one
module per UI area so agent-assisted edits touch smaller files.

Fragments leave this package as they are ported to real ``.css`` under
``webui/src/styles/`` (Vite/TS migration) — meta pill, root, tools panel,
modals, playlist cards, player bar, table view are gone already.
"""

from __future__ import annotations

from ._track_list import render_track_list_css
from ._video_overlay import render_video_overlay_css

__all__ = [
    "render_track_list_css",
    "render_video_overlay_css",
]
