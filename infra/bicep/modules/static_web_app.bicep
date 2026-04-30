@description('Name of the Static Web App')
param name string

@description('Azure region — SWA uses a limited set of locations, default to centralus')
param location string = 'centralus'

@description('Resource tags')
param tags object = {}

@description('SKU tier: Free or Standard')
param skuName string = 'Free'

resource swa 'Microsoft.Web/staticSites@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuName
  }
  properties: {
    buildProperties: {
      appLocation: 'frontend'
      outputLocation: 'dist'
    }
  }
}

output hostname string = swa.properties.defaultHostname
output id string = swa.id
