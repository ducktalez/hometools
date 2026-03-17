#!/usr/bin/env python
"""Test render_media_page directly."""

from hometools.streaming.core.server_utils import render_media_page

# Test waveform style
html_waveform = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="waveform"
)

print("=" * 80)
print("WAVEFORM STYLE TEST")
print("=" * 80)
print(f"Contains 'id=\"btn-dl\"': {'id=\"btn-dl\"' in html_waveform}")
print(f"Contains 'initDownloadDB': {'initDownloadDB' in html_waveform}")
print()

# Test classic style
html_classic = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="classic"
)

print("=" * 80)
print("CLASSIC STYLE TEST")
print("=" * 80)
print(f"Contains 'id=\"btn-dl\"': {'id=\"btn-dl\"' in html_classic}")
print(f"Contains 'downloadMedia': {'downloadMedia' in html_classic}")
print()

# Try to find where btn-dl is in waveform
if 'id="btn-dl"' in html_waveform:
    idx = html_waveform.find('id="btn-dl"')
    print("Found in waveform at position", idx)
    print("Context:", html_waveform[max(0, idx-100):idx+100])
else:
    print("NOT FOUND in waveform!")

