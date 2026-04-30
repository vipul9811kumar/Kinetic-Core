param name string
param location string
param tags object
param sku string = 'standard'
param replicaCount int = 1
param partitionCount int = 1

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: sku }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'standard'
  }
}

output endpoint string = 'https://${searchService.name}.search.windows.net'
output name string = searchService.name
