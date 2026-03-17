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

# Write to file
with open("tmp/test_output2.txt", "w") as f:
    f.write("HTML LENGTH: " + str(len(html)) + "\n")
    f.write("Has btn-dl: " + str('id="btn-dl"' in html) + "\n")
    f.write("Has initDownloadDB: " + str('initDownloadDB' in html) + "\n")
    
print("Done")

