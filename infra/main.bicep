targetScope = 'resourceGroup'

@minLength(1)
@description('Primary location for all resources. Hosted agents are available in: eastus2, swedencentral, francecentral, ...')
param location string = resourceGroup().location

@description('Object ID of the user/principal granted Azure AI User on the project.')
param userPrincipalId string = deployer().objectId

@description('Optional: principal id (instance identity) of the cart-manager hosted agent. Provide after the agent is registered to grant Storage data-plane access. Leave empty to skip.')
param cartManagerPrincipalId string = ''

var suffix = uniqueString(resourceGroup().id)
var aiFoundryName = 'aif-${suffix}'
var aiProjectName = 'proj-${suffix}'
var registryName = 'cr${suffix}'
var storageAccountName = 'st${suffix}'
var cartContainerName = 'carts'

var azureAIUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
// Storage Blob Data Contributor (read/write/delete blobs)
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

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

@description('GPT-4o model deployment used by the hosted agent.')
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = {
  name: 'gpt-4o'
  parent: aiFoundry
  sku: {
    name: 'GlobalStandard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
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
resource userAIUserProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, userPrincipalId, azureAIUserRoleId)
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

@description('Grant the deploying user Azure AI User on the Foundry account.')
resource userAIUserAccount 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundry.id, userPrincipalId, azureAIUserRoleId)
  scope: aiFoundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

@description('Storage account for shared cart state across hosted-agent containers (AAD-only).')
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {}
}

resource cartContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: cartContainerName
  properties: {
    publicAccess: 'None'
  }
}

@description('Grant the deploying user Storage Blob Data Contributor for local dev.')
resource userStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

@description('Grant the cart-manager hosted agent identity Storage Blob Data Contributor (only when principal id provided).')
resource cartManagerStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(cartManagerPrincipalId)) {
  name: guid(storageAccount.id, cartManagerPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: cartManagerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output AZURE_AI_FOUNDRY_NAME string = aiFoundry.name
output AZURE_AI_PROJECT_NAME string = aiProject.name
output AZURE_AI_PROJECT_ENDPOINT string = '${aiFoundry.properties.endpoint}api/projects/${aiProject.name}'
output AZURE_AI_FOUNDRY_ENDPOINT string = aiFoundry.properties.endpoint
output AZURE_MODEL_DEPLOYMENT string = gpt4oDeployment.name
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccount.name
output AZURE_STORAGE_BLOB_ENDPOINT string = storageAccount.properties.primaryEndpoints.blob
output AZURE_STORAGE_CART_CONTAINER string = cartContainerName
