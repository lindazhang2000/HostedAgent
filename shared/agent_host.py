"""Shared agent factory used by every hosted-agent container.

Each `agents/<name>/main.py` imports `build_app` and passes its name,
instructions, and tool list. `from_agent_framework` exposes the agent over
the Responses protocol so the Foundry runtime can route traffic to it.
"""

from __future__ import annotations

import os
from typing import Callable, Iterable

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from azure.ai.agentserver.agentframework import from_agent_framework


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
    return Agent(
        client=_client(),
        name=name,
        instructions=instructions,
        tools=list(tools or []),
    )


async def serve(agent: Agent) -> None:
    """Start the Responses-protocol HTTP server."""
    await from_agent_framework(agent).run_async()
