"""
Foundry Hosted Agent - Responses protocol entry point.

This is a minimal containerized agent that:
  - Runs a Foundry Agent Service-compatible HTTP server (Responses protocol)
  - Calls a Foundry-deployed model using the agent's per-agent Microsoft Entra
    identity (DefaultAzureCredential picks it up automatically inside the sandbox)
  - Streams replies back to the platform

Reference:
  https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents

Run locally:
  uvicorn main:app --host 0.0.0.0 --port 8088

Container entrypoint is configured in the Dockerfile.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncIterator

from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

# The foundry hosted-agents Python protocol package provides the Responses
# server, OpenTelemetry wiring, and health endpoints. (Replace with the
# official package name once you pin a version.)
#
#   pip install foundry-hosted-agents
#
from foundry_hosted_agents.responses import ResponsesAgent, create_app  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hosted-agent")

# These are populated by the platform from the environment variables you set
# in agent.yaml (env: section). FOUNDRY_PROJECT_ENDPOINT is injected by the
# runtime automatically.
PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["MODEL_DEPLOYMENT"]      # e.g. "gpt-4o"
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful Foundry hosted agent. Answer concisely.",
)


class EchoAgent(ResponsesAgent):
    """Minimal Responses-protocol agent that calls a Foundry model."""

    def __init__(self) -> None:
        super().__init__()
        self._credential = DefaultAzureCredential()
        # Foundry exposes models under the project endpoint with a managed
        # OpenAI-compatible surface.
        self._client = AsyncAzureOpenAI(
            azure_endpoint=PROJECT_ENDPOINT,
            azure_ad_token_provider=self._token_provider,
            api_version="2025-01-01-preview",
        )

    async def _token_provider(self) -> str:
        token = await self._credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        return token.token

    async def respond(self, messages, **_kwargs) -> AsyncIterator[str]:
        """Stream a model reply for the inbound conversation."""
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages:
            chat_messages.append({"role": m.role, "content": m.content})

        stream = await self._client.chat.completions.create(
            model=MODEL_DEPLOYMENT,
            messages=chat_messages,
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# `create_app` builds a FastAPI/Starlette app that implements:
#   POST /agents/{name}/endpoint/protocols/openai/v1/responses
#   GET  /healthz
#   /files endpoints for session-scoped uploads
# and wires OpenTelemetry exporters that the platform reads.
app = create_app(EchoAgent())
