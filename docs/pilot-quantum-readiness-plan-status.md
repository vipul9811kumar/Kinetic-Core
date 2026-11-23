# Quantum-Readiness Pilot: Plan Status (updated Nov 23, 2026)

Full plans (pilot, build, test) and the Issue 15 decision: https://claude.ai/artifact/XoG3E9PC67mwtrnFpBhoWf

## Decision
- Issue 15: NO-GO for Mon Nov 23. CONDITIONAL GO for Mon Nov 30, depending on a gate check Fri Nov 27.
- Scope for Issue 15: Kinetic Core only. VoltLedger is "next" and stays out of the counts.
- Needs a one-time surge of about 8.75 pilot hours (estimate) from Nov 20 to Nov 27. Thanksgiving is kept free.
- If the gate fails: Issue 15 moves to Dec 7, with a build-in-public post on Nov 30 that has no counts.

## Environment (confirmed Nov 19)
- Kinetic Core code: GitHub, Python. sonar-cryptography fully supports Python.
- Scan host: VK's OCI VM, reached via VS Code Remote-SSH. All scans and triage run there. Azure Cloud Shell is the fallback for the Key Vault step if a firewall blocks it.

## Planned pipeline (summary)
Scanners (sonar-cryptography, CBOMkit-theia, cdxgen/Syft, Azure exports, testssl.sh) → merged CycloneDX CBOM → evidence-bound triage ("unknown" allowed) → 100% human review + misclassification log → publish filter (counts and patterns only). The completed local pass used Ollama on the scan VM, not Azure OpenAI; human review is still pending.

## Open questions
Confirm the target Azure directory/subscription with the Kinetic Core deployment owner, approve the triage-model approach, identify VoltLedger's stack and TLS benchmark hardware, and set the Issue 16 date.

## Azure scan update (Nov 23, 2026)
- A read-only Azure Portal review found two resource groups and 13 resources in the selected directory: 12 in the quantum pilot resource group and one Azure DevOps organization resource outside the pilot.
- The pilot resource group is populated; the earlier report/runbook statements that it was empty are stale. The selected directory/subscription still needs confirmation against the actual Kinetic Core production environment.
- The pilot ACR currently has no listed repositories, and no Container App was visible. No Azure API image or pilot endpoint has been verified.
- Key Vault certificate metadata could not be rechecked because the current portal client was blocked by the vault firewall. No firewall or resource settings were changed.
- The pilot expiry tag recorded in the Nov 19 inventory is Nov 20, 2026. Review costs and retention with the subscription owner; no cleanup was performed.
- See the [Azure-enriched interim report](./quantum-readiness/Kinetic-Core-Quantum-Readiness-Detailed-Scan-Report.md). It supersedes the earlier Azure-status statements but not the pending human-review and Issue 15 gates.
- See the [scan runbook](./quantum-readiness/Quantum-Readiness-Scan-Runbook.md) for private run setup, CBOM merging, review rules, tests, and publication controls.
