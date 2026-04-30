@description('ACR name — must be globally unique, alphanumeric only, 5-50 chars')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

output loginServer string = acr.properties.loginServer
output name string = acr.name
