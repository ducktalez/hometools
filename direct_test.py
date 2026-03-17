#!/usr/bin/env python
"""Direct test of render functions."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now test
def test_waveform():
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
    
    print("Test waveform:")
    print(f"  HTML length: {len(html)}")
    print(f"  Has btn-dl: {'id=\"btn-dl\"' in html}")
    print(f"  Has initDownloadDB: {'initDownloadDB' in html}")
    
    assert 'id="btn-dl"' in html, "btn-dl not found!"
    assert "initDownloadDB" in html, "initDownloadDB not found!"
    print("  ✓ PASSED")


def test_classic():
    from hometools.streaming.core.server_utils import render_media_page
    
    html = render_media_page(
        title="Videos",
        emoji="🎬",
        items_json="[]",
        media_element_tag="video",
        api_path="/api/video/items",
        item_noun="video",
        player_bar_style="classic"
    )
    
    print("\nTest classic:")
    print(f"  HTML length: {len(html)}")
    print(f"  Has btn-dl: {'id=\"btn-dl\"' in html}")
    print(f"  Has downloadMedia: {'downloadMedia' in html}")
    
    assert 'id="btn-dl"' in html, "btn-dl not found!"
    assert "downloadMedia" in html, "downloadMedia not found!"
    print("  ✓ PASSED")


if __name__ == "__main__":
    try:
        test_waveform()
        test_classic()
        print("\nAll tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

