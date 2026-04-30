param accountName string
param location string
param tags object
param databaseName string = 'kinetic-core'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [{ locationName: location, failoverPriority: 0 }]
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    capabilities: [{ name: 'EnableServerless' }]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: { resource: { id: databaseName } }
}

var containers = [
  { id: 'telemetry', partitionKey: '/device_id', ttl: 2592000 }   // 30-day TTL
  { id: 'incidents', partitionKey: '/incident_id', ttl: -1 }        // permanent
  { id: 'agent-memory', partitionKey: '/incident_id', ttl: -1 }     // permanent audit
  { id: 'work-orders', partitionKey: '/work_order_id', ttl: -1 }    // permanent
  { id: 'prompt-registry', partitionKey: '/agent', ttl: -1 }        // permanent
]

resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = [for c in containers: {
  parent: database
  name: c.id
  properties: {
    resource: {
      id: c.id
      partitionKey: { paths: [c.partitionKey], kind: 'Hash' }
      defaultTtl: c.ttl
    }
  }
}]

output endpoint string = cosmosAccount.properties.documentEndpoint
output accountName string = cosmosAccount.name
