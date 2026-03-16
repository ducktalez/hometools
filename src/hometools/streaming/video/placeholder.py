"""Planned video streaming area.

This module intentionally contains only a placeholder so the repository can grow
into a matching video service later without mixing concerns into the current
Audio MVP.
"""

from __future__ import annotations


def describe_video_streaming_scope() -> dict[str, object]:
    """Return the planned scope for the future video streaming component."""
    return {
        "status": "planned",
        "implemented": False,
        "next_steps": [
            "catalog indexing",
            "metadata lookup reuse",
            "stream endpoint",
            "transcoding evaluation",
        ],
    }

