"""Quick check for queue issues."""

import os
import sys

os.environ.setdefault("HOMETOOLS_AUDIO_LIBRARY_DIR", "C:/tmp/test")
os.environ.setdefault("HOMETOOLS_VIDEO_LIBRARY_DIR", "C:/tmp/test")

from hometools.streaming.core.server_utils import render_base_css, render_media_page

css = render_base_css()
html = render_media_page(
    title="Test",
    emoji="X",
    items_json="[]",
    media_element_tag="audio",
    api_path="/api/items",
    item_noun="track",
    enable_shuffle=True,
    enable_lyrics=True,
    enable_playlists=True,
)

out = []
out.append(f"queue-panel in HTML: {html.count('queue-panel')}")
out.append(f"queue-body in HTML: {html.count('queue-body')}")
out.append(f".queue-panel.visible in CSS: {'.queue-panel.visible' in css}")

# Check body overflow
out.append(f"body overflow:hidden in CSS: {'overflow: hidden' in css}")

# Check player-bar position
idx_pb = css.find(".player-bar {")
if idx_pb >= 0:
    end = css.find("}", idx_pb)
    out.append(f"player-bar CSS: {css[idx_pb : end + 1]}")

# Check queue-panel CSS
idx_qp = css.find(".queue-panel {")
if idx_qp >= 0:
    end = css.find("}", idx_qp)
    out.append(f"queue-panel CSS: {css[idx_qp : end + 1]}")

idx_qpv = css.find(".queue-panel.visible")
if idx_qpv >= 0:
    end = css.find("}", idx_qpv)
    out.append(f"queue-panel.visible CSS: {css[idx_qpv : end + 1]}")

# Check HTML structure around queue-panel
idx_qp_html = html.find('id="queue-panel"')
if idx_qp_html >= 0:
    snippet = html[max(0, idx_qp_html - 200) : idx_qp_html + 200]
    out.append(f"HTML around queue-panel:\n{snippet}")

# Check if dequeueNext is in the JS
out.append(f"dequeueNext in HTML: {'dequeueNext' in html}")
out.append(f"player ended + dequeueNext: {'if (!dequeueNext())' in html}")

with open("_check_queue_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

sys.exit(0)
