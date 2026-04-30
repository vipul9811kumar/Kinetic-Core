param name string
param location string
param tags object
param gpt4oDeploymentName string = 'gpt-4o'
param adaDeploymentName string = 'text-embedding-ada-002'
param gpt4oCapacity int = 80
param adaCapacity int = 120

resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAiAccount
  name: gpt4oDeploymentName
  sku: { name: 'Standard', capacity: gpt4oCapacity }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-05-13' }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource adaDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAiAccount
  name: adaDeploymentName
  sku: { name: 'Standard', capacity: adaCapacity }
  properties: {
    model: { format: 'OpenAI', name: 'text-embedding-ada-002', version: '2' }
  }
  dependsOn: [gpt4oDeployment]
}

output endpoint string = openAiAccount.properties.endpoint
output accountName string = openAiAccount.name
