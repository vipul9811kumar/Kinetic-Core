# Kinetic Core Quantum-Readiness Scan
## Azure-Enriched Interim Report

**Evidence snapshot:** 23 November 2026<br>
**Status:** Partial scan; not a readiness certification
**Scope:** Kinetic Core pilot only; VoltLedger excluded

## Executive summary

The local source, dependency, and container-image inventories from 19 November have been supplemented with a read-only Azure Portal review on 23 November. The selected Azure directory showed one active subscription where the signed-in user has the Owner role. The portal listed two resource groups and 13 resources: 12 resources in the quantum-readiness pilot group and one Azure DevOps organization resource outside it.

The pilot group is no longer empty. The Azure resource inventory collected on 19 November also records a successful deployment, contradicting statements in the earlier interim report and runbook that the group contained no service resources. This report supersedes those earlier Azure-status statements.

The pilot Azure Container Registry currently has no listed repositories, and no Container App was visible. Therefore, the Kinetic Core API image has not been verified in Azure, and there is no pilot Container App endpoint to test. Key Vault certificate metadata could not be retrieved from the current browser because the vault firewall denied the request. No secret values or private-key material were requested or read.

The scan remains partial. The selected subscription and directory have not been reconciled with the actual Kinetic Core production environment, and human review of the local cryptography observation is still pending.

## Scope and evidence

| Evidence | Date | Limitations |
|---|---|---|
| Local source, dependency, and image scan artifacts | 19 Nov 2026 | Source snapshot is commit `25bfdab78b439a185b67d1bf7e7a8a94b5f82107`; this is not a fresh scan of Azure or deployed versions. |
| Saved Azure pilot configuration inventory | 19 Nov 2026 | Pilot-resource metadata only; not production inventory. It records deployment success and 11 resources but omits an Action Group visible in the later portal listing. |
| Azure Portal subscription, resource-group, resource, ACR, and Key Vault views | 23 Nov 2026 | Read-only browser review of the selected directory and subscription. No ARM export or cross-directory discovery was performed. |

The current repository is at `7bc35c7e29e92ecd813c00f4bd291ed531b0f1c6`. Comparing it with the local scan commit shows only the pilot documentation and isolated quantum-pilot Bicep files were added; application source files were unchanged. The application source observation is therefore still attributable to the earlier source snapshot, but the overall repository HEAD is no longer identical to it.

The selected Azure directory/subscription does not match identifiers recorded in earlier project notes. Do not treat this inventory as coverage of production until the Kinetic Core deployment owner confirms that it is the intended environment.

## Azure inventory

### Subscription-level view

- One active subscription was visible in the selected directory.
- The signed-in account had the Owner role on that subscription.
- Two resource groups and 13 resources were listed.
- The portal displayed a non-zero current-cost figure, but its period and resource attribution were not established. Use Cost Analysis before attributing charges to the pilot.
- The second resource group contains an Azure DevOps organization resource and is outside this pilot's scan scope.

### Pilot resource-group view

The portal listed 12 resources in the pilot group:

| Resource type | Count | Observed configuration / status |
|---|---:|---|
| Action Group | 1 | Listed with Application Insights Smart Detection. |
| Application Insights | 1 | Also present in the 19 November inventory as workspace-linked. |
| Event Grid system topic | 1 | Source type recorded as IoT Hub in the 19 November inventory. |
| Container Apps environment | 1 | Present; logs are configured to Log Analytics in the saved inventory. |
| IoT Hub | 1 | F1 tier, capacity 1 in the saved inventory; network and local-auth settings were not established. |
| Log Analytics workspace | 1 | 30-day retention in the saved inventory. |
| User-assigned managed identity | 1 | Present in the saved inventory. |
| Azure AI Search | 1 | Basic tier, one replica and one partition; public network access enabled in the saved inventory. |
| Static Web App | 1 | Free tier in the saved inventory. |
| Cosmos DB account | 1 | Serverless, free tier disabled, one database and five containers, Session consistency in the saved inventory. |
| Azure Container Registry | 1 | Basic tier; admin user disabled in the saved inventory. The current repository view showed no repositories. |
| Key Vault | 1 | Standard tier; RBAC enabled and soft delete enabled in the saved inventory. Current portal overview showed purge protection disabled. |

The 19 November inventory records a pilot-expiry tag of 20 November 2026. That date had passed by this report's evidence snapshot; verify the current tag and review the resources' costs and intended retention with the subscription owner. This report does not delete or modify any resource.

## Findings and follow-up

### 1. Azure pilot resources are deployed; prior documentation is stale

The current portal lists 12 resources in the pilot resource group. The saved 19 November configuration inventory records deployment state `Succeeded` and 11 resources; the portal additionally lists an Action Group. Earlier report/runbook statements that the group was empty are inconsistent with this evidence and must not be used.

**Follow-up:** Confirm the deployed pilot resources and retention plan with the owner. Review actual charges and update the expiry decision. No cleanup was attempted.

### 2. No Azure API image or Container App was verified

The ACR repository page showed no repositories. The subscription resource list showed a Container Apps environment but no Container App. The existing local API image SBOM is not proof of an image in ACR or a live deployment.

**Follow-up:** Keep the image, deployment, and endpoint sections marked not scanned. Pushing an image or deploying a Container App would be a separate, billable change and was not authorized or performed here.

### 3. Key Vault certificate metadata is blocked by the firewall

The portal's certificate-list request was rejected by the Key Vault firewall. The saved 19 November inventory reported zero certificates in the pilot vault, but that count was not independently revalidated on 23 November. The portal overview showed soft delete enabled and purge protection disabled. No secret values were accessed.

**Follow-up:** Recheck metadata from the authorized scanner host/network if its configured allow rule is still valid. Do not add the browser client's address or weaken the firewall to complete this scan. Review whether purge protection should be enabled through the normal owner-approved change process.

### 4. The selected Azure subscription is not yet confirmed as production

The currently selected directory/subscription differs from identifiers in earlier notes. A name-based search or one-directory portal view cannot establish that the actual Kinetic Core deployment is absent or covered.

**Follow-up:** Have the deployment owner confirm the target tenant, subscription, and production resource identifiers before drawing conclusions about production.

### 5. Existing scan evidence needs human review

The source scan indexed 81 files. The cryptography scanner plugin recognized no supported assets; a manual source review recorded SHA-256 use for deterministic chunk identifiers, truncated to 16 hexadecimal characters (64 bits), at `knowledge/chunker/semantic_chunker.py:62`. The local model's output is triage only; collision relevance, migration priority, secrecy lifetime, and human disposition remain unknown.

The repository SBOM contains 90 components. The unpinned root and function dependency manifests produced resolution snapshots of 55 and 31 packages, respectively; these are not deployed-version attestations. The locally built API image SBOM contains 3,039 entries, including `cryptography` 50.0.2 and OpenSSL 3.5.7. This is inventory, not a vulnerability scan, and the image has not been verified in ACR.

**Follow-up:** Complete human disposition and a misclassification log before publishing counts or assigning severity. Do not describe the theoretical Grover observation alone as an actionable vulnerability.

## Coverage status

| Scan area | Status | Evidence / limitation |
|---|---|---|
| Source and cryptographic-use review | Partial | Local scan from 19 Nov; manual SHA-256 observation needs human review. |
| Repository software inventory | Local inventory complete | 90-component SBOM; dependency resolutions are unpinned snapshots. |
| Kinetic Core API container | Local inventory only | Local image SBOM exists; Azure registry has no listed repository. |
| Azure resource inventory | Partial, selected subscription only | Portal view on 23 Nov; production linkage and other directories are unverified. |
| Azure configuration | Partial | A subset of settings comes from the 19 Nov pilot inventory; no fresh ARM export. |
| Key Vault certificate metadata | Not verified on 23 Nov | Firewall denied the portal request; earlier pilot inventory reported zero certificates. |
| Client-facing TLS | Not scanned | No production endpoint was confirmed or tested. No pilot Container App endpoint exists. |
| AI triage and human review | Partial | Local Ollama screening only; human review remains pending. |

## Method and safety boundaries

- Azure inspection in this update was read-only. No resource, network rule, role, secret, or deployment setting was changed.
- No production deployment workflow or production Bicep entry point was run or modified.
- No Azure OpenAI or hosted-model triage was used; local Ollama was used in the earlier scan.
- Secret values and private-key material were not requested or read.
- Raw scan outputs remain outside the repository. This report omits tenant/subscription IDs, resource IDs, vault endpoints, and other internal identifiers.

## Next steps

1. Reconcile the selected Azure directory/subscription with the Kinetic Core deployment owner.
2. Review current pilot costs and decide, with the owner, whether to retain or clean up the expired pilot resource group.
3. If authorized, refresh the read-only Azure inventory from the approved scanner environment and collect Key Vault certificate metadata without reading secrets.
4. Confirm whether an ACR image and an approved endpoint are required. Obtain separate approval before pushing or deploying anything.
5. Complete human review of the SHA-256 observation and reconcile the final coverage/counts.

**Conclusion:** This is an Azure-enriched interim report, not a readiness certification or a production scan. Azure inventory improved, but the deployed API image, Key Vault certificate inventory, approved endpoint TLS, production environment linkage, and final human review remain incomplete.
