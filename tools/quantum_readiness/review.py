"""Validate complete human review and misclassification records."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.quantum_readiness.triage import (
    CONFIDENCE_VALUES,
    LIFETIME_VALUES,
    PRIORITY_VALUES,
    QUANTUM_VALUES,
    THREAT_VALUES,
    validate_triage_batch,
)


REVIEW_COLUMNS = (
    "asset_id",
    "model_call",
    "verdict",
    "corrected_quantum_vulnerable",
    "corrected_threat",
    "corrected_classical_weakness",
    "corrected_data_secrecy_lifetime",
    "corrected_migration_priority",
    "corrected_evidence_ref",
    "corrected_confidence",
    "reviewer_reason",
    "evidence_checked",
    "minutes_spent",
)
MISCLASS_COLUMNS = (
    "asset_id",
    "error_type",
    "caught_by",
    "details",
    "minutes_spent",
)
REVIEW_VERDICTS = frozenset({"agree", "correct", "unknown"})
MISCLASS_TYPES = frozenset(
    {
        "false-safe",
        "false-vulnerable",
        "wrong-lifetime",
        "wrong-priority",
        "hallucinated-evidence",
        "overconfident-unknown",
    }
)
CAUGHT_BY_VALUES = frozenset(
    {"seeded-item", "gold-set", "evidence-check", "second-run"}
)
CORRECTED_FIELDS = (
    "corrected_quantum_vulnerable",
    "corrected_threat",
    "corrected_classical_weakness",
    "corrected_data_secrecy_lifetime",
    "corrected_migration_priority",
    "corrected_evidence_ref",
    "corrected_confidence",
)


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"blank {label} record at line {line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid JSON in {label} at line {line_number}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"{label} record at line {line_number} must be an object")
            records.append(record)
    return records


def _resolve_run_file(path: Path, run_root: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    raw_dir = (run_root / "raw").resolve()
    if (
        not resolved.is_relative_to(run_root)
        or resolved.is_relative_to(raw_dir)
        or not resolved.is_file()
    ):
        raise ValueError(f"{label} must be a file in the run directory outside raw/")
    return resolved


def _asset_locations(cbom: Mapping[str, Any]) -> dict[str, list[str]]:
    components = cbom.get("components")
    if not isinstance(components, list):
        raise ValueError("CBOM must contain a components array")
    assets: dict[str, list[str]] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict) or component.get("type") != "cryptographic-asset":
            raise ValueError(f"CBOM component {index} is not a cryptographic asset")
        asset_id = component.get("bom-ref")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"CBOM component {index} has no bom-ref")
        if asset_id in assets:
            raise ValueError(f"duplicate CBOM asset ID: {asset_id}")
        evidence = component.get("evidence")
        occurrences = evidence.get("occurrences") if isinstance(evidence, dict) else None
        if not isinstance(occurrences, list) or not occurrences:
            raise ValueError(f"CBOM asset {asset_id} has no evidence occurrences")
        locations = [
            item.get("location")
            for item in occurrences
            if isinstance(item, dict) and isinstance(item.get("location"), str)
        ]
        if len(locations) != len(occurrences) or any(
            not location.strip() for location in locations
        ):
            raise ValueError(f"CBOM asset {asset_id} has an invalid evidence location")
        assets[asset_id] = list(dict.fromkeys(locations))
    return assets


def _read_csv(path: Path, expected_columns: Sequence[str], label: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(expected_columns):
            raise ValueError(f"{label} columns do not match the required schema")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{label} contains a malformed row")
    return rows


def _minutes(value: str, label: str) -> int:
    try:
        minutes = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a non-negative integer") from error
    if minutes < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return minutes


def _validate_corrected_values(
    row: Mapping[str, str], model_call: Mapping[str, Any], locations: Sequence[str]
) -> tuple[bool, set[str]]:
    enum_fields = (
        ("corrected_quantum_vulnerable", "quantum_vulnerable", QUANTUM_VALUES),
        ("corrected_threat", "threat", THREAT_VALUES),
        (
            "corrected_data_secrecy_lifetime",
            "data_secrecy_lifetime",
            LIFETIME_VALUES,
        ),
        ("corrected_migration_priority", "migration_priority", PRIORITY_VALUES),
        ("corrected_confidence", "confidence", CONFIDENCE_VALUES),
    )
    has_correction = False
    required_errors: set[str] = set()
    for csv_field, model_field, allowed in enum_fields:
        value = row[csv_field].strip()
        if value:
            if value not in allowed:
                raise ValueError(f"invalid {csv_field}: {value!r}")
            if value == model_call[model_field]:
                raise ValueError(f"{csv_field} does not change the model value")
            has_correction = True
            if model_field == "data_secrecy_lifetime":
                required_errors.add("wrong-lifetime")
            elif model_field == "migration_priority":
                required_errors.add("wrong-priority")
            elif model_field == "quantum_vulnerable":
                original = model_call[model_field]
                if original == "no" and value == "yes":
                    required_errors.add("false-safe")
                elif original == "yes" and value == "no":
                    required_errors.add("false-vulnerable")
                elif original != "unknown" and value == "unknown":
                    if model_call["confidence"] == "high":
                        required_errors.add("overconfident-unknown")

    classical_value = row["corrected_classical_weakness"].strip()
    if classical_value:
        if classical_value not in {"true", "false"}:
            raise ValueError("corrected_classical_weakness must be true or false")
        if (classical_value == "true") is model_call["classical_weakness"]:
            raise ValueError("corrected_classical_weakness does not change the model value")
        has_correction = True

    evidence_ref = row["corrected_evidence_ref"].strip()
    if evidence_ref:
        if evidence_ref not in locations:
            raise ValueError("corrected_evidence_ref is not a CBOM occurrence")
        if evidence_ref == model_call["evidence_ref"]:
            raise ValueError("corrected_evidence_ref does not change the model value")
        has_correction = True
        required_errors.add("hallucinated-evidence")
    return has_correction, required_errors


def validate_review_data(
    cbom: Mapping[str, Any],
    triage_records: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, str]],
    misclass_rows: Sequence[Mapping[str, str]],
) -> dict[str, int]:
    """Validate asset coverage, human verdicts, corrected values, and error log."""
    if cbom.get("bomFormat") != "CycloneDX" or cbom.get("specVersion") != "1.6":
        raise ValueError("review gate requires a CycloneDX 1.6 CBOM")
    expected_assets = _asset_locations(cbom)
    validated_triage = validate_triage_batch(triage_records, expected_assets)
    triage_by_id = {record["asset_id"]: record for record in validated_triage}

    reviews_by_id: dict[str, Mapping[str, str]] = {}
    corrections_by_id: dict[str, bool] = {}
    required_errors_by_id: dict[str, set[str]] = {}
    verdict_counts: Counter[str] = Counter()
    for row in review_rows:
        if set(row) != set(REVIEW_COLUMNS) or any(
            not isinstance(value, str) for value in row.values()
        ):
            raise ValueError("review row does not match the required schema")
        asset_id = row["asset_id"].strip()
        if not asset_id or asset_id not in expected_assets:
            raise ValueError(f"review row has an unknown asset_id: {asset_id!r}")
        if asset_id in reviews_by_id:
            raise ValueError(f"duplicate review row for asset_id: {asset_id}")
        verdict = row["verdict"].strip()
        if verdict not in REVIEW_VERDICTS:
            raise ValueError(f"invalid review verdict for {asset_id}: {verdict!r}")
        try:
            model_call = json.loads(row["model_call"])
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid model_call JSON for {asset_id}") from error
        if model_call != triage_by_id[asset_id]:
            raise ValueError(f"review model_call does not match triage for {asset_id}")
        evidence_checked = row["evidence_checked"].strip()
        if not evidence_checked:
            raise ValueError(f"review evidence_checked is required for {asset_id}")
        _minutes(row["minutes_spent"], f"review minutes_spent for {asset_id}")
        has_correction, required_errors = _validate_corrected_values(
            row, model_call, expected_assets[asset_id]
        )
        reviewer_reason = row["reviewer_reason"].strip()
        if verdict == "agree" and has_correction:
            raise ValueError(f"agree verdict cannot contain corrections for {asset_id}")
        if verdict == "correct" and not has_correction:
            raise ValueError(f"correct verdict requires changed values for {asset_id}")
        if verdict in {"correct", "unknown"} and not reviewer_reason:
            raise ValueError(f"reviewer_reason is required for {verdict} verdict: {asset_id}")
        if verdict == "unknown" and model_call["confidence"] == "high":
            required_errors.add("overconfident-unknown")
        reviews_by_id[asset_id] = row
        corrections_by_id[asset_id] = has_correction
        required_errors_by_id[asset_id] = required_errors
        verdict_counts[verdict] += 1

    missing_reviews = set(expected_assets) - set(reviews_by_id)
    if missing_reviews:
        raise ValueError(
            f"missing review rows for: {', '.join(sorted(missing_reviews))}"
        )

    misclasses_by_id: Counter[str] = Counter()
    seen_errors: set[tuple[str, str]] = set()
    errors_by_id: dict[str, set[str]] = {}
    for row in misclass_rows:
        if set(row) != set(MISCLASS_COLUMNS) or any(
            not isinstance(value, str) for value in row.values()
        ):
            raise ValueError("misclass row does not match the required schema")
        asset_id = row["asset_id"].strip()
        error_type = row["error_type"].strip()
        if asset_id not in reviews_by_id:
            raise ValueError(f"misclassification has no reviewed asset: {asset_id!r}")
        if error_type not in MISCLASS_TYPES:
            raise ValueError(f"invalid misclassification error_type: {error_type!r}")
        review_verdict = reviews_by_id[asset_id]["verdict"].strip()
        if review_verdict == "agree":
            raise ValueError(f"agreed asset cannot have a misclassification: {asset_id}")
        key = (asset_id, error_type)
        if key in seen_errors:
            raise ValueError(f"duplicate misclassification type for asset: {asset_id}")
        seen_errors.add(key)
        errors_by_id.setdefault(asset_id, set()).add(error_type)
        if row["caught_by"].strip() not in CAUGHT_BY_VALUES:
            raise ValueError(f"invalid caught_by value for {asset_id}")
        if not row["details"].strip():
            raise ValueError(f"misclassification details are required for {asset_id}")
        _minutes(row["minutes_spent"], f"misclassification minutes_spent for {asset_id}")
        misclasses_by_id[asset_id] += 1

    for asset_id, row in reviews_by_id.items():
        verdict = row["verdict"].strip()
        requires_misclass = verdict == "correct" or (
            verdict == "unknown" and corrections_by_id[asset_id]
        )
        if requires_misclass and not misclasses_by_id[asset_id]:
            raise ValueError(f"correction is missing a misclass.csv row for {asset_id}")
        missing_error_types = required_errors_by_id[asset_id] - errors_by_id.get(
            asset_id, set()
        )
        if missing_error_types:
            raise ValueError(
                f"misclass.csv for {asset_id} is missing: "
                f"{', '.join(sorted(missing_error_types))}"
            )

    return {
        "assets": len(expected_assets),
        "agree": verdict_counts["agree"],
        "correct": verdict_counts["correct"],
        "unknown": verdict_counts["unknown"],
        "misclassifications": len(misclass_rows),
    }


def load_validated_review_run(
    cbom_path: Path,
    triage_path: Path,
    review_path: Path,
    misclass_path: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, str]],
    dict[str, int],
]:
    cbom_path = cbom_path.resolve(strict=True)
    run_root = cbom_path.parent.resolve()
    if not (run_root / "raw").is_dir():
        raise ValueError("CBOM must be stored at a run root beside raw/")
    for label, path in (
        ("CBOM", cbom_path),
        ("triage", triage_path),
        ("review", review_path),
        ("misclass", misclass_path),
    ):
        _resolve_run_file(path, run_root, label)

    cbom = _read_json_object(cbom_path, "CBOM")
    triage_records = _read_jsonl(triage_path, "triage")
    review_rows = _read_csv(review_path, REVIEW_COLUMNS, "review.csv")
    misclass_rows = _read_csv(misclass_path, MISCLASS_COLUMNS, "misclass.csv")
    summary = validate_review_data(cbom, triage_records, review_rows, misclass_rows)
    return cbom, triage_records, review_rows, misclass_rows, summary


def validate_review_files(
    cbom_path: Path,
    triage_path: Path,
    review_path: Path,
    misclass_path: Path,
) -> dict[str, int]:
    return load_validated_review_run(
        cbom_path, triage_path, review_path, misclass_path
    )[-1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cbom", type=Path, required=True)
    parser.add_argument("--triage", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--misclass", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_review_files(
            args.cbom, args.triage, args.review, args.misclass
        )
    except ValueError as error:
        parser.error(str(error))
    print(
        "Review gate passed: "
        f"{result['assets']} assets ({result['agree']} agree, "
        f"{result['correct']} corrected, {result['unknown']} unknown); "
        f"{result['misclassifications']} misclassifications recorded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
