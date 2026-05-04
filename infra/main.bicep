targetScope = 'resourceGroup'

@minLength(1)
@description('Primary location for all resources. Hosted agents are available in: eastus2, swedencentral, francecentral, ...')
param location string = resourceGroup().location

@description('Object ID of the user/principal granted Azure AI User on the project.')
param userPrincipalId string = deployer().objectId

var suffix = uniqueString(resourceGroup().id)
var aiFoundryName = 'aif-${suffix}'
var aiProjectName = 'proj-${suffix}'
var registryName = 'cr${suffix}'

var azureAIUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' = {
  name: aiFoundryName
  location: location
  identity: { type: 'SystemAssigned' }
  sku: { name: 'S0' }
  kind: 'AIServices'
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundryName
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
  }
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
}

@description('Container Registry that stores the hosted agent image. Foundry pulls the image from here at deploy time.')
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
  }
}

@description('Allow the Foundry project managed identity to pull images from ACR.')
resource projectAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, aiProject.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

@description('Grant the deploying user Azure AI User on the project so they can register agent versions.')
resource userAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, userPrincipalId, azureAIUserRoleId)
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

output AZURE_AI_FOUNDRY_NAME string = aiFoundry.name
output AZURE_AI_PROJECT_NAME string = aiProject.name
output AZURE_AI_PROJECT_ENDPOINT string = 'https://${aiFoundry.properties.endpoint}/api/projects/${aiProject.name}'
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
