"""Debug script to check queue panel HTML generation."""

import os
import re

os.environ.setdefault("HOMETOOLS_AUDIO_LIBRARY_DIR", "C:/tmp/test")
os.environ.setdefault("HOMETOOLS_VIDEO_LIBRARY_DIR", "C:/tmp/test")

from hometools.streaming.core.server_utils import render_media_page

html = render_media_page(
    title="Test",
    emoji="🎵",
    items_json="[]",
    media_element_tag="audio",
    api_path="/api/items",
    item_noun="track",
    enable_shuffle=True,
    enable_lyrics=True,
    enable_playlists=True,
)

print("queue-body count:", html.count("queue-body"))
print("queue-panel count:", html.count("queue-panel"))
print("_queueBody count in JS:", html.count("_queueBody"))
print("_queuePanel count in JS:", html.count("_queuePanel"))

idx = html.find('id="queue-body"')
print("queue-body found at char index:", idx)
if idx >= 0:
    snippet = html[max(0, idx - 150) : idx + 150]
    print("--- SNIPPET around queue-body ---")
    print(snippet)
    print("--- END ---")

# Check JS: find renderQueuePanel function
js_idx = html.find("function renderQueuePanel")
print("\nrenderQueuePanel found at:", js_idx)
if js_idx >= 0:
    print(html[js_idx : js_idx + 400])

# Check JS: _queueBody definition
qb_js = html.find("var _queueBody")
print("\nvar _queueBody at:", qb_js)
if qb_js >= 0:
    print(html[qb_js : qb_js + 100])

# Check order: does _queueBody var come BEFORE the queue-body DOM element?
qb_dom = html.find('id="queue-body"')
print("\n_queueBody JS var at:", qb_js, "| queue-body DOM at:", qb_dom)
if qb_js >= 0 and qb_dom >= 0:
    if qb_js < qb_dom:
        print("WARNING: JS variable defined BEFORE DOM element!")
    else:
        print("OK: DOM element exists before JS variable.")

# Extract just the JS from the <script> tag

scripts = re.findall(r"<script>(.+?)</script>", html, re.DOTALL)
print(f"Number of <script> tags with inline JS: {len(scripts)}")
if scripts:
    js = scripts[-1]  # The main JS is the last one
    print(f"JS length: {len(js)} chars")

    # Check if _userQueue is used in the same scope as renderQueuePanel
    # Find all function declarations
    funcs = re.findall(r"function\s+(\w+)", js)
    print(f"\nTop-level functions found: {len(funcs)}")

    # Check for any 'var _userQueue' redeclaration
    redecls = [m.start() for m in re.finditer(r"var _userQueue", js)]
    print(f"_userQueue declarations: {len(redecls)} at positions: {redecls}")

    # Check for any syntax that could shadow _userQueue
    let_decls = [m.start() for m in re.finditer(r"let _userQueue", js)]
    const_decls = [m.start() for m in re.finditer(r"const _userQueue", js)]
    print(f"let _userQueue: {len(let_decls)}, const _userQueue: {len(const_decls)}")

    # Check context around addToQueue to see if it accesses _userQueue
    aq_idx = js.find("function addToQueue")
    if aq_idx >= 0:
        print("\naddToQueue function:")
        print(js[aq_idx : aq_idx + 500])

    # Check if there are any try-catch blocks that might swallow errors
    # Check for 'ended' event listener
    ended_idx = js.find("player.addEventListener('ended'")
    if ended_idx >= 0:
        print("\nplayer ended handler:")
        print(js[ended_idx : ended_idx + 200])

    # Write JS to file for manual inspection
    with open("_debug_queue_js.txt", "w", encoding="utf-8") as f:
        f.write(js)
    print("\nJS written to _debug_queue_js.txt")
