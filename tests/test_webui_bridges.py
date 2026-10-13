"""Parity: every `window.<name>` the legacy player JS calls must be bridged in webui main.ts."""

from __future__ import annotations

import re
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1] / "src" / "hometools" / "streaming" / "core"
_JS_DIR = _CORE / "server_utils" / "player_js"
_MAIN_TS = _CORE / "webui" / "src" / "main.ts"


def test_window_bridges_defined_in_main_ts():
    ts = _MAIN_TS.read_text(encoding="utf-8")
    bridged = set(re.findall(r"^window\.(\w+)\s*=", ts, re.M))
    used: dict[str, str] = {}
    for f in _JS_DIR.glob("*.py"):
        src = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
        for name in re.findall(r"\bwindow\.(_\w+)\s*\(", src):
            used.setdefault(name, f.name)
    missing = {n: f for n, f in used.items() if n not in bridged}
    assert not missing, f"window bridges missing in main.ts: {missing}"
