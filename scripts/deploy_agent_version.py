"""
Register / update the hosted agent version in Foundry.

Run after `azd deploy` has pushed the image to ACR. Reads agent.yaml,
substitutes ${AZURE_*} variables from the environment, and calls
AIProjectClient.agents.create_version with a ContainerAgentDefinition.
"""

from __future__ import annotations

import os
import string
import sys

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ContainerAgentDefinition,
    ContainerProtocolVersion,
    ContainerResources,
)
from azure.identity import DefaultAzureCredential


def _expand(value: str) -> str:
    """Replace ${VAR} placeholders with environment values."""
    return string.Template(value).safe_substitute(os.environ)


def main() -> int:
    project_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get(
        "AZURE_AI_PROJECT_ENDPOINT"
    )
    if not project_endpoint:
        print("FOUNDRY_PROJECT_ENDPOINT is required", file=sys.stderr)
        return 1

    with open("agent.yaml", "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    name = manifest["name"]
    description = manifest.get("description", "")
    container = manifest["container"]
    image = _expand(container["image"])
    port = int(container.get("port", 8088))
    cpu = float(container.get("resources", {}).get("cpu", 0.5))
    memory = container.get("resources", {}).get("memory", "1Gi")

    env = [
        {"name": e["name"], "value": _expand(str(e.get("value", "")))}
        for e in (manifest.get("env") or [])
    ]
    protocols = [
        ContainerProtocolVersion(name=p) for p in manifest.get("protocols", ["responses"])
    ]

    client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    with client:
        agent = client.agents.create_version(
            agent_name=name,
            description=description,
            definition=ContainerAgentDefinition(
                image=image,
                port=port,
                resources=ContainerResources(cpu=cpu, memory=memory),
                container_protocol_versions=protocols,
                environment_variables=env,
            ),
        )
        print(f"Registered hosted agent {name}@{agent.version} (id={agent.id})")
        print(
            "Endpoint: "
            f"{project_endpoint}/agents/{name}/endpoint/protocols/openai/v1/responses"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
