#!/usr/bin/env python
"""Run a single test and capture output."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", 
     "tests/test_offline_downloads.py::TestDownloadUI::test_download_button_in_waveform",
     "-xvs"
    ],
    cwd=".",
    capture_output=True,
    text=True,
    timeout=30
)

# Write to file
with open("tmp/test_single_output.txt", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn code: {result.returncode}")

# Also print
print(f"Test completed with return code {result.returncode}")
print("Output written to tmp/test_single_output.txt")

