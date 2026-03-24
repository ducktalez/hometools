"""Quick debug check for player-bar rendering."""

from pathlib import Path

from hometools.streaming.core.server_utils import render_media_page

out = Path(__file__).parent / "_debug_output.txt"
lines = []

html = render_media_page(
    title="test",
    emoji="X",
    items_json="[]",
    media_element_tag="video",
    extra_css="",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="classic",
)

# Check player-bar is in HTML
idx = html.find("player-bar")
lines.append(f"player-bar found at index: {idx}")
if idx >= 0:
    lines.append(html[idx - 10 : idx + 500])
    lines.append("---")

# Check video element
vidx = html.find("<video")
lines.append(f"\nvideo element found at index: {vidx}")

# Check JS: playerBar removal of view-hidden
js_idx = html.find("playerBar.classList.remove")
lines.append(f"\nplayerBar.classList.remove found at index: {js_idx}")

# Check progress-bar in both
lines.append(f"\nclassic: progress-bar found: {'progress-bar' in html}")
lines.append(f"classic: waveform-canvas found: {'waveform-canvas' in html}")
lines.append(f"classic: progress-track found: {'progress-track' in html}")
lines.append(f"classic: progress-wrap found: {'progress-wrap' in html}")

# Now check waveform style
html2 = render_media_page(
    title="test",
    emoji="X",
    items_json="[]",
    media_element_tag="video",
    extra_css="",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="waveform",
)
lines.append(f"\nwaveform: progress-bar found: {'progress-bar' in html2}")
lines.append(f"waveform: waveform-canvas found: {'waveform-canvas' in html2}")
lines.append(f"waveform: progress-track found: {'progress-track' in html2}")

# Check that the player-bar contains the progress elements
player_bar_start = html.find("player-bar classic")
if player_bar_start >= 0:
    player_bar_end = html.find("</div>", player_bar_start + 500)
    lines.append("\n--- CLASSIC PLAYER BAR HTML (full) ---")
    lines.append(html[player_bar_start - 10 : player_bar_end + 50])

out.write_text("\n".join(lines), encoding="utf-8")
