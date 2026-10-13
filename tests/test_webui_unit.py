"""Run the webui vitest suite (`webui/test/*.test.ts`) from pytest.

Behaviour tests for ported TS modules — the Python string-presence tests
(test_streaming_player_ui.py) only prove code exists, these prove it works.
Skipped when npm or webui/node_modules (vitest) is missing, so a plain
Python-only checkout still passes.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from hometools.streaming.webui_build import WEBUI_DIR


def test_webui_vitest_suite():
    npm = shutil.which("npm")
    if npm is None:
        pytest.skip("npm not on PATH")
    if not (WEBUI_DIR / "node_modules" / "vitest").is_dir():
        pytest.skip("vitest not installed — run 'npm install' in webui/")
    try:
        proc = subprocess.run(
            [npm, "test", "--silent"],
            cwd=str(WEBUI_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.fail(f"vitest run failed to execute: {exc}")
    assert proc.returncode == 0, f"vitest failed:\n{proc.stdout[-4000:]}\n{proc.stderr[-2000:]}"


def test_webui_typecheck():
    """`tsc --noEmit`: catches missing imports / window typings in main.ts
    that the string-presence tests cannot see."""
    npx = shutil.which("npx")
    if npx is None:
        pytest.skip("npx not on PATH")
    if not (WEBUI_DIR / "node_modules" / "typescript").is_dir():
        pytest.skip("typescript not installed — run 'npm install' in webui/")
    try:
        proc = subprocess.run(
            [npx, "--no-install", "tsc", "--noEmit"],
            cwd=str(WEBUI_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.fail(f"tsc failed to execute: {exc}")
    assert proc.returncode == 0, f"tsc failed:\n{proc.stdout[-4000:]}\n{proc.stderr[-2000:]}"
