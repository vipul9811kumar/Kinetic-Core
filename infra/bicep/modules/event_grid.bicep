param topicName string
param location string
param tags object
param iotHubId string

resource eventGridTopic 'Microsoft.EventGrid/systemTopics@2023-12-15-preview' = {
  name: topicName
  location: location
  tags: tags
  properties: {
    source: iotHubId
    topicType: 'Microsoft.Devices.IoTHubs'
  }
}

output topicId string = eventGridTopic.id
output topicName string = eventGridTopic.name
