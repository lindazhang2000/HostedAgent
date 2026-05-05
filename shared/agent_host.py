"""Shared agent factory used by every hosted-agent container.

Each `agents/<name>/main.py` imports `build_agent`/`serve` and passes its name,
instructions, and tool list. `ResponsesHostServer` exposes the agent over the
Responses protocol so the Foundry runtime can route traffic to it.

Updated for the refreshed Foundry hosted-agent public preview:
  https://learn.microsoft.com/azure/foundry/agents/how-to/migrate-hosted-agent-preview
"""

from __future__ import annotations

import os
from typing import Callable, Iterable

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential


def _client() -> FoundryChatClient:
    return FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ.get("MODEL_DEPLOYMENT", "gpt-4o"),
        credential=DefaultAzureCredential(),
    )


def build_agent(
    name: str,
    instructions: str,
    tools: Iterable[Callable] | None = None,
) -> Agent:
    # `store=False` because conversation history is managed by the hosting platform
    # in the refreshed preview.
    return Agent(
        client=_client(),
        name=name,
        instructions=instructions,
        tools=list(tools or []),
        default_options={"store": False},
    )


def serve(agent: Agent) -> None:
    """Start the Responses-protocol HTTP server."""
    ResponsesHostServer(agent).run()
