targetScope = 'resourceGroup'

@description('Azure region for the pilot Container App.')
param location string = resourceGroup().location

@description('Date after which the pilot resource group should be reviewed for cleanup.')
param pilotExpiry string

@minLength(40)
@maxLength(40)
@description('Full 40-character audited Git commit SHA used as the image tag.')
param imageTag string

var suffix = uniqueString(subscription().id, resourceGroup().id)
var appName = 'kcore-qr-api-${suffix}'
var acrName = 'kcoreqr${suffix}'
var containerEnvironmentName = 'kcore-qr-env-${suffix}'
var registryIdentityName = 'kcore-qr-pull-${suffix}'
var tags = {
  project: 'kinetic-core'
  environment: 'quantum-pilot'
  purpose: 'quantum-readiness-scan'
  pilotExpiry: pilotExpiry
  managedBy: 'bicep'
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: containerEnvironmentName
}

resource registryIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: registryIdentityName
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: registryIdentity.id
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${containerRegistry.properties.loginServer}/kinetic-core-api:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output containerAppName string = containerApp.name
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerImage string = '${containerRegistry.properties.loginServer}/kinetic-core-api:${imageTag}'
