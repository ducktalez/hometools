"""CSS generation for the streaming player UI.

All CSS fully migrated to real ``.css`` files under ``webui/src/styles/``
(Vite/TS migration, see ``docs/IMPLEMENTATION_PLAN.md``) — the former
``server_utils/css/`` fragment package is gone. Function kept for API
compat with ``_html.py``'s ``css = render_base_css() + extra_css``.
"""

from __future__ import annotations


def render_base_css() -> str:
    """Return the shared dark-theme CSS used by both audio and video UIs.

    Always empty now — all rules live in ``webui/src/styles/*.css``.
    """
    return ""
