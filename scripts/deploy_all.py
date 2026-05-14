"""Build, push, and register every Zava hosted agent.

Usage:
  python scripts/deploy_all.py

Env vars:
  AZURE_CONTAINER_REGISTRY_ENDPOINT  e.g. <registry>.azurecr.io
  AZURE_AI_PROJECT_ENDPOINT          full https://...cognitiveservices.azure.com/api/projects/{name}
  AZURE_BUILD_TAG                    optional (default: git short sha)
  BUILD_MODE                         'acr' (default, server-side) or 'docker' (local)

For each agents/<name>/:
  1. build & push image (ACR build or local docker)
  2. AIProjectClient.agents.create_version(definition=HostedAgentDefinition(...))
"""

from __future__ import annotations

import os
import string
import subprocess
import sys
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentProtocol,
    ContainerConfiguration,
    HostedAgentDefinition,
    ProtocolVersionRecord,
)
from azure.identity import DefaultAzureCredential

REPO = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO / "agents"


def _run(*args: str, cwd: Path | None = None) -> None:
    print(">", " ".join(args))
    # shell=True on Windows so az.cmd / docker.exe resolve via PATH.
    subprocess.run(args, check=True, cwd=cwd, shell=(os.name == "nt"))


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


def _image_exists(registry: str, name: str, tag: str) -> bool:
    try:
        out = subprocess.run(
            ["az", "acr", "repository", "show-tags",
             "--name", registry, "--repository", name,
             "--query", f"contains(@, '{tag}')", "-o", "tsv"],
            capture_output=True, text=True, check=True, shell=(os.name == "nt"),
        )
        return out.stdout.strip().lower() == "true"
    except Exception:
        return False


def build_and_push(name: str, tag: str, acr: str) -> str:
    """Build & push the image. ACR build (default) or local Docker."""
    image = f"{acr}/{name}:{tag}"
    registry = acr.split(".")[0]
    mode = os.environ.get("BUILD_MODE", "acr").lower()
    if mode == "acr":
        if _image_exists(registry, name, tag):
            print(f"  image {name}:{tag} already in ACR — skipping build")
            return image
        rg = os.environ.get("AZURE_RESOURCE_GROUP", "hostedagents")
                      _run(
            "az", "acr", "build",
            "--resource-group", rg,
            "--registry", registry,
            "--image", f"{name}:{tag}",
            "--source-acr-auth-id", "[caller]",
            "--file", f"agents/{name}/Dockerfile",
            ".",
            cwd=REPO,
        )
    else:
        _run("docker", "build", "-f", f"agents/{name}/Dockerfile", "-t", image, ".", cwd=REPO)
        _run("docker", "push", image)
    return image


def register_version(
    client: AIProjectClient,
    name: str,
    manifest: dict,
    image: str,
) -> None:
    container = manifest["container"]
    cpu = str(container.get("resources", {}).get("cpu", "0.5"))
    memory = str(container.get("resources", {}).get("memory", "1Gi"))

    env_vars = {
        e["name"]: _expand(str(e.get("value", "")))
        for e in (manifest.get("env") or [])
    }

    proto_map = {
        "responses": AgentProtocol.RESPONSES,
        "invocations": AgentProtocol.INVOCATIONS,
        "activity_protocol": AgentProtocol.ACTIVITY_PROTOCOL,
    }
    protocols = [
        ProtocolVersionRecord(protocol=proto_map[p], version="1.0.0")
        for p in manifest.get("protocols", ["responses"])
    ]

    definition = HostedAgentDefinition(
        image=image,
        container_protocol_versions=protocols,
        cpu=cpu,
        memory=memory,
        environment_variables=env_vars,
    )

    agent = client.agents.create_version(
        agent_name=name,
        description=manifest.get("description", ""),
        definition=definition,
    )
    print(f"  registered {name}@{getattr(agent, 'version', '?')} (id={getattr(agent, 'id', '?')})")


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

    client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    with client:
        only = {n.strip() for n in os.environ.get("AGENT_FILTER", "").split(",") if n.strip()}
        for agent_dir in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
            name = agent_dir.name
            if only and name not in only:
                continue
            print(f"=== {name} ===")
            manifest = yaml.safe_load(
                (agent_dir / "agent.yaml").read_text(encoding="utf-8")
            )
            image = build_and_push(name, tag, acr)
            register_version(client, name, manifest, image)
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
