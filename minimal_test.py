#!/usr/bin/env python
"""Minimal test."""
print("Starting...")
import sys
sys.path.insert(0, 'src')
print("Path added")

try:
    from hometools.streaming.core.server_utils import render_media_page
    print("Import successful")
    
    html = render_media_page(
        title="Videos",
        emoji="🎬",
        items_json="[]",
        media_element_tag="video",
        api_path="/api/video/items",
        item_noun="video",
        player_bar_style="waveform"
    )
    
    result = {
        'length': len(html),
        'has_btn_dl': 'id="btn-dl"' in html,
        'has_init_dl': 'initDownloadDB' in html
    }
    
    with open("tmp/result.txt", "w") as f:
        for k, v in result.items():
            f.write(f"{k}: {v}\n")
    
    print("Result written to tmp/result.txt")
    
except Exception as e:
    with open("tmp/error.txt", "w") as f:
        import traceback
        f.write(traceback.format_exc())
    print(f"Error: {e}")

