#!/usr/bin/env python3
from hometools.streaming.core.server_utils import render_player_js

js = render_player_js(api_path="/api/video/items", item_noun="video", file_emoji="🎬", player_bar_style="waveform")

# Check for key strings
checks = {
    'id="btn-dl"': 'id="btn-dl"' in js,
    'initDownloadDB': 'initDownloadDB' in js,
    'downloadMedia': 'downloadMedia' in js,
    'deleteDownload': 'deleteDownload' in js,
    'btn-play': 'id="btn-play"' in js or 'btn-play' in js,
    'INITIAL': 'INITIAL' in js,
    'playTrack': 'playTrack' in js,
}

print("String checks:")
for key, result in checks.items():
    print(f"  {key}: {result}")

print(f"\nTotal JavaScript length: {len(js)} characters")
print(f"\nFirst 500 characters:")
print(js[:500])
print(f"\n... (truncated) ...\n")
print(f"Last 500 characters:")
print(js[-500:])

# Write to file for inspection
with open('/tmp/rendered_js.txt', 'w', encoding='utf-8') as f:
    f.write(js)
print("\nFull output written to /tmp/rendered_js.txt")

