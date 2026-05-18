"""Inspect the audit log for anomalies."""

import json
from pathlib import Path

lines = Path(r"C:\Users\Simon\PycharmProjects\hometools\.hometools-audit\audit.jsonl").read_text(encoding="utf-8").splitlines()
print("Total entries:", len(lines))
print("--- Last 5 entries ---")
for line in lines[-5:]:
    e = json.loads(line)
    ts = e.get("timestamp", "")[:16]
    action = e.get("action", "?")
    path = e.get("path", "?")
    server = e.get("server", "?")
    print(f"  {ts} | {action} | {server} | {path[:60]}")

print("--- Unique servers ---")
servers = set(json.loads(l).get("server", "MISSING") for l in lines if l.strip())
print(servers)
print("--- Unique actions ---")
actions = set(json.loads(l).get("action", "MISSING") for l in lines if l.strip())
print(actions)
print("--- Entries with null/missing path ---")
for line in lines:
    if not line.strip():
        continue
    e = json.loads(line)
    if not e.get("path"):
        print("  BAD ENTRY:", e)
print("--- Done ---")
