if (-not $env:AZURE_AI_PROJECT_ENDPOINT -or -not $env:AZURE_BUILD_TAG) {
  Write-Error 'AZURE_AI_PROJECT_ENDPOINT and AZURE_BUILD_TAG must be set'
  exit 1
}
$base = $env:AZURE_AI_PROJECT_ENDPOINT
$tag = $env:AZURE_BUILD_TAG
foreach ($a in @('cora','cart-manager','customer-loyalty','interior-designer','inventory')) {
  $r = az rest --method GET --url "$base/agents/$a/versions?api-version=2025-11-15-preview" --resource 'https://ai.azure.com' --query "data[?contains(definition.image,'$tag')].{name:name,version:version,status:status}" -o tsv
  Write-Host ("{0,-20} {1}" -f $a, $r)
}
