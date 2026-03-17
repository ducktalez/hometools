#!/usr/bin/env python
import sys
sys.path.insert(0, r"C:\Users\Simon\PycharmProjects\hometools\src")

from hometools.streaming.core.server_utils import render_media_page

html = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="waveform"
)

print("HTML LENGTH:", len(html))
print("Has btn-dl:", 'id="btn-dl"' in html)
print("Has initDownloadDB:", 'initDownloadDB' in html)

