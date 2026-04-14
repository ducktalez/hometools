"""Analyze structure of server_utils.py."""

import re

with open("src/hometools/streaming/core/server_utils.py", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total: {len(lines)} lines\n")

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("def ") or stripped.startswith("class ") or (stripped.startswith("# ---") and len(stripped) > 10):
        print(f"  {i:5d} | {stripped[:120]}")
    elif re.match(r"^SVG_[A-Z]", line):
        print(f"  {i:5d} | {line[:80].rstrip()} ...")
