"""CSS generation for the streaming player UI.

The actual CSS text lives in themed fragments under ``server_utils/css/``
(split from a >1800 line monolith); this module only concatenates them in
a fixed order so ``render_base_css()`` keeps its original public signature.

Vite/TS migration: fragments move out of here one at a time into real
``.css`` files under ``webui/src/styles/``, imported by ``main.ts`` and
linked by ``_html.py`` after this inline block. Ported so far: meta pill
(``styles/metaPill.css``), root (``styles/root.css``), tools panel
(``styles/toolsPanel.css``), modals (``styles/modals.css``), playlist cards
(``styles/playlistCards.css``), player bar (``styles/playerBar.css``),
table view (``styles/tableView.css``).
"""

from __future__ import annotations

from .css import render_track_list_css, render_video_overlay_css


def render_base_css() -> str:
    """Return the shared dark-theme CSS used by both audio and video UIs."""
    return render_track_list_css() + render_video_overlay_css()
