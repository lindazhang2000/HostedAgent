# Foundry Hosted Agents - Zava (Microsoft Agent Framework)

A multi-hosted-agent rewrite of the
[TechWorkshop-L300-AI-Apps-and-agents](https://github.com/microsoft/TechWorkshop-L300-AI-Apps-and-agents)
Zava shopping assistant, built on **Microsoft Agent Framework** and deployed
as **container/hosted agents** per
[Microsoft Foundry hosted agents](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agents).

Each specialist agent is a separate immutable hosted agent (own image, own
per-agent Microsoft Entra identity, own Responses endpoint). Cora (the
public-facing router) calls the specialists over the project's Responses
protocol via a `handoff_to_specialist` tool.

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `cora` | `handoff_to_specialist`, `list_products` | Greets the user, browses, routes |
| `interior-designer` | `list_products` | DIY + design recommendations |
| `inventory` | `inventory_check` | Stock & warehouse lookups |
| `customer-loyalty` | `calculate_discount` | Tiered loyalty discounts |
| `cart-manager` | `add_to_cart`, `view_cart`, `clear_cart` | Cart operations |

All five agents share `shared/agent_host.py` (an `Agent` + `FoundryChatClient`
wrapped by `azure.ai.agentserver.agentframework.from_agent_framework`).

## Deploy

The resource group `hostedagents` is already provisioned in Sweden Central with:

- Foundry `aif-h2aa4vjgovzru`, project `proj-h2aa4vjgovzru`
- ACR `crh2aa4vjgovzru.azurecr.io`
- `gpt-4o` model deployment

Build, push, and register all 5 hosted agents:

```powershell
cd C:\Users\zhenlzhang\githubrepository\HostedAgent
az login
az acr login -n crh2aa4vjgovzru

$env:AZURE_AI_PROJECT_ENDPOINT       = "https://aif-h2aa4vjgovzru.cognitiveservices.azure.com/api/projects/proj-h2aa4vjgovzru"
$env:AZURE_CONTAINER_REGISTRY_ENDPOINT = "crh2aa4vjgovzru.azurecr.io"

python ./scripts/deploy_all.py
```

If you ever need to recreate the infra in a fresh RG:

```powershell
az group create -n hostedagents -l swedencentral
az deployment group create -g hostedagents -f infra/main.bicep -p location=swedencentral
```

## Try it

```powershell
$ENDPOINT = "$env:AZURE_AI_PROJECT_ENDPOINT/agents/cora/endpoint/protocols/openai/v1/responses"
$TOKEN    = (az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv)

curl -X POST $ENDPOINT `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"input":[{"role":"user","content":"Hi! I want to redo my living room in emerald and brass."}]}'
```

Cora will hand off to `interior-designer`, which uses `list_products` to
recommend pieces from the Zava catalog.

## Compare with the original workshop

| | Original workshop | This repo |
|---|---|---|
| Agent kind | Prompt agents (`PromptAgentDefinition`) | Container/hosted agents |
| Where it runs | Foundry prompt runtime | Per-session VM sandbox |
| SDK | `azure.ai.projects` direct | Microsoft Agent Framework (`FoundryChatClient`) |
| Routing | `HandoffService` w/ structured-output classifier | Tool-call: `handoff_to_specialist` |
| Endpoint | Threads/runs API | `/agents/{name}/endpoint/protocols/openai/v1/responses` |
| Identity | Project MI | Per-agent Microsoft Entra identity |
| Deploy | Bicep + `agents.create_version(PromptAgentDefinition(...))` | Bicep + `docker build/push` + `agents.create_version(ContainerAgentDefinition(...))` |

## Layout

```
HostedAgent/
├── agents/
│   ├── cora/                {main.py, Dockerfile, agent.yaml}
│   ├── interior-designer/   ...
│   ├── inventory/           ...
│   ├── customer-loyalty/    ...
│   └── cart-manager/        ...
├── shared/
│   ├── agent_host.py        # FoundryChatClient + Agent + Responses HTTP server
│   ├── handoff.py           # Cora's handoff_to_specialist tool
│   ├── zava_tools.py        # local function tools (inventory, discount, cart)
│   ├── requirements.txt     # pinned agent-framework + agentserver
│   └── Dockerfile.base
├── data/product_catalog.json
├── infra/main.bicep         # Foundry + ACR + gpt-4o + RBAC
├── scripts/deploy_all.py    # build/push/register every agent
├── azure.yaml               # azd manifest (postdeploy = deploy_all.py)
└── README.md
```

## Notes / caveats

- SDK preview: pin `agent-framework-* == 1.0.0rc6` and `azure-ai-agentserver-* == 1.0.0b16`.
- `ContainerAgentDefinition` / `ContainerProtocolVersion` names follow the
  hosted-agents preview SDK; verify against your installed `azure-ai-projects`.
- Tools in `shared/zava_tools.py` are illustrative (random stock,
  hard-coded loyalty tiers). For production, back them with Cosmos DB or
  real inventory APIs as the original workshop does.
