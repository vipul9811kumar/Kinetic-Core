param name string
param location string
param tags object
param skuName string = 'S1'
param skuCapacity int = 1

resource iotHub 'Microsoft.Devices/IotHubs@2023-06-30' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
    capacity: skuCapacity
  }
  properties: {
    routing: {
      fallbackRoute: {
        name: '$fallback'
        source: 'DeviceMessages'
        isEnabled: true
        endpointNames: ['events']
      }
    }
    messagingEndpoints: {
      fileNotifications: {
        lockDurationAsIso8601: 'PT1M'
        ttlAsIso8601: 'PT1H'
        maxDeliveryCount: 10
      }
    }
    enableFileUploadNotifications: false
    cloudToDevice: {
      maxDeliveryCount: 10
      defaultTtlAsIso8601: 'PT1H'
      feedback: {
        lockDurationAsIso8601: 'PT1M'
        ttlAsIso8601: 'PT1H'
        maxDeliveryCount: 10
      }
    }
  }
}

output iotHubId string = iotHub.id
output iotHubName string = iotHub.name
output hostName string = iotHub.properties.hostName
