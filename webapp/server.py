"""Tiny FastAPI chat UI for the deployed Foundry hosted agents.

Run:
    $env:AZURE_AI_PROJECT_ENDPOINT="https://.../api/projects/<name>"
    uvicorn webapp.server:app --reload --port 8000

Then open http://127.0.0.1:8000 in a browser.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

ENDPOINT_ENV = "AZURE_AI_PROJECT_ENDPOINT"
DEFAULT_AGENT = os.environ.get("DEFAULT_AGENT", "cora")

app = FastAPI(title="Zava hosted-agent chat")
_credential = DefaultAzureCredential()
_project: AIProjectClient | None = None


def _get_project() -> AIProjectClient:
    global _project
    if _project is None:
        endpoint = os.environ.get(ENDPOINT_ENV)
        if not endpoint:
            raise RuntimeError(f"Set {ENDPOINT_ENV} before starting the server.")
        _project = AIProjectClient(
            endpoint=endpoint,
            credential=_credential,
            allow_preview=True,
        )
    return _project


class ChatRequest(BaseModel):
    agent: str = DEFAULT_AGENT
    message: str
    previous_response_id: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: str
    output: str | None = None


class ChatResponse(BaseModel):
    reply: str
    response_id: str | None = None
    tool_calls: list[ToolCall] = []


def _extract_text(resp: Any) -> str:
    parts: list[str] = []
    for item in resp.output or []:
        if getattr(item, "type", None) != "message":
            continue
        for c in getattr(item, "content", None) or []:
            t = getattr(c, "text", None)
            if t:
                parts.append(t)
    return "\n".join(parts).strip()


def _extract_tool_calls(resp: Any) -> list[ToolCall]:
    calls: dict[str, ToolCall] = {}
    for item in resp.output or []:
        kind = getattr(item, "type", None)
        if kind == "function_call":
            calls[item.call_id] = ToolCall(
                name=item.name,
                arguments=item.arguments or "",
            )
        elif kind == "function_call_output":
            existing = calls.get(item.call_id)
            output = item.output if isinstance(item.output, str) else str(item.output)
            if existing:
                existing.output = output
    return list(calls.values())


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    client = _get_project().get_openai_client(agent_name=req.agent)
    kwargs: dict[str, Any] = {"input": req.message}
    if req.previous_response_id:
        kwargs["previous_response_id"] = req.previous_response_id
    resp = client.responses.create(**kwargs)
    return ChatResponse(
        reply=_extract_text(resp) or "(empty)",
        response_id=getattr(resp, "id", None),
        tool_calls=_extract_tool_calls(resp),
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "index.html")
