"""Build, push, and register every Zava hosted agent.

Usage (after `az login`, with the resource group + Foundry project + ACR
already provisioned by infra/main.bicep):

  python scripts/deploy_all.py

Reads env vars (set via `azd env set` or your shell):
  AZURE_CONTAINER_REGISTRY_ENDPOINT  e.g. crh2aa4vjgovzru.azurecr.io
  AZURE_AI_PROJECT_ENDPOINT          full /api/projects/{project} URL
  AZURE_BUILD_TAG                    optional, defaults to git short sha or 'latest'

For each agent under agents/<name>/:
  1. docker build -t {acr}/{name}:{tag}
  2. docker push
  3. AIProjectClient.agents.create_version(ContainerAgentDefinition(...))
"""

from __future__ import annotations

import os
import string
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO / "agents"


def _run(*args: str, cwd: Path | None = None) -> None:
    print(">", " ".join(args))
    subprocess.run(args, check=True, cwd=cwd)


def _short_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, cwd=REPO,
        )
        return out.stdout.strip() or "latest"
    except Exception:
        return "latest"


def _expand(value: str) -> str:
    return string.Template(value).safe_substitute(os.environ)


def build_and_push(name: str, tag: str, acr: str) -> str:
    image = f"{acr}/{name}:{tag}"
    # Build context = repo root so Dockerfile can COPY shared/ + agents/<name>/.
    _run("docker", "build", "-f", f"agents/{name}/Dockerfile", "-t", image, ".", cwd=REPO)
    _run("docker", "push", image)
    return image


def register_version(name: str, manifest: dict, project_endpoint: str) -> None:
    # Imported lazily so the build step doesn't require the SDK.
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import (
        ContainerAgentDefinition,
        ContainerProtocolVersion,
        ContainerResources,
    )
    from azure.identity import DefaultAzureCredential

    container = manifest["container"]
    env_vars = [
        {"name": e["name"], "value": _expand(str(e.get("value", "")))}
        for e in (manifest.get("env") or [])
    ]
    protocols = [
        ContainerProtocolVersion(name=p)
        for p in manifest.get("protocols", ["responses"])
    ]

    client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    with client:
        agent = client.agents.create_version(
            agent_name=name,
            description=manifest.get("description", ""),
            definition=ContainerAgentDefinition(
                image=_expand(container["image"]),
                port=int(container.get("port", 8088)),
                resources=ContainerResources(
                    cpu=float(container.get("resources", {}).get("cpu", 0.5)),
                    memory=container.get("resources", {}).get("memory", "1Gi"),
                ),
                container_protocol_versions=protocols,
                environment_variables=env_vars,
            ),
        )
        print(f"  registered {name}@{agent.version} (id={agent.id})")
        print(
            f"  endpoint: {project_endpoint}/agents/{name}"
            "/endpoint/protocols/openai/v1/responses"
        )


def main() -> int:
    acr = os.environ.get("AZURE_CONTAINER_REGISTRY_ENDPOINT")
    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not acr or not project_endpoint:
        print(
            "Set AZURE_CONTAINER_REGISTRY_ENDPOINT and AZURE_AI_PROJECT_ENDPOINT.",
            file=sys.stderr,
        )
        return 1

    tag = os.environ.get("AZURE_BUILD_TAG") or _short_sha()
    os.environ["AZURE_BUILD_TAG"] = tag
    print(f"Using tag: {tag}\n")

    for agent_dir in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        name = agent_dir.name
        print(f"=== {name} ===")
        manifest = yaml.safe_load((agent_dir / "agent.yaml").read_text(encoding="utf-8"))
        build_and_push(name, tag, acr)
        register_version(name, manifest, project_endpoint)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
