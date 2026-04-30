// Kinetic-Core — Main Bicep Deployment
// Deploys all Azure resources for the full platform.
// Usage:
//   az deployment group create \
//     --resource-group kinetic-core-rg \
//     --template-file main/main.bicep \
//     --parameters @main/parameters.prod.json

targetScope = 'resourceGroup'

@description('Environment name (dev, staging, prod)')
param environment string = 'dev'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Unique suffix to avoid naming conflicts')
param suffix string = uniqueString(resourceGroup().id)

@description('Allowed CORS origin for the API')
param allowedOrigin string = 'http://localhost:3000'

@description('Region for CosmosDB — override when primary region has capacity issues')
param cosmosLocation string = 'westus2'

var prefix = 'kcore'
var tags = {
  project: 'kinetic-core'
  environment: environment
  managedBy: 'bicep'
}

// ── Key Vault ─────────────────────────────────────────────────────────────────
module keyVault '../modules/key_vault.bicep' = {
  name: 'keyVaultDeploy'
  params: {
    name: '${prefix}-kv-${suffix}'
    location: location
    tags: tags
  }
}

// ── IoT Hub ───────────────────────────────────────────────────────────────────
module iotHub '../modules/iot_hub.bicep' = {
  name: 'iotHubDeploy'
  params: {
    name: '${prefix}-iothub-${suffix}'
    location: location
    tags: tags
    skuName: environment == 'prod' ? 'S1' : 'F1'
    skuCapacity: environment == 'prod' ? 2 : 1
  }
}

// ── Event Grid ────────────────────────────────────────────────────────────────
module eventGrid '../modules/event_grid.bicep' = {
  name: 'eventGridDeploy'
  params: {
    topicName: '${prefix}-eg-${suffix}'
    location: location
    tags: tags
    iotHubId: iotHub.outputs.iotHubId
  }
}

// ── Cosmos DB ─────────────────────────────────────────────────────────────────
module cosmosDb '../modules/cosmos_db.bicep' = {
  name: 'cosmosDbDeploy'
  params: {
    accountName: '${prefix}-cosmos-${suffix}'
    location: cosmosLocation
    tags: tags
    databaseName: 'kinetic-core'
  }
}

// ── Azure AI Search ───────────────────────────────────────────────────────────
module aiSearch '../modules/ai_search.bicep' = {
  name: 'aiSearchDeploy'
  params: {
    name: '${prefix}-search-${suffix}'
    location: location
    tags: tags
    sku: environment == 'prod' ? 'standard' : 'basic'
  }
}

// ── Azure Functions ───────────────────────────────────────────────────────────
// Azure OpenAI endpoint is intentionally blank — agents/client.py falls back
// to OPENAI_API_KEY automatically when AZURE_OPENAI_ENDPOINT is empty.
// Wire this up once Azure OpenAI quota is approved for the subscription.
module functionApp '../modules/function_app.bicep' = {
  name: 'functionAppDeploy'
  params: {
    name: '${prefix}-func-${suffix}'
    location: location
    tags: tags
    cosmosEndpoint: cosmosDb.outputs.endpoint
    openAiEndpoint: ''
    searchEndpoint: aiSearch.outputs.endpoint
    allowedOrigin: allowedOrigin
    keyVaultName: keyVault.outputs.name
  }
}

// ── Azure Static Web Apps ─────────────────────────────────────────────────────
module staticWebApp '../modules/static_web_app.bicep' = {
  name: 'staticWebAppDeploy'
  params: {
    name: '${prefix}-swa-${suffix}'
    tags: tags
    skuName: environment == 'prod' ? 'Standard' : 'Free'
  }
}

// ── Azure Monitor + Log Analytics ─────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-law-${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appi-${suffix}'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output iotHubConnectionString string = iotHub.outputs.connectionString
output cosmosEndpoint string = cosmosDb.outputs.endpoint
output searchEndpoint string = aiSearch.outputs.endpoint
output functionAppUrl string = functionApp.outputs.url
output instrumentationKey string = appInsights.properties.InstrumentationKey
output swaHostname string = staticWebApp.outputs.hostname
