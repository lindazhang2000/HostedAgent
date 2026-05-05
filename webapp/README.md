# Zava hosted-agent test chat

Minimal FastAPI + HTML UI that talks to your deployed Foundry hosted agents
via the Responses API. Useful when the Foundry Playground hides
tool-using replies (handoffs, `list_products`, etc.).

The same `webapp/` directory runs locally and can be deployed to Azure App Service.

## Architecture

| Resource | Notes |
|---|---|
| App Service Plan | Linux, B1 (or larger) |
| Web App | Python 3.12, system-assigned managed identity |

The web app's MSI must be granted:

- `Cognitive Services OpenAI User` on the Foundry account
- `Azure AI User` on the Foundry project

App settings:

- `AZURE_AI_PROJECT_ENDPOINT` = your project endpoint
- `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`

Startup command: `startup.sh` -> `uvicorn server:app --host 0.0.0.0 --port 8000`

## Run locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r webapp\requirements.txt

$env:AZURE_AI_PROJECT_ENDPOINT = "https://<foundry>.cognitiveservices.azure.com/api/projects/<project>"
.\.venv\Scripts\python.exe -m uvicorn webapp.server:app --port 8765
```

Open http://127.0.0.1:8765 - pick an agent, type a message.
Tool calls (handoffs, `list_products`, etc.) are shown under each reply.

Auth uses `DefaultAzureCredential`, so `az login` is required.

## Redeploy

```powershell
$src = Join-Path $PSScriptRoot ""  # webapp/
$zip = Join-Path $env:TEMP "webapp.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$src\server.py","$src\index.html","$src\requirements.txt","$src\startup.sh" -DestinationPath $zip

az webapp deploy `
  -g <resource-group> `
  -n <web-app-name> `
  --src-path $zip `
  --type zip
```

## Re-provision (fresh)

```powershell
$rg="<resource-group>"; $loc="swedencentral"
$plan="<plan-name>"; $app="<web-app-name>"
$account="<foundry-account-name>"; $project="<project-name>"

az appservice plan create -g $rg -n $plan --is-linux --sku B1 -l $loc
az webapp create -g $rg -p $plan -n $app --runtime "PYTHON:3.12"
az webapp config set -g $rg -n $app --startup-file "startup.sh"

$mi = az webapp identity assign -g $rg -n $app --query principalId -o tsv
$sub = az account show --query id -o tsv
$acct = "/subscriptions/$sub/resourceGroups/$rg/providers/Microsoft.CognitiveServices/accounts/$account"
$proj = "$acct/projects/$project"

az role assignment create --assignee-object-id $mi --assignee-principal-type ServicePrincipal `
  --role "Cognitive Services OpenAI User" --scope $acct
az role assignment create --assignee-object-id $mi --assignee-principal-type ServicePrincipal `
  --role "Azure AI User" --scope $proj

az webapp config appsettings set -g $rg -n $app --settings `
  AZURE_AI_PROJECT_ENDPOINT="https://$account.cognitiveservices.azure.com/api/projects/$project" `
  SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

Then run the redeploy step above.

## Files

| File | Purpose |
|---|---|
| `server.py` | FastAPI: `GET /` serves UI, `POST /api/chat` calls the hosted agent |
| `index.html` | Single-page chat UI with agent selector + threading toggle |
| `requirements.txt` | `fastapi`, `uvicorn`, `azure-ai-projects`, `azure-identity`, `pydantic` |
| `startup.sh` | App Service startup command |
