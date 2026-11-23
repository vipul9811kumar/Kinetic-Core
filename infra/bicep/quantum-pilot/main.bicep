targetScope = 'resourceGroup'

@description('Azure region for pilot resources.')
param location string = resourceGroup().location

@description('Region for Cosmos DB.')
param cosmosLocation string = 'westus2'

@description('Date after which the pilot resource group should be reviewed for cleanup.')
param pilotExpiry string

@description('Public IPv4 address of the OCI scanner VM for Key Vault metadata access.')
param scannerIPv4 string

@description('Object ID of the signed-in work account user receiving pilot-scoped AcrPush and Key Vault Reader roles.')
param imageBuilderPrincipalId string

var suffix = uniqueString(subscription().id, resourceGroup().id)
var tags = {
  project: 'kinetic-core'
  environment: 'quantum-pilot'
  purpose: 'quantum-readiness-scan'
  pilotExpiry: pilotExpiry
  managedBy: 'bicep'
}

var keyVaultName = 'kcoreqrkv${suffix}'
var iotHubName = 'kcore-qr-iot-${suffix}'
var eventGridName = 'kcore-qr-eg-${suffix}'
var cosmosAccountName = 'kcoreqrcosmos${suffix}'
var searchName = 'kcore-qr-search-${suffix}'
var acrName = 'kcoreqr${suffix}'
var staticWebAppName = 'kcore-qr-web-${suffix}'
var logAnalyticsName = 'kcore-qr-law-${suffix}'
var appInsightsName = 'kcore-qr-appi-${suffix}'
var containerEnvironmentName = 'kcore-qr-env-${suffix}'
var containerAppName = 'kcore-qr-api-${suffix}'
var registryIdentityName = 'kcore-qr-pull-${suffix}'

var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleDefinitionId = '8311e382-0749-4cb8-b61a-304f252e45ec'
var keyVaultReaderRoleDefinitionId = '21090545-7ca7-4776-b22c-e363652d74d2'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: [
        {
          value: scannerIPv4
        }
      ]
    }
  }
}

resource keyVaultReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, imageBuilderPrincipalId, keyVaultReaderRoleDefinitionId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultReaderRoleDefinitionId)
    principalId: imageBuilderPrincipalId
    principalType: 'User'
  }
}

module iotHub '../modules/iot_hub.bicep' = {
  name: 'pilotIotHub'
  params: {
    name: iotHubName
    location: location
    tags: tags
    skuName: 'F1'
    skuCapacity: 1
  }
}

module eventGrid '../modules/event_grid.bicep' = {
  name: 'pilotEventGrid'
  params: {
    topicName: eventGridName
    location: location
    tags: tags
    iotHubId: iotHub.outputs.iotHubId
  }
}

module cosmosDb '../modules/cosmos_db.bicep' = {
  name: 'pilotCosmosDb'
  params: {
    accountName: cosmosAccountName
    location: cosmosLocation
    tags: tags
    databaseName: 'kinetic-core'
  }
}

module aiSearch '../modules/ai_search.bicep' = {
  name: 'pilotAiSearch'
  params: {
    name: searchName
    location: location
    tags: tags
    sku: 'basic'
    replicaCount: 1
    partitionCount: 1
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource imageBuilderAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, imageBuilderPrincipalId, acrPushRoleDefinitionId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPushRoleDefinitionId)
    principalId: imageBuilderPrincipalId
    principalType: 'User'
  }
}

module staticWebApp '../modules/static_web_app.bicep' = {
  name: 'pilotStaticWebApp'
  params: {
    name: staticWebAppName
    tags: tags
    skuName: 'Free'
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource registryIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: registryIdentityName
  location: location
  tags: tags
}

resource registryAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, registryIdentity.id, acrPullRoleDefinitionId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
    principalId: registryIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output resourceGroupName string = resourceGroup().name
output keyVaultName string = keyVault.name
output acrName string = containerRegistry.name
output acrLoginServer string = containerRegistry.properties.loginServer
output containerAppName string = containerAppName
output containerAppResourceId string = resourceId('Microsoft.App/containerApps', containerAppName)
output aiSearchName string = searchName
output cosmosAccountName string = cosmosAccountName
