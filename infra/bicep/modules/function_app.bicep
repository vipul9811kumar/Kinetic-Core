param name string
param location string
param tags object
param cosmosEndpoint string
param openAiEndpoint string
param searchEndpoint string
param allowedOrigin string
param keyVaultName string

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: '${replace(name, '-', '')}stor'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

resource hostingPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${name}-plan'
  location: location
  tags: tags
  sku: { name: 'B1', tier: 'Basic' }
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      pythonVersion: '3.11'
      cors: { allowedOrigins: [allowedOrigin] }
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
        { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
        { name: 'AZURE_OPENAI_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=azure-openai-key)' }
        { name: 'AZURE_SEARCH_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=azure-search-key)' }
        { name: 'COSMOS_KEY', value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=cosmos-key)' }
      ]
    }
  }
}

output url string = 'https://${functionApp.properties.defaultHostName}'
output principalId string = functionApp.identity.principalId
