"""Static asset serving for the Vite/TypeScript-built player UI bundle.

Vite/TS migration Phase 4 (docs/IMPLEMENTATION_PLAN.md): the webui scaffold
under ``streaming/core/webui/`` builds to ``streaming/core/static/`` (git-
ignored — must be built via ``npm run build`` before packaging, or produced
by the Docker build stage). This module resolves that build output at
runtime and mounts it under ``/static`` on a FastAPI app.

Every function here is defensive: a missing/unbuilt ``static/`` directory
(e.g. local dev without ``npm install``/``npm run build``) must never crash
server startup or page rendering — it only means the ported TS symbols
(``fmtTime``/``escHtml``/``formatBytes`` and whatever else is ported in the
future) are unavailable, which is logged loudly so it's easy to notice
during development.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# streaming/core/server_utils/_static.py -> streaming/core/static/
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_MANIFEST_PATH = STATIC_DIR / ".vite" / "manifest.json"
_ENTRY_KEY = "src/main.ts"

_manifest_cache: dict[str, Any] | None = None
_warned_missing = False


def _load_manifest() -> dict[str, Any] | None:
    """Read + cache the Vite manifest. Returns ``None`` on any failure."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache
    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
            _manifest_cache = json.load(fh)
        return _manifest_cache
    except (OSError, ValueError):
        return None


def mount_static_assets(app: Any) -> bool:
    """Mount the built webui bundle at ``/static`` if it exists.

    Never raises — returns ``True`` if the mount happened, ``False`` if the
    ``static/`` directory doesn't exist yet (unbuilt webui scaffold). Server
    startup must stay instant and must never fail because of this.
    """
    global _warned_missing
    if not STATIC_DIR.is_dir():
        if not _warned_missing:
            logger.warning(
                "Static webui bundle not found at %s — run "
                "'npm install && npm run build' in src/hometools/streaming/core/webui/ "
                "(or use the Docker image, which builds it automatically). "
                "The player UI falls back to server-generated inline JS only; "
                "any already-ported TS module (e.g. fmtTime/escHtml/formatBytes) "
                "will be unavailable and referencing it will throw at runtime.",
                STATIC_DIR,
            )
            _warned_missing = True
        return False
    try:
        from fastapi.staticfiles import StaticFiles

        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        return True
    except Exception:
        logger.exception("Failed to mount /static from %s", STATIC_DIR)
        return False


def get_static_script_tag() -> str:
    """Return a ``<script src="/static/...">`` tag for the built player bundle.

    Returns an empty string (never raises) if the bundle hasn't been built
    yet — callers must render the page without it in that case.
    """
    manifest = _load_manifest()
    if not manifest:
        return ""
    entry = manifest.get(_ENTRY_KEY)
    if not entry or not isinstance(entry, dict):
        return ""
    file_name = entry.get("file")
    if not file_name:
        return ""
    return f'<script src="/static/{file_name}"></script>'
