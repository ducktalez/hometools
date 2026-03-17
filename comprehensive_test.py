#!/usr/bin/env python
"""Direct test runner - calls pytest and captures all output."""
import subprocess
import sys
import json

# First, verify httpx is available
try:
    import httpx
    httpx_available = True
    httpx_version = httpx.__version__
except ImportError:
    httpx_available = False
    httpx_version = None

# Try to import fastapi TestClient
try:
    from fastapi.testclient import TestClient
    testclient_available = True
except ImportError as e:
    testclient_available = False
    testclient_error = str(e)

# Write environment info
result_data = {
    "httpx_available": httpx_available,
    "httpx_version": httpx_version,
    "testclient_available": testclient_available,
}

# Now run tests
test_commands = [
    ["tests/test_offline_downloads.py::TestDownloadUI", "-xvs"],
    ["tests/test_feature_parity.py::TestServerEndpointParity", "-xvs"],
]

test_results = []

for test_path, *args in test_commands:
    cmd = [sys.executable, "-m", "pytest", test_path] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd="."
    )
    
    test_results.append({
        "test": test_path,
        "return_code": result.returncode,
        "stdout_lines": result.stdout.count('\n'),
        "stderr_lines": result.stderr.count('\n'),
        "success": result.returncode == 0,
    })

result_data["tests"] = test_results

# Write results
with open("tmp/test_run_report.json", "w") as f:
    json.dump(result_data, f, indent=2)

# Also write raw output
with open("tmp/test_run_detailed.txt", "w") as f:
    f.write(f"httpx available: {httpx_available}\n")
    f.write(f"httpx version: {httpx_version}\n")
    f.write(f"TestClient available: {testclient_available}\n")
    f.write("\n" + "="*80 + "\n")
    
    for test_path, *args in test_commands:
        cmd = [sys.executable, "-m", "pytest", test_path] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="."
        )
        
        f.write(f"\nTest: {test_path}\n")
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"Return code: {result.returncode}\n")
        f.write(f"\nSTDOUT:\n{result.stdout}\n")
        f.write(f"\nSTDERR:\n{result.stderr}\n")
        f.write("\n" + "="*80 + "\n")

print("Test run complete. Results written to tmp/test_run_report.json and tmp/test_run_detailed.txt")

