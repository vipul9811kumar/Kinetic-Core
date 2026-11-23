"""Create a sanitized draft aggregate from a fully reviewed scan run."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.quantum_readiness.merge_cbom import SCAN_AREAS
from tools.quantum_readiness.review import (
    load_validated_review_run,
    validate_review_data,
)
from tools.quantum_readiness.triage import (
    LIFETIME_VALUES,
    PRIORITY_VALUES,
    QUANTUM_VALUES,
    THREAT_VALUES,
)


SOURCE_TOOL_ALIASES = {
    "sonar-cryptography": "sonar-cryptography",
    "cbomkit-theia": "cbomkit-theia",
    "syft": "syft",
    "azure-cli": "azure-inventory",
    "azure-pilot-config-inventory": "azure-inventory",
    "azure pilot configuration inventory": "azure-inventory",
    "az resource list": "azure-inventory",
    "testssl": "testssl",
    "testssl.sh": "testssl",
    "manual-gap-review": "manual-review",
    "manual-review": "manual-review",
}
PUBLIC_SOURCE_TOOLS = frozenset(
    {
        "sonar-cryptography",
        "cbomkit-theia",
        "syft",
        "azure-inventory",
        "testssl",
        "manual-review",
        "other",
    }
)


def _asset_provenance(component: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    properties = component.get("properties")
    if not isinstance(properties, list):
        raise ValueError("CBOM asset properties must be an array")
    source_tools: set[str] = set()
    scan_areas: set[str] = set()
    for prop in properties:
        if (
            not isinstance(prop, dict)
            or not isinstance(prop.get("name"), str)
            or not isinstance(prop.get("value"), str)
        ):
            raise ValueError("CBOM asset property must have string name and value")
        name = prop["name"]
        value = prop["value"].strip()
        if name == "source_tool":
            if not value:
                raise ValueError("CBOM asset source_tool must not be empty")
            source_tools.add(
                SOURCE_TOOL_ALIASES.get(value.casefold(), "other")
            )
        elif name == "scan_area":
            if value not in SCAN_AREAS:
                raise ValueError(f"invalid CBOM scan_area: {value!r}")
            scan_areas.add(value)
    if not source_tools or not scan_areas:
        raise ValueError("CBOM assets must include source_tool and scan_area properties")
    return source_tools, scan_areas


def _effective_classification(
    review: Mapping[str, str], model_call: Mapping[str, Any]
) -> dict[str, Any]:
    verdict = review["verdict"]
    if verdict == "unknown":
        return {
            "quantum_vulnerable": "unknown",
            "threat": "unknown",
            "classical_weakness": "unknown",
            "data_secrecy_lifetime": "unknown",
            "migration_priority": "unknown",
        }

    quantum_vulnerable = (
        review["corrected_quantum_vulnerable"].strip()
        or model_call["quantum_vulnerable"]
    )
    threat = review["corrected_threat"].strip() or model_call["threat"]
    classical_weakness = review["corrected_classical_weakness"].strip()
    if classical_weakness:
        classical_weakness = "yes" if classical_weakness == "true" else "no"
    else:
        classical_weakness = "yes" if model_call["classical_weakness"] else "no"
    lifetime = (
        review["corrected_data_secrecy_lifetime"].strip()
        or model_call["data_secrecy_lifetime"]
    )
    priority = (
        review["corrected_migration_priority"].strip()
        or model_call["migration_priority"]
    )

    if quantum_vulnerable not in QUANTUM_VALUES:
        raise ValueError("invalid reviewed quantum_vulnerable value")
    if threat not in THREAT_VALUES:
        raise ValueError("invalid reviewed threat value")
    if lifetime not in LIFETIME_VALUES:
        raise ValueError("invalid reviewed data_secrecy_lifetime value")
    if priority not in PRIORITY_VALUES:
        raise ValueError("invalid reviewed migration_priority value")
    return {
        "quantum_vulnerable": quantum_vulnerable,
        "threat": threat,
        "classical_weakness": classical_weakness,
        "data_secrecy_lifetime": lifetime,
        "migration_priority": priority,
    }


def build_publication_summary(
    cbom: Mapping[str, Any],
    triage_records: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, str]],
    misclass_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Build aggregates after revalidating the complete review set."""
    review_summary = validate_review_data(
        cbom, triage_records, review_rows, misclass_rows
    )
    if review_summary["assets"] == 0:
        raise ValueError("cannot create a publication summary from an empty CBOM")

    reviews_by_id = {row["asset_id"]: row for row in review_rows}
    triage_by_id = {record["asset_id"]: record for record in triage_records}
    quantum_counts: Counter[str] = Counter()
    threat_counts: Counter[str] = Counter()
    classical_counts: Counter[str] = Counter()
    lifetime_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for component in cbom["components"]:
        asset_id = component["bom-ref"]
        review = reviews_by_id[asset_id]
        model_call = triage_by_id[asset_id]
        classification = _effective_classification(review, model_call)
        quantum_counts[classification["quantum_vulnerable"]] += 1
        threat_counts[classification["threat"]] += 1
        classical_counts[classification["classical_weakness"]] += 1
        lifetime_counts[classification["data_secrecy_lifetime"]] += 1
        priority_counts[classification["migration_priority"]] += 1
        asset_source_tools, asset_scan_areas = _asset_provenance(component)
        for source_tool in asset_source_tools:
            source_counts[source_tool] += 1
        for scan_area in asset_scan_areas:
            area_counts[scan_area] += 1

    misclassification_counts = Counter(
        row["error_type"] for row in misclass_rows
    )
    total = review_summary["assets"]
    model_unknown_count = sum(
        record["quantum_vulnerable"] == "unknown" for record in triage_records
    )
    model_unknown_rate = model_unknown_count / total
    reviewed_unknown_rate = quantum_counts["unknown"] / total
    agreement_rate = review_summary["agree"] / total
    patterns = []
    if quantum_counts["yes"]:
        patterns.append(
            "Reviewed assets include classical cryptography classified as "
            "quantum-vulnerable under the stated rubric."
        )
    if classical_counts["yes"]:
        patterns.append("Reviewed assets include classical-cryptography cleanup items.")
    if quantum_counts["unknown"]:
        patterns.append(
            "Some reviewed assets remain unclassified because the evidence was "
            "insufficient for a defensible decision."
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "draft_requires_manual_approval",
        "eligible_for_external_publication": False,
        "counts": {
            "assets_total": total,
            "assets_reviewed": total,
            "review_verdict": {
                verdict: review_summary[verdict]
                for verdict in ("agree", "correct", "unknown")
            },
            "quantum_vulnerable": {
                value: quantum_counts[value]
                for value in ("yes", "no", "unknown")
            },
            "threat": {
                value: threat_counts[value]
                for value in ("shor", "grover", "none", "unknown")
            },
            "classical_weakness": {
                value: classical_counts[value] for value in ("yes", "no", "unknown")
            },
            "data_secrecy_lifetime": {
                value: lifetime_counts[value]
                for value in ("<1y", "1-5y", "5-10y", ">10y", "unknown")
            },
            "migration_priority": {
                value: priority_counts[value]
                for value in ("P1", "P2", "P3", "unknown")
            },
            "by_scan_area": {
                area: area_counts[area] for area in sorted(SCAN_AREAS)
            },
            "by_source_tool": {
                source: source_counts[source]
                for source in sorted(PUBLIC_SOURCE_TOOLS)
            },
            "misclassifications": {
                error_type: misclassification_counts[error_type]
                for error_type in sorted(
                    {
                        "false-safe",
                        "false-vulnerable",
                        "wrong-lifetime",
                        "wrong-priority",
                        "hallucinated-evidence",
                        "overconfident-unknown",
                    }
                )
            },
            "false_safe_count": misclassification_counts["false-safe"],
            "model_unknown_rate": round(model_unknown_rate, 4),
            "reviewed_quantum_unknown_rate": round(reviewed_unknown_rate, 4),
            "model_human_agreement_rate": round(agreement_rate, 4),
        },
        "patterns": patterns,
        "generic_examples": [],
        "limitations": [
            "Counts cover this reviewed CBOM only and do not prove inventory completeness.",
            "Source-tool and scan-area counts can overlap and are not additive.",
            "Gold-set agreement was not measured by this summary.",
            "External publication requires separate human approval.",
        ],
    }


def create_publication_summary(
    cbom_path: Path,
    triage_path: Path,
    review_path: Path,
    misclass_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    cbom, triage, reviews, misclass, _ = load_validated_review_run(
        cbom_path, triage_path, review_path, misclass_path
    )
    run_root = cbom_path.resolve(strict=True).parent.resolve()
    output_path = output_path.resolve()
    raw_dir = (run_root / "raw").resolve()
    if (
        not output_path.is_relative_to(run_root)
        or output_path.is_relative_to(raw_dir)
        or output_path.name != "publication-summary.json"
    ):
        raise ValueError(
            "publication output must be publication-summary.json inside the run "
            "directory and outside raw/"
        )
    input_paths = {
        cbom_path.resolve(),
        triage_path.resolve(strict=True),
        review_path.resolve(strict=True),
        misclass_path.resolve(strict=True),
    }
    if output_path in input_paths:
        raise ValueError("publication output must not overwrite review inputs")

    summary = build_publication_summary(cbom, triage, reviews, misclass)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary_path = Path(stream.name)
        try:
            json.dump(summary, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cbom", type=Path, required=True)
    parser.add_argument("--triage", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--misclass", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = create_publication_summary(
            args.cbom,
            args.triage,
            args.review,
            args.misclass,
            args.output,
        )
    except ValueError as error:
        parser.error(str(error))
    print(
        f"Wrote sanitized draft for {result['counts']['assets_total']} "
        "reviewed assets; external publication approval is still required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
