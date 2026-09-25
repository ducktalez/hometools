"""Build helper for the Vite/TypeScript web UI bundle.

Running a streaming server from a source checkout requires the webui
bundle in ``streaming/core/static/`` (the Docker image builds it in its
own stage). Without it ``server_utils/_static.py`` logs a warning and the
player UI loses every already-ported TS module / CSS file — see
``streaming/core/webui/README.md``.

Forgetting the rebuild after touching ``webui/src/`` is the single most
common local-dev breakage, so this module exists to make it a one-liner
(``hometools build-webui``) that is cheap enough to wire up as a PyCharm
before-launch task: :func:`is_bundle_stale` short-circuits when the built
bundle is already newer than every source file.

Exception-safe by project rule: :func:`build_webui` never raises, it
returns ``False`` on any failure so a caller (e.g. a run configuration)
can decide whether to continue with a stale bundle.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

#: webui sources (``package.json``, ``src/``) — repo-relative.
WEBUI_DIR = Path(__file__).resolve().parent / "core" / "webui"
#: Vite output directory consumed by ``server_utils/_static.py``.
STATIC_DIR = Path(__file__).resolve().parent / "core" / "static"

#: Files/dirs whose mtime decides whether a rebuild is needed.
_SOURCE_PATHS = ("src", "package.json", "vite.config.ts", "tsconfig.json")


def _newest_source_mtime(webui_dir: Path) -> float:
    """Return the newest mtime across all webui sources (0.0 if none found)."""
    newest = 0.0
    for rel in _SOURCE_PATHS:
        path = webui_dir / rel
        if not path.exists():
            continue
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
            continue
        for child in path.rglob("*"):
            if child.is_file():
                newest = max(newest, child.stat().st_mtime)
    return newest


def _oldest_bundle_mtime(static_dir: Path) -> float | None:
    """Return the oldest mtime of the built bundle, or ``None`` if unbuilt.

    Oldest (not newest) on purpose: if *any* emitted artefact predates a
    source change the bundle is stale as a whole.
    """
    if not static_dir.is_dir():
        return None
    mtimes = [p.stat().st_mtime for p in static_dir.rglob("*") if p.is_file()]
    return min(mtimes) if mtimes else None


def is_bundle_stale(webui_dir: Path | None = None, static_dir: Path | None = None) -> bool:
    """Return ``True`` if the bundle is missing or older than its sources.

    Never raises — returns ``True`` on any error, since rebuilding is the
    safe fallback.
    """
    webui_dir = webui_dir or WEBUI_DIR
    static_dir = static_dir or STATIC_DIR
    try:
        bundle_mtime = _oldest_bundle_mtime(static_dir)
        if bundle_mtime is None:
            return True
        return _newest_source_mtime(webui_dir) > bundle_mtime
    except OSError:
        logger.warning("Could not compare webui bundle mtimes — assuming stale.", exc_info=True)
        return True


def build_webui(webui_dir: Path | None = None, *, force: bool = False) -> bool:
    """Build the webui bundle via ``npm``. Returns ``True`` on success.

    Skips the build when the bundle is already up to date (unless *force*),
    so this is cheap to call before every server start. Never raises:
    a missing ``npm``/``node`` or a failing build is logged and reported
    via the return value.
    """
    webui_dir = webui_dir or WEBUI_DIR
    if not (webui_dir / "package.json").is_file():
        logger.error("No package.json in %s — cannot build the webui bundle.", webui_dir)
        return False

    if not force and not is_bundle_stale(webui_dir):
        logger.info("webui bundle is up to date — skipping build.")
        return True

    npm = shutil.which("npm")
    if npm is None:
        logger.error(
            "npm not found on PATH — install Node.js to build the webui bundle, or run the Docker image (which builds it automatically)."
        )
        return False

    if not (webui_dir / "node_modules").is_dir():
        logger.info("node_modules missing — running 'npm install' in %s", webui_dir)
        if not _run([npm, "install"], webui_dir):
            return False

    logger.info("Building webui bundle in %s", webui_dir)
    return _run([npm, "run", "build"], webui_dir)


def _run(cmd: list[str], cwd: Path) -> bool:
    """Run *cmd* in *cwd*, streaming output. Returns ``True`` on rc == 0."""
    try:
        # No shell=True: shutil.which() already resolved npm to its full
        # path (npm.cmd on Windows), which subprocess can execute directly.
        completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    except OSError:
        logger.exception("Failed to execute %s", " ".join(cmd))
        return False
    if completed.returncode != 0:
        logger.error("%s failed with exit code %s", " ".join(cmd), completed.returncode)
        return False
    return True
