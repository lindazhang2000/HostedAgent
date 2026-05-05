"""Inspect current endpoint routing for each agent.

Reads `AZURE_AI_PROJECT_ENDPOINT` from the environment.
"""
import json
import os
import subprocess
import sys

BASE = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
if not BASE:
    print("AZURE_AI_PROJECT_ENDPOINT must be set", file=sys.stderr)
    sys.exit(1)
AGENTS = ["cora", "cart-manager", "customer-loyalty", "interior-designer", "inventory"]

for a in AGENTS:
    r = subprocess.run(
        ["az", "rest", "--method", "GET",
         "--url", f"{BASE}/agents/{a}?api-version=2025-11-15-preview",
         "--resource", "https://ai.azure.com"],
        capture_output=True, text=True, shell=True,
    )
    if r.returncode != 0:
        print(f"{a}: ERROR {r.stderr.strip()[:200]}")
        continue
    data = json.loads(r.stdout)
    routing = data.get("endpoint_routing") or data.get("traffic") or data.get("routing") or {}
    print(f"=== {a} ===")
    print(json.dumps(data, indent=2))
    print()
