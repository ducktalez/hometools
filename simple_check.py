#!/usr/bin/env python
"""Import and run a single simple test to check if everything works."""

# First, test if we can import the functions
print("=== Testing Imports ===")

try:
    from hometools.streaming.core.server_utils import render_media_page
    print("✓ render_media_page imported")
except Exception as e:
    print(f"✗ Failed to import render_media_page: {e}")
    exit(1)

try:
    from fastapi.testclient import TestClient
    print("✓ TestClient imported")
except Exception as e:
    print(f"✗ Failed to import TestClient: {e}")
    exit(1)

try:
    from hometools.streaming.audio.server import create_app as create_audio_app
    from hometools.streaming.video.server import create_app as create_video_app
    print("✓ Both create_app functions imported")
except Exception as e:
    print(f"✗ Failed to import create_app functions: {e}")
    exit(1)

# Now test render_media_page
print("\n=== Testing render_media_page ===")

html = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="waveform"
)

print(f"HTML generated: {len(html)} bytes")
print(f"Contains 'id=\"btn-dl\"': {'id=\"btn-dl\"' in html}")
print(f"Contains 'initDownloadDB': {'initDownloadDB' in html}")

if 'id="btn-dl"' in html and 'initDownloadDB' in html:
    print("✓ Waveform test would PASS")
else:
    print("✗ Waveform test would FAIL")

# Test classic
html_classic = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="classic"
)

print(f"\nClassic HTML generated: {len(html_classic)} bytes")
print(f"Contains 'id=\"btn-dl\"': {'id=\"btn-dl\"' in html_classic}")
print(f"Contains 'downloadMedia': {'downloadMedia' in html_classic}")

if 'id="btn-dl"' in html_classic and 'downloadMedia' in html_classic:
    print("✓ Classic test would PASS")
else:
    print("✗ Classic test would FAIL")

# Test app creation
print("\n=== Testing App Creation ===")

try:
    audio_app = create_audio_app()
    print("✓ Audio app created")
except Exception as e:
    print(f"✗ Failed to create audio app: {e}")
    exit(1)

try:
    video_app = create_video_app()
    print("✓ Video app created")
except Exception as e:
    print(f"✗ Failed to create video app: {e}")
    exit(1)

# Test TestClient with audio app
print("\n=== Testing TestClient ===")

try:
    audio_client = TestClient(audio_app)
    print("✓ Audio TestClient created")
    
    response = audio_client.get("/health")
    print(f"✓ Audio /health returned {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Audio health test would PASS")
    else:
        print(f"✗ Audio health test would FAIL (expected 200, got {response.status_code})")
        
except Exception as e:
    print(f"✗ Failed TestClient test: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

try:
    video_client = TestClient(video_app)
    print("✓ Video TestClient created")
    
    response = video_client.get("/health")
    print(f"✓ Video /health returned {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Video health test would PASS")
    else:
        print(f"✗ Video health test would FAIL (expected 200, got {response.status_code})")
        
except Exception as e:
    print(f"✗ Failed Video TestClient test: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n=== All Basic Tests Completed ===")
print("If all above show ✓, then pytest should pass!")

