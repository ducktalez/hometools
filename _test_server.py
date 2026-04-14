"""Quick test to see if the video server starts correctly."""

import sys
import traceback

print("=== Test Video Server Start ===", flush=True)

try:
    print("1. Importing create_app...", flush=True)
    from hometools.streaming.video.server import create_app

    print("2. Import OK", flush=True)

    print("3. Creating app...", flush=True)
    app = create_app()
    print(f"4. App created: {app}", flush=True)

    print("5. Importing uvicorn...", flush=True)
    import uvicorn

    print("6. Starting uvicorn on port 8005...", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="info")
except Exception:
    traceback.print_exc()
    sys.exit(1)
