"""Update endpoint routing on each agent to point at the newest active version.

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


def az_rest(method: str, url: str, body: str | None = None):
    args = ["az", "rest", "--method", method, "--url", url,
            "--resource", "https://ai.azure.com"]
    if body is not None:
        args += ["--body", body, "--headers", "Content-Type=application/json"]
    return subprocess.run(args, capture_output=True, text=True, shell=True)


for a in AGENTS:
    r = az_rest("GET", f"{BASE}/agents/{a}/versions?api-version=2025-11-15-preview")
    if r.returncode != 0:
        print(f"{a}: list failed: {r.stderr.strip()[:200]}")
        continue
    versions = json.loads(r.stdout).get("data", [])
    target = next(
        (v for v in sorted(versions, key=lambda v: v.get("created_at", 0), reverse=True)
         if v.get("status") == "active" and TAG in v.get("definition", {}).get("image", "")),
        None,
    )
    if not target:
        print(f"{a}: no active version with tag {TAG}")
        continue
    target_version = target["version"]

    body = json.dumps({
        "agent_endpoint": {
            "version_selector": {
                "version_selection_rules": [
                    {"type": "FixedRatio", "agent_version": target_version, "traffic_percentage": 100}
                ]
            }
        }
    })
    r2 = az_rest("PATCH", f"{BASE}/agents/{a}?api-version=2025-11-15-preview", body=body)
    if r2.returncode == 0:
        print(f"{a}: routed 100% -> version {target_version}")
    else:
        print(f"{a}: PATCH failed: {(r2.stderr or r2.stdout).strip()[:300]}")
