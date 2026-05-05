"""Check status of latest versions for all hosted agents.

Environment variables:
  AZURE_AI_PROJECT_ENDPOINT  required
  AZURE_BUILD_TAG            tag substring to match in the image (required)
"""
import json
import os
import subprocess
import sys

BASE = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
TAG = os.environ.get("AZURE_BUILD_TAG")
if not BASE or not TAG:
    print("AZURE_AI_PROJECT_ENDPOINT and AZURE_BUILD_TAG must be set", file=sys.stderr)
    sys.exit(1)
AGENTS = ["cora", "cart-manager", "customer-loyalty", "interior-designer", "inventory"]

for a in AGENTS:
    r = subprocess.run(
        ["az", "rest", "--method", "GET",
         "--url", f"{BASE}/agents/{a}/versions?api-version=2025-11-15-preview",
         "--resource", "https://ai.azure.com"],
        capture_output=True, text=True, shell=True,
    )
    if r.returncode != 0:
        print(f"{a:<20} ERROR: {r.stderr.strip()[:200]}")
        continue
    versions = json.loads(r.stdout).get("data", [])
    matching = [v for v in versions if TAG in v.get("definition", {}).get("image", "")]
    if not matching:
        print(f"{a:<20} no version with tag {TAG}")
        continue
    for v in matching:
        print(f"{a:<20} version={v['version']:<3} status={v['status']:<10} image={v['definition']['image']}")
