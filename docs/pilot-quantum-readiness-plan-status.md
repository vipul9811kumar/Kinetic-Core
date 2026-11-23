# Quantum-Readiness Pilot: Plan Status (Nov 19, 2026)

Full plans (pilot, build, test) and the Issue 15 decision: https://claude.ai/artifact/XoG3E9PC67mwtrnFpBhoWf

## Decision
- Issue 15: NO-GO for Mon Nov 23. CONDITIONAL GO for Mon Nov 30, depending on a gate check Fri Nov 27.
- Scope for Issue 15: Kinetic Core only. VoltLedger is "next" and stays out of the counts.
- Needs a one-time surge of about 8.75 pilot hours (estimate) from Nov 20 to Nov 27. Thanksgiving is kept free.
- If the gate fails: Issue 15 moves to Dec 7, with a build-in-public post on Nov 30 that has no counts.

## Environment (confirmed Nov 19)
- Kinetic Core code: GitHub, Python. sonar-cryptography fully supports Python.
- Scan host: VK's OCI VM, reached via VS Code Remote-SSH. All scans and triage run there. Azure Cloud Shell is the fallback for the Key Vault step if a firewall blocks it.

## Pipeline (summary)
Scanners (sonar-cryptography, CBOMkit-theia, cdxgen/Syft, az exports, testssl.sh) → merged CycloneDX CBOM → Azure OpenAI GPT-4 triage (evidence-bound, "unknown" allowed) → 100% human review + misclassification log → publish filter (counts and patterns only).

## Open questions
Test Azure subscription and Reader access, the triage model deployment, VoltLedger's stack, the device hardware for the TLS benchmark, and the Issue 16 date.
