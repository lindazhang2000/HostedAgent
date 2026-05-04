# Foundry Hosted Agent (sample)

A minimal **containerized hosted agent** for [Microsoft Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agents).

Unlike *prompt-based* agents (which are just prompt + tool config), a hosted
agent is **your own code in a container** that the Foundry runtime executes
inside a per-session VM-isolated sandbox, with its own Microsoft Entra
identity and dedicated endpoint.

## What this sample contains

| File | Purpose |
|---|---|
| [src/main.py](src/main.py) | Responses-protocol agent that calls a Foundry model and streams the reply |
| [src/Dockerfile](src/Dockerfile) | Container image |
| [src/requirements.txt](src/requirements.txt) | Python dependencies |
| [agent.yaml](agent.yaml) | Hosted-agent manifest (image, resources, protocols, env) |
| [azure.yaml](azure.yaml) | `azd` project that builds + pushes the image, then registers the version |
| [scripts/deploy_agent_version.py](scripts/deploy_agent_version.py) | Calls `AIProjectClient.agents.create_version` with `ContainerAgentDefinition` |
| [infra/main.bicep](infra/main.bicep) | Foundry account + project + ACR + RBAC |

## Endpoint

After `azd up`, the agent is reachable at:

```
{AZURE_AI_PROJECT_ENDPOINT}/agents/echo-agent/endpoint/protocols/openai/v1/responses
```

Any OpenAI-compatible SDK (Python, JS, C#) can call it — the Foundry runtime
manages conversation history, streaming, and session state automatically.

## Deploy

```powershell
# 1. Login
az login
azd auth login

# 2. Provision Foundry + ACR + RBAC, build image, register agent version
azd up
```

`azd up` runs:

1. `infra/main.bicep` — creates the Foundry account/project and ACR.
2. `docker build` + `docker push` of `src/Dockerfile`.
3. `scripts/deploy_agent_version.py` — calls
   `agents.create_version(definition=ContainerAgentDefinition(...))`.

The runtime then provisions a sandbox on first invocation (cold start), runs
your container, and tears it down after 15 minutes idle (state persists for
up to 30 days). Pricing is per active CPU/memory consumption.

## Try it

```bash
ENDPOINT="$(azd env get-values | grep AZURE_AI_PROJECT_ENDPOINT | cut -d= -f2 | tr -d '\"')"
TOKEN="$(az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv)"

curl -X POST "$ENDPOINT/agents/echo-agent/endpoint/protocols/openai/v1/responses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello, hosted agent!"}'
```

## Compare with the prompt-agent workshop

| | This repo (hosted agent) | TechWorkshop-L300 (prompt agent) |
|---|---|---|
| `kind` | `container` | `prompt` |
| Definition | `ContainerAgentDefinition` | `PromptAgentDefinition` |
| Where it runs | Per-session VM sandbox | Foundry's prompt runtime |
| You provide | Container image + code | Instructions text + tool list |
| Endpoint | `/agents/{name}/endpoint/protocols/openai/v1/responses` | Threads/runs API |
| Identity | Per-agent Microsoft Entra identity | Project identity |

## Next steps

- Swap `EchoAgent` for an Agent Framework / LangGraph orchestration.
- Add `protocols: [responses, invocations]` to expose a webhook surface.
- Connect to the Foundry Toolbox MCP endpoint to use Code Interpreter, Web
  Search, AI Search, etc.
- Read [Agent runtime components](https://learn.microsoft.com/azure/foundry/agents/concepts/runtime-components).
