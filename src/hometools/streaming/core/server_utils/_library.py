"""Library directory accessibility checks and index-status payloads."""

from __future__ import annotations

import html
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_check_cache: dict[str, tuple[tuple[bool, str], float]] = {}
_CHECK_CACHE_TTL = 10.0  # seconds


def check_library_accessible(library_dir: Path, timeout: float = 3.0) -> tuple[bool, str]:
    """Check whether a library directory is accessible.

    Uses a **timeout** so that unreachable network paths (UNC/SMB) don't
    block the server.  Results are cached for ``_CHECK_CACHE_TTL`` seconds
    to avoid repeated slow probes on every request.

    Returns ``(ok, message)``.
    """
    key = str(library_dir)
    now = time.monotonic()

    # Return cached result if fresh enough
    if key in _check_cache:
        cached_result, cached_at = _check_cache[key]
        if now - cached_at < _CHECK_CACHE_TTL:
            return cached_result

    path_str = key
    is_unc = path_str.startswith("\\\\") or path_str.startswith("//")

    result: list[tuple[bool, str]] = []

    def _probe() -> None:
        try:
            if not library_dir.exists():
                hint = ""
                if is_unc:
                    hint = (
                        " Tipp: LIBRARY_DIR sollte ein schneller lokaler Ordner sein. "
                        "Den NAS-Pfad stattdessen als NAS_DIR für 'sync' verwenden."
                    )
                result.append((False, f"Verzeichnis existiert nicht: {library_dir}{hint}"))
            elif not library_dir.is_dir():
                result.append((False, f"Pfad ist kein Verzeichnis: {library_dir}"))
            else:
                result.append((True, "ok"))
        except OSError as exc:
            reason = f"Pfad nicht erreichbar: {exc}"
            if is_unc:
                reason += (
                    " — UNC-Netzwerkpfade (\\\\Server\\Share) erfordern, dass das NAS eingeschaltet und die Freigabe authentifiziert ist."
                )
            result.append((False, reason))

    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if not result:
        # Thread is still running → timeout
        msg = f"Zeitüberschreitung ({timeout}s): Pfad nicht erreichbar: {library_dir}"
        if is_unc:
            msg += (
                " — UNC-Netzwerkpfade können bei nicht erreichbarem NAS "
                "lange blockieren. Verwenden Sie einen lokalen Ordner als LIBRARY_DIR."
            )
        outcome = (False, msg)
    else:
        outcome = result[0]

    _check_cache[key] = (outcome, now)
    return outcome


def render_error_page(title: str, emoji: str, error_message: str, library_dir: Path) -> str:
    """Return a minimal dark-theme HTML page showing a library access error."""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — Fehler</title>
<style>
body {{ background:#121212; color:#fff; font-family:system-ui,sans-serif;
       display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
.card {{ background:#1e1e1e; border-radius:12px; padding:2rem 2.5rem; max-width:600px; }}
h1 {{ margin:0 0 1rem; font-size:1.3rem; }}
.err {{ color:#ff6b6b; background:#2a1515; border-radius:8px; padding:1rem; font-size:0.9rem;
        word-break:break-all; margin:1rem 0; }}
.path {{ color:#b3b3b3; font-size:0.85rem; }}
.hint {{ color:#b3b3b3; font-size:0.85rem; margin-top:1rem; }}
code {{ background:#282828; padding:0.15rem 0.4rem; border-radius:4px; font-size:0.85rem; }}
</style></head><body>
<div class="card">
<h1>{emoji} {html.escape(title)}</h1>
<div class="err">⚠ {html.escape(error_message)}</div>
<div class="path">Konfigurierter Pfad: <code>{html.escape(str(library_dir))}</code></div>
<div class="hint">
  Prüfen Sie die Einstellung in <code>.env</code> und stellen Sie sicher,
  dass das Verzeichnis existiert und erreichbar ist.<br>
  Der Server läuft weiter — laden Sie die Seite neu, sobald das Problem behoben ist.
</div>
</div></body></html>"""


def build_index_status_payload(
    *,
    library_dir: Path,
    item_label: str,
    library_ok: bool,
    library_message: str,
    cache_status: dict[str, object],
    issues_summary: dict[str, object] | None = None,
    todo_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a normalized API payload describing index-build state.

    Used by both audio and video servers so the frontend can diagnose slow
    background scans consistently.
    """
    path_str = str(library_dir)
    is_unc = path_str.startswith("\\\\") or path_str.startswith("//")
    detail = library_message
    if library_ok and bool(cache_status.get("building")):
        runtime = cache_status.get("build_running_for_seconds")
        if runtime is not None:
            detail = f"Building {item_label} index in background for {float(runtime):.1f}s"
        else:
            detail = f"Building {item_label} index in background"
        if is_unc:
            detail += ". UNC/NAS libraries can be very slow on the first scan; a local LIBRARY_DIR plus NAS sync is recommended."

    payload = {
        "library_dir": path_str,
        "library_accessible": library_ok,
        "detail": detail,
        "cache": cache_status,
    }
    if issues_summary is not None:
        payload["issues"] = issues_summary
    if todo_summary is not None:
        payload["todos"] = todo_summary
    return payload
