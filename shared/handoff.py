"""Sibling-agent handoff tool used by the Cora router agent.

Uses AIProjectClient.get_openai_client(agent_name=...) which routes
to the specialist hosted agent's responses endpoint.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from agent_framework import tool
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from pydantic import Field

_VALID = {"interior-designer", "inventory", "customer-loyalty", "cart-manager"}
_credential = DefaultAzureCredential()
_project: AIProjectClient | None = None


def _get_project() -> AIProjectClient:
    global _project
    if _project is None:
        _project = AIProjectClient(
            endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            credential=_credential,
            allow_preview=True,
        )
    return _project


@tool(approval_mode="never_require")
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

    try:
        client = _get_project().get_openai_client(agent_name=specialist)
        resp = client.responses.create(input=user_message)
        text_parts: list[str] = []
        for item in (resp.output or []):
            for c in getattr(item, "content", None) or []:
                t = getattr(c, "text", None)
                if t:
                    text_parts.append(t)
        return {
            "specialist": specialist,
            "reply_text": "\n".join(text_parts) or "(empty)",
        }
    except Exception as exc:  # noqa: BLE001
        return {"specialist": specialist, "error": f"{type(exc).__name__}: {exc}"[:500]}
