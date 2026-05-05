"""Get per-agent identities and assign Azure AI User role at project scope.

Reads configuration from environment variables so the script is portable:

  AZURE_AI_PROJECT_ENDPOINT  e.g. https://<foundry>.cognitiveservices.azure.com/api/projects/<project>
  AZURE_SUBSCRIPTION_ID      target subscription (defaults to current `az account show`)
  AZURE_RESOURCE_GROUP       resource group containing the Foundry account (default: hostedagents)
"""
import json
import os
import subprocess
import sys
from urllib.parse import urlparse

BASE = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
if not BASE:
    print("AZURE_AI_PROJECT_ENDPOINT must be set", file=sys.stderr)
    sys.exit(1)

# Parse account/project from the endpoint:
# https://<account>.cognitiveservices.azure.com/api/projects/<project>
parsed = urlparse(BASE)
ACCOUNT = parsed.hostname.split(".", 1)[0] if parsed.hostname else ""
PROJECT = BASE.rstrip("/").rsplit("/", 1)[-1]

AGENTS = ["cora", "cart-manager", "customer-loyalty", "interior-designer", "inventory"]
RG = os.environ.get("AZURE_RESOURCE_GROUP", "hostedagents")
SUBSCRIPTION = os.environ.get("AZURE_SUBSCRIPTION_ID") or subprocess.run(
    ["az", "account", "show", "--query", "id", "-o", "tsv"],
    capture_output=True, text=True, shell=True,
).stdout.strip()
# Azure AI User role definition ID (built-in)
ROLE = "53ca6127-db72-4b80-b1b0-d745d6d5456d"

# Project-scope resource ID
SCOPE = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{RG}"
    f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT}"
    f"/projects/{PROJECT}"
)


def az(*args, capture=True):
    r = subprocess.run(["az", *args], capture_output=capture, text=True, shell=True)
    return r


for a in AGENTS:
    r = az("rest", "--method", "GET",
           "--url", f"{BASE}/agents/{a}/versions?api-version=2025-11-15-preview",
           "--resource", "https://ai.azure.com")
    if r.returncode != 0:
        print(f"{a}: failed to fetch versions: {r.stderr.strip()[:200]}")
        continue
    versions = json.loads(r.stdout).get("data", [])
    active = [v for v in versions if v.get("status") == "active"]
    if not active:
        print(f"{a}: no active versions")
        continue
    latest = max(active, key=lambda v: v.get("created_at", 0))
    pid = latest.get("instance_identity", {}).get("principal_id")
    if not pid:
        print(f"{a}: no principal_id on latest version")
        continue
    print(f"{a}: principal_id={pid}")
    # Assign Azure AI User at project scope
    rr = az("role", "assignment", "create",
            "--assignee-object-id", pid,
            "--assignee-principal-type", "ServicePrincipal",
            "--role", ROLE,
            "--scope", SCOPE)
    out = (rr.stdout or "") + (rr.stderr or "")
    if rr.returncode == 0:
        print(f"  assigned Azure AI User -> {a}")
    elif "already exists" in out.lower() or "RoleAssignmentExists" in out:
        print(f"  already assigned -> {a}")
    else:
        print(f"  FAILED: {out.strip()[:300]}")
