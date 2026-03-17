from hometools.streaming.core.server_utils import render_pwa_service_worker

sw = render_pwa_service_worker()
with open("/tmp/sw_output.txt", "w") as f:
    f.write(sw)

print("Written to /tmp/sw_output.txt")
print("Length:", len(sw))
print("Contains serveFromIndexedDB:", "serveFromIndexedDB" in sw)
print("Contains FETCH_FROM_INDEXEDDB:", "FETCH_FROM_INDEXEDDB" in sw)
print("Contains DOWNLOAD_CACHE:", "DOWNLOAD_CACHE" in sw)
