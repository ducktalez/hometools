"""Filtered OpenAPI schema for the streaming servers.

The servers expose HTML and binary (Response-subclass) routes that trip
FastAPI's default schema builder under ``from __future__ import annotations``
(it tries to model a string forward-ref like ``HTMLResponse``). That breaks the
built-in ``/openapi.json`` and ``/docs``.

This module builds the schema from **only the JSON API surface**
(``/api/*`` + ``/health``) — which is also exactly the contract native clients
consume. It is used both by:

- ``cli.py:run_export_openapi`` (writes ``clients/shared/openapi/*.json``), and
- each server's ``create_app`` (so ``/openapi.json`` + ``/docs`` work in the
  browser for interactive testing).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


def build_api_openapi(app: FastAPI) -> dict[str, Any]:
    """Return the OpenAPI schema for the JSON API surface only.

    Includes routes under ``/api/`` plus ``/health``; excludes HTML/binary
    routes (``/``, ``/video/stream``, ``/thumb``, ``/sw.js``, icons, …).
    """
    api_routes = [r for r in app.routes if isinstance(r, APIRoute) and (r.path.startswith("/api/") or r.path == "/health")]
    return get_openapi(
        title=app.title,
        version=getattr(app, "version", "0.1.0"),
        routes=api_routes,
    )


def install_filtered_openapi(app: FastAPI) -> None:
    """Make ``app.openapi()`` (and thus ``/openapi.json`` + ``/docs``) use the
    filtered schema. Safe/no-op on failure — never breaks server startup.
    """

    def _openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        try:
            app.openapi_schema = build_api_openapi(app)
        except Exception:
            logger.debug("Failed to build filtered OpenAPI schema", exc_info=True)
            app.openapi_schema = {"openapi": "3.1.0", "info": {"title": app.title, "version": "0"}, "paths": {}}
        return app.openapi_schema

    app.openapi = _openapi
