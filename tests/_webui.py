"""Helper: TypeScript sources of the player UI (``streaming/core/webui/src``)."""

from __future__ import annotations

from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src" / "hometools" / "streaming" / "core" / "webui" / "src"


def all_ts() -> str:
    """All player TS sources concatenated (for string-presence asserts)."""
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(_SRC.glob("*.ts")))
