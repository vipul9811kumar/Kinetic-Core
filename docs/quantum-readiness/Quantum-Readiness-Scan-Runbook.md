# Quantum-Readiness Scan Runbook

## Purpose and current status

This runbook describes a reproducible scan and review process for Kinetic Core. It is designed to produce a private evidence set and a separate, reviewed aggregate suitable for a newsletter or social post.

The pipeline has five stages:

1. Scanners write unmodified raw evidence.
2. Normalizers and a merger produce one CycloneDX 1.6 CBOM.
3. An approved LLM proposes one classification per asset.
4. A human reviews every asset and records corrections.
5. A publication filter emits only reviewed, sanitized aggregates.

The current repository implements private per-run setup, merging of already-normalized CycloneDX 1.6 CBOM inputs, an auxiliary Syft/Azure coverage inventory, a fail-closed Azure-only triage provider, complete review validation, and an aggregate-only publication draft generator. The triage provider has not been used because an approved Azure GPT-4 deployment is not confirmed. Format-specific CBOM adapters and Key Vault/TLS export handling are still pending; the publication draft is never marked approved for external use. Do not treat the full pipeline as complete until those stages and the remaining coverage tests pass.

The latest Azure-enriched status and limitations are in the [pilot status](../pilot-quantum-readiness-plan-status.md) and [interim scan report](./Kinetic-Core-Quantum-Readiness-Detailed-Scan-Report.md).

## Safety and data handling

- Keep runs under `qr-pilot/run-YYYY-MM-DD/`. The repository `.gitignore` excludes each run folder. Do not force-add run artifacts.
- Treat `raw/`, CBOM occurrences, triage inputs/outputs, review decisions, misclassification notes, and TLS measurements as private. They can contain source paths, hostnames, IPs, resource IDs, certificate subjects, or configuration details.
- Never collect or send private keys, certificate bodies, connection strings, secret values, telemetry, or customer data. Certificate metadata is sufficient for the planned inventory.
- Do not run scans against production endpoints until the owner confirms the exact endpoint list and authorizes the test. Do not probe a service just because it appears in an inventory.
- The current Azure account has Owner access, but this runbook authorizes no provisioning, role changes, firewall changes, image pushes, deployments, or cleanup.
- The selected Azure directory/subscription has not been confirmed as the Kinetic Core production environment. Keep pilot and production claims separate.
- Azure OpenAI was not used in the existing scan, and the currently selected subscription did not show an Azure OpenAI resource. Confirm an approved GPT-4 deployment before use. The scan triage provider must fail closed unless an Azure endpoint and deployment are configured; it must never fall back to the direct OpenAI API.
- The application helper in `agents/client.py` can fall back to direct OpenAI when Azure is not configured. Do not reuse it for scan triage.
- No raw evidence or individual asset finding is suitable for public release. Publish only after the review and publication gates below pass.

## Run layout and setup

From the repository root:

```bash
python3 -m tools.quantum_readiness.run_setup --date 2026-11-23
```

The command refuses to overwrite an existing run. It creates:

```text
qr-pilot/
  run-YYYY-MM-DD/
    raw/          # untouched scanner and Azure exports
    inputs.json   # relative paths and provenance for CBOM inputs
    inventory-inputs.json # relative paths for auxiliary inventories
    cbom.json     # merged CycloneDX 1.6 output
    inventory.json # private Syft and Azure coverage inventory
    triage-inputs.jsonl # allowlisted metadata and redacted snippets
    triage.jsonl  # one model response per asset
    review.csv    # one human verdict per asset
    misclass.csv  # every model correction
    publication-summary.json # sanitized aggregate draft; approval still required
    timelog.csv   # date, step, minutes, manual|automated
    tools.txt     # exact tool versions, commands, and image digests
```

Record each tool's exact version, command, relevant options, platform, and container image digest in `tools.txt` before running it. Do not substitute an approximate version. Record the source commit separately from the tool version.

The five `scan_area` values are:

- `code-and-libraries`
- `container-images`
- `azure-config`
- `key-vault`
- `endpoint-tls`

Record explicit coverage even when an area yields no assets. "No crypto found" is a result only when the area was actually scanned and its denominator is known.

## Collection and normalization

Keep the original output from each scanner in `raw/` unchanged. The current merger takes a manifest of CycloneDX 1.6 BOM files whose components are already typed as `cryptographic-asset`:

```json
{
  "run_id": "run-2026-11-23",
  "inputs": [
    {
      "path": "raw/source.cbom.json",
      "source_tool": "sonar-cryptography",
      "scan_area": "code-and-libraries"
    }
  ]
}
```

Paths must remain inside that run directory. The merger rejects non-CycloneDX-1.6 inputs, unsupported component types, missing evidence locations, and invalid scan areas instead of silently dropping them.

Run the merge with:

```bash
python3 -m tools.quantum_readiness.merge_cbom \
  --manifest qr-pilot/run-2026-11-23/inputs.json \
  --output qr-pilot/run-2026-11-23/cbom.json
```

The output uses a stable asset reference based on the asset name and `cryptoProperties`. Duplicate assets are consolidated; evidence occurrences are deduplicated by location and line/offset while distinct locations remain. Each merged asset retains all distinct `source_tool` and `scan_area` CycloneDX properties.

The merger is not a scanner and does not infer cryptographic algorithms from a library name or Azure resource type. Format-specific CBOM adapters must map each real export to explicit evidence-backed assets. If an exporter does not expose an algorithm or key-exchange group, represent that fact as unknown; do not fill it in from assumptions.

Before adding format-specific CBOM adapters, retain one representative, sanitized sample from each source format. Current examples include a manual SHA-256 CBOM, Syft SBOMs, and an Azure pilot inventory. A CBOMkit-theia image export and a testssl.sh JSON export were not present in the current run artifacts, so their mappings remain to be verified.

The auxiliary inventory adapter processes Syft CycloneDX SBOMs and the saved Azure inventory without converting them into CBOM assets:

```json
{
  "syft_inputs": [
    {
      "path": "raw/kinetic-core-api-image.sbom.json",
      "scan_area": "container-images"
    }
  ],
  "azure_inventory": "raw/azure-pilot-config-inventory.json"
}
```

Run it with:

```bash
python3 -m tools.quantum_readiness.inventory_adapter \
  --manifest qr-pilot/run-2026-11-23/inventory-inputs.json \
  --output qr-pilot/run-2026-11-23/inventory.json
```

Syft library-name matches are candidate leads only; file entries are excluded, and no algorithm or runtime use is inferred. Azure resource rows retain only names, types, IDs when available, and locations; tags and SKU/configuration fields are omitted. The inventory is still private data. The saved export lacks resource IDs, so its names are not stable global identifiers. A historical zero count is not current verification, and denominator mismatches fail rather than being silently normalized. This auxiliary inventory does not replace the CBOM or prove that a service uses a specific cryptographic algorithm.

## LLM triage

The model proposes a classification; it does not determine truth, severity, or publication eligibility. Send only the allowlisted metadata and a redacted snippet (maximum 1,000 characters) needed to classify an asset. Do not send raw scanner logs or full resource exports.

Use `tools.quantum_readiness.triage.AzureOpenAITriage` only after the owner confirms the Azure endpoint, key, and approved GPT-4 deployment. The provider requires `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_QR_TRIAGE_DEPLOYMENT`; it has no direct-OpenAI fallback and rejects non-HTTPS endpoints. The deployment setting is deliberately separate from the application's default deployment. No scan triage request has been sent to Azure OpenAI.

Set temperature to zero, request JSON only, validate the exact response schema, require one record per asset, and reject any `evidence_ref` not present in that asset's input locations. The validator also checks enum values, field types, and the 25-word reason limit. Record the approved deployment identifier, prompt version, timestamp, and input asset ID in the private run log.

Populate `triage-inputs.jsonl` with one allowlisted JSON object per asset using the fields accepted by `tools.quantum_readiness.triage.build_messages`. Redact the snippet before writing it. After Azure triage is approved and configured, run:

```json
{"asset_id":"<CBOM bom-ref>","asset_type":"algorithm","algorithm_or_protocol":"SHA-256","key_size_or_curve":"unknown","library":"unknown","scan_area":"code-and-libraries","source_tool":"manual-review","locations":["src/crypto.py:10"],"redacted_snippet":"<redacted snippet>","system_context":"device telemetry"}
```

```bash
python3 -m tools.quantum_readiness.triage \
  --inputs qr-pilot/run-2026-11-23/triage-inputs.jsonl \
  --output qr-pilot/run-2026-11-23/triage.jsonl
```

The command validates every input before making requests, requires unique asset IDs, and writes the output only after every response passes validation. A failed request or invalid record leaves any previous `triage.jsonl` untouched.

Suggested classification rules:

- RSA, DSA, DH, ECDH, ECDSA, EdDSA, and X25519 used for key exchange or signatures are quantum-relevant to Shor's algorithm.
- AES-128 is not currently classified as broken; note Grover's theoretical quadratic search speedup and prefer AES-256 for long-lived confidentiality where justified.
- AES-256, SHA-256/384/512, and HMAC are not currently classified as quantum-vulnerable solely because of quantum computing.
- ML-KEM, ML-DSA, SLH-DSA, and a verified hybrid such as X25519MLKEM768 are not classified as quantum-vulnerable by this rubric.
- MD5, SHA-1, TLS below 1.2, 3DES, and RC4 are recorded as classical weaknesses separately from quantum exposure.
- Provider-managed cryptography with no visible configuration is `unknown`; record the provider as owner where evidence supports that attribution.
- A TLS version alone is not an algorithm. Record the negotiated key-exchange group and signature algorithm when observable. A TLS 1.2 endpoint that is proven to negotiate classical ECDHE can be marked quantum-relevant; if the provider hides the group, do not claim a group that was not observed.

Suggested priority:

- `P1`: quantum-vulnerable and data must remain secret for at least five years, or a long-lived trust anchor such as a root CA or device identity.
- `P2`: quantum-vulnerable with a shorter secrecy lifetime.
- `P3`: not quantum-vulnerable under this rubric, or only a classical cleanup.
- `unknown`: evidence is insufficient to assign a defensible priority.

Required JSONL fields:

```json
{"asset_id":"...","quantum_vulnerable":"yes|no|unknown","threat":"shor|grover|none|unknown","classical_weakness":false,"data_secrecy_lifetime":"<1y|1-5y|5-10y|>10y|unknown","migration_priority":"P1|P2|P3|unknown","evidence_ref":"...","reason":"...","confidence":"high|medium|low"}
```

The validator must check field types, enum values, reason length (25 words maximum), valid evidence references, one output per input asset, and no duplicate or missing asset IDs.

## Human review and misclassification tracking

`review.csv` has one row for every CBOM asset. Use exactly one verdict: `agree`, `correct`, or `unknown`. A reviewer records the evidence checked, corrected values when applicable, and minutes spent. No row may be skipped.

For `correct`, enter at least one changed corrected value and a reviewer reason. For `unknown`, explain why the evidence did not support a decision. Correctable fields include quantum status, threat, classical weakness, secrecy lifetime, priority, evidence reference, and confidence. `agree` rows leave corrected fields blank. Evidence checked and minutes spent are required for every verdict.

Run the review gate after triage and human review:

```bash
python3 -m tools.quantum_readiness.review \
  --cbom qr-pilot/run-2026-11-23/cbom.json \
  --triage qr-pilot/run-2026-11-23/triage.jsonl \
  --review qr-pilot/run-2026-11-23/review.csv \
  --misclass qr-pilot/run-2026-11-23/misclass.csv
```

It fails if any CBOM asset lacks exactly one triage record or review row, if a review's stored model call differs from triage, if corrected values are invalid, or if a correction lacks a correctly tagged misclassification entry. For example, `no` corrected to `yes` requires `false-safe`; changed lifetime, priority, or evidence references require their matching error categories. A high-confidence model call reviewed as `unknown` requires `overconfident-unknown`. A passing gate is necessary but does not itself authorize publication.

Every correction also gets a `misclass.csv` row. Use one or more error categories:

- `false-safe`: model said no, reviewed result is yes
- `false-vulnerable`: model said yes, reviewed result is no
- `wrong-lifetime`
- `wrong-priority`
- `hallucinated-evidence`
- `overconfident-unknown`

Record how an error was caught: seeded item, gold set, evidence check, or second run. Keep the notes private and factual. Do not let a model-generated explanation substitute for evidence.

## Tests and predeclared pass criteria

### Inventory completeness

1. On a throwaway test branch or isolated fixture, seed six known examples: RSA-2048 key generation, ECDSA signing, a TLS 1.0 setting, a self-signed certificate in a test image, MD5, and AES-256-GCM. Pass only if all six are found at the expected locations. Never merge the intentionally weak fixtures into the application branch or production image.
2. Before scanning, enumerate every in-scope repository, ACR image, Azure resource, Key Vault certificate, and owner-approved public endpoint. Reconcile each denominator item to one or more CBOM occurrences or an explicit scanned-with-no-crypto result. Report `covered / listed`; explain exclusions.
3. Compare sonar-cryptography results with targeted source searches and the SBOM's crypto-library inventory. Manually review anything found by only one source.
4. Record non-Java/Python/Go source as a language coverage gap and label it pattern-scanned-only if no suitable semantic scanner was run.

### Triage accuracy

1. Create a 15-20 item gold set spanning the five scan areas and including the seeded items. Label it before viewing model output.
2. Review every model call against its evidence.
3. Run triage twice with identical inputs. Any changed classification is low-confidence and requires a second review.
4. Report measured gold-set agreement, false-safe count (target: zero), unknown rate, and one or two reviewed misclassifications. Do not estimate these values.

### Post-quantum TLS benchmark (Issue 17; separate approval required)

Use only a test subscription and a TLS terminator the project controls. Compare classical X25519 with X25519MLKEM768; keep certificate and signature settings the same and state that they remain classical.

- Use a simulator on the field-device hardware class if available. Otherwise label the result as not measured on device hardware.
- Run at least 1,000 full handshakes per group, disable session resumption, warm up first, alternate groups, and repeat under predeclared latency/loss conditions.
- Measure handshake p50/p95, ClientHello/ServerHello byte sizes, client CPU and peak memory, and server CPU. Record versions, VM size, region, date, and raw CSVs privately.
- Verify that a client without hybrid support still connects via the intended classical fallback.
- Do not test a production endpoint or deploy a test terminator without separate approval. Any public benchmark data must be de-identified and reviewed before release.

Microsoft's current [IoT Hub TLS support documentation](https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-tls-support) describes TLS 1.2 enforcement, classic ECDHE cipher suites, and TLS-version/cipher metrics. The [Container Apps ingress documentation](https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview) documents TLS 1.2/1.3 termination; its [ingress settings](https://learn.microsoft.com/en-us/azure/container-apps/ingress-how-to) do not expose a named key-exchange-group or cipher-suite selector. These managed services are therefore not a controllable endpoint for comparing named groups through documented settings. Confirm current service capabilities again before Issue 17; do not infer a provider's negotiated group from TLS version alone.

## Publication gate

Before producing newsletter or social-post material:

1. Require one reviewed row per CBOM asset, zero missing reviews, and validated evidence references.
2. Derive counts only from reviewed values, never directly from scanner or model output.
3. Remove hostnames, IPs, certificate subjects/thumbprints, resource IDs, private source paths, account names, and configuration values.
4. Do not publish unpatched weakness details, raw snippets, scanner logs, prompts containing private data, or model/reviewer notes.
5. Publish only approved category counts, patterns, methodology, limitations, and scrubbed generic examples.
6. Preserve the private run and the sanitized publication artifact separately. Do not make raw TLS captures public without a separate de-identification review.

After the review validator passes, generate a sanitized aggregate draft with:

```bash
python3 -m tools.quantum_readiness.publication \
  --cbom qr-pilot/run-2026-11-23/cbom.json \
  --triage qr-pilot/run-2026-11-23/triage.jsonl \
  --review qr-pilot/run-2026-11-23/review.csv \
  --misclass qr-pilot/run-2026-11-23/misclass.csv \
  --output qr-pilot/run-2026-11-23/publication-summary.json
```

The output contains only counts, generic patterns, and limitations; it omits asset-level fields and never includes raw tool labels. Source-tool aliases are mapped to a fixed public vocabulary, with unrecognized values grouped as `other`. Counts by source tool and scan area may overlap. The generator always sets `eligible_for_external_publication` to false; it does not establish inventory completeness, gold-set accuracy, or human publication approval.

Inventory-completeness validation and human publication approval remain outstanding. Keep every generated summary provisional and private until those gates pass.
