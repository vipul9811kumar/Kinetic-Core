"""Create a private, reproducible directory for one quantum-readiness scan."""

from __future__ import annotations

import argparse
import csv
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence


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

TIMELOG_COLUMNS = ("date", "step", "minutes", "mode")


def create_run(run_date: str, root: Path = Path("qr-pilot")) -> Path:
    """Create a new run directory and private-output templates without overwriting."""
    parsed_date = date.fromisoformat(run_date)
    if parsed_date.isoformat() != run_date:
        raise ValueError("run date must use YYYY-MM-DD format")

    run_dir = root / f"run-{run_date}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "raw").mkdir()

    now = datetime.now(timezone.utc).isoformat()
    initial_cbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "properties": [{"name": "run_id", "value": run_dir.name}],
        },
        "components": [],
        "dependencies": [],
    }
    (run_dir / "cbom.json").write_text(
        json.dumps(initial_cbom, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "triage.jsonl").write_text("", encoding="utf-8")
    (run_dir / "triage-inputs.jsonl").write_text("", encoding="utf-8")
    (run_dir / "inputs.json").write_text(
        json.dumps({"run_id": run_dir.name, "inputs": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "inventory-inputs.json").write_text(
        json.dumps({"syft_inputs": [], "azure_inventory": None}, indent=2) + "\n",
        encoding="utf-8",
    )

    for filename, columns in (
        ("review.csv", REVIEW_COLUMNS),
        ("misclass.csv", MISCLASS_COLUMNS),
        ("timelog.csv", TIMELOG_COLUMNS),
    ):
        with (run_dir / filename).open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerow(columns)

    (run_dir / "tools.txt").write_text(
        "Record tool name, exact version, command, and relevant image digest "
        "before each scan step.\n"
        "Do not replace an unknown version with an estimate.\n"
        "Pending tools: sonar-cryptography, CBOMkit-theia, Syft, Azure CLI, "
        "testssl.sh, and the approved triage model.\n",
        encoding="utf-8",
    )
    return run_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="UTC run date in YYYY-MM-DD form (default: today)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("qr-pilot"),
        help="private run-data root (default: ./qr-pilot)",
    )
    args = parser.parse_args(argv)
    run_dir = create_run(args.date, args.root)
    print(f"Created private scan run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
