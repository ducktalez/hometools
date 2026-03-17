#!/usr/bin/env python
"""Test render functions directly without pytest infrastructure."""
import sys
sys.path.insert(0, 'src')

# Test 1: Waveform player bar with download button
from hometools.streaming.core.server_utils import render_media_page

print("Test 1: Waveform player bar")
html_waveform = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="waveform"
)

test1_pass = 'id="btn-dl"' in html_waveform and "initDownloadDB" in html_waveform
print(f"  Has btn-dl: {'✓' if 'id=\"btn-dl\"' in html_waveform else '✗'}")
print(f"  Has initDownloadDB: {'✓' if 'initDownloadDB' in html_waveform else '✗'}")
print(f"  Result: {'PASS' if test1_pass else 'FAIL'}")

# Test 2: Classic player bar with download button
print("\nTest 2: Classic player bar")
html_classic = render_media_page(
    title="Videos",
    emoji="🎬",
    items_json="[]",
    media_element_tag="video",
    api_path="/api/video/items",
    item_noun="video",
    player_bar_style="classic"
)

test2_pass = 'id="btn-dl"' in html_classic and "downloadMedia" in html_classic
print(f"  Has btn-dl: {'✓' if 'id=\"btn-dl\"' in html_classic else '✗'}")
print(f"  Has downloadMedia: {'✓' if 'downloadMedia' in html_classic else '✗'}")
print(f"  Result: {'PASS' if test2_pass else 'FAIL'}")

# Test 3: Service worker has offline cache
print("\nTest 3: Service worker offline cache")
from hometools.streaming.core.server_utils import render_pwa_service_worker

sw = render_pwa_service_worker()
test3_pass = all(x in sw for x in ["CACHE_NAME", "DOWNLOAD_CACHE", "destination === 'document'"])
print(f"  Has CACHE_NAME: {'✓' if 'CACHE_NAME' in sw else '✗'}")
print(f"  Has DOWNLOAD_CACHE: {'✓' if 'DOWNLOAD_CACHE' in sw else '✗'}")
print(f"  Has document dest handler: {'✓' if \"destination === 'document'\" in sw else '✗'}")
print(f"  Result: {'PASS' if test3_pass else 'FAIL'}")

# Test 4: Apps create successfully
print("\nTest 4: App creation")
try:
    from hometools.streaming.audio.server import create_app as create_audio_app
    from hometools.streaming.video.server import create_app as create_video_app
    audio_app = create_audio_app()
    video_app = create_video_app()
    test4_pass = True
    print(f"  Audio app created: ✓")
    print(f"  Video app created: ✓")
except Exception as e:
    test4_pass = False
    print(f"  Error: {e}")
print(f"  Result: {'PASS' if test4_pass else 'FAIL'}")

# Test 5: FastAPI TestClient works
print("\nTest 5: FastAPI TestClient")
try:
    from fastapi.testclient import TestClient
    from hometools.streaming.audio.server import create_app as create_audio_app
    from hometools.streaming.video.server import create_app as create_video_app
    
    audio_app = create_audio_app()
    video_app = create_video_app()
    
    audio_client = TestClient(audio_app)
    video_client = TestClient(video_app)
    
    audio_health = audio_client.get("/health")
    video_health = video_client.get("/health")
    
    test5_pass = audio_health.status_code == 200 and video_health.status_code == 200
    print(f"  Audio /health: {audio_health.status_code} {'✓' if audio_health.status_code == 200 else '✗'}")
    print(f"  Video /health: {video_health.status_code} {'✓' if video_health.status_code == 200 else '✗'}")
    
    # Test manifest
    audio_manifest = audio_client.get("/manifest.json")
    video_manifest = video_client.get("/manifest.json")
    
    manifest_pass = audio_manifest.status_code == 200 and video_manifest.status_code == 200
    print(f"  Audio /manifest.json: {audio_manifest.status_code} {'✓' if audio_manifest.status_code == 200 else '✗'}")
    print(f"  Video /manifest.json: {video_manifest.status_code} {'✓' if video_manifest.status_code == 200 else '✗'}")
    
    test5_pass = test5_pass and manifest_pass
except Exception as e:
    test5_pass = False
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

print(f"  Result: {'PASS' if test5_pass else 'FAIL'}")

# Summary
print("\n" + "="*50)
all_pass = test1_pass and test2_pass and test3_pass and test4_pass and test5_pass
print(f"Overall: {'ALL TESTS PASS ✓' if all_pass else 'SOME TESTS FAIL ✗'}")
sys.exit(0 if all_pass else 1)

