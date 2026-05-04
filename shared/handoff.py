"""Sibling-agent handoff tool used by the Cora router agent.

Cora calls this when it determines another specialist should handle the
turn. Each specialist is a separate hosted agent reachable at:
  {FOUNDRY_PROJECT_ENDPOINT}/agents/{name}/endpoint/protocols/openai/v1/responses
"""

from __future__ import annotations

import os
from typing import Annotated, Any

import httpx
from azure.identity import DefaultAzureCredential
from pydantic import Field

_VALID = {"interior-designer", "inventory", "customer-loyalty", "cart-manager"}
_credential = DefaultAzureCredential()


def _project_endpoint() -> str:
    return os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")


async def handoff_to_specialist(
    specialist: Annotated[
        str,
        Field(description="One of: interior-designer, inventory, customer-loyalty, cart-manager"),
    ],
    user_message: Annotated[str, Field(description="The user's request to forward")],
) -> dict[str, Any]:
    """Forward the user's message to a specialist hosted agent and return its reply."""
    if specialist not in _VALID:
        return {"error": f"unknown specialist '{specialist}'", "valid": sorted(_VALID)}

    token = _credential.get_token("https://cognitiveservices.azure.com/.default").token
    url = f"{_project_endpoint()}/agents/{specialist}/endpoint/protocols/openai/v1/responses"
    payload = {
        "input": [{"role": "user", "content": user_message}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return {"specialist": specialist, "reply": r.json()}
