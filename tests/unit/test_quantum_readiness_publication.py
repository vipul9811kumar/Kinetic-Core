"""Tests for sanitized publication aggregates."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.quantum_readiness.publication import (
    build_publication_summary,
    create_publication_summary,
)
from tools.quantum_readiness.review import MISCLASS_COLUMNS, REVIEW_COLUMNS


def publication_fixture() -> tuple[dict, list[dict], list[dict[str, str]], list[dict[str, str]]]:
    cbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [
            {
                "type": "cryptographic-asset",
                "bom-ref": "private-asset-1",
                "name": "Sensitive endpoint ECDHE",
                "properties": [
                    {"name": "source_tool", "value": "Sonar-Cryptography"},
                    {"name": "scan_area", "value": "code-and-libraries"},
                ],
                "evidence": {"occurrences": [{"location": "src/private.py:42"}]},
            },
            {
                "type": "cryptographic-asset",
                "bom-ref": "private-asset-2",
                "name": "Private TLS host",
                "properties": [
                    {"name": "source_tool", "value": "secret-subscription-host"},
                    {"name": "scan_area", "value": "endpoint-tls"},
                ],
                "evidence": {"occurrences": [{"location": "https://private.example"}]},
            },
        ],
    }
    triage = [
        {
            "asset_id": "private-asset-1",
            "quantum_vulnerable": "yes",
            "threat": "shor",
            "classical_weakness": False,
            "data_secrecy_lifetime": "5-10y",
            "migration_priority": "P1",
            "evidence_ref": "src/private.py:42",
            "reason": "Observed ECDHE is vulnerable to Shor's algorithm.",
            "confidence": "high",
        },
        {
            "asset_id": "private-asset-2",
            "quantum_vulnerable": "no",
            "threat": "none",
            "classical_weakness": False,
            "data_secrecy_lifetime": "unknown",
            "migration_priority": "P3",
            "evidence_ref": "https://private.example",
            "reason": "No quantum-vulnerable exchange was observed.",
            "confidence": "low",
        },
    ]
    reviews = []
    for record, verdict, reason in (
        (triage[0], "agree", ""),
        (triage[1], "unknown", "Negotiated key exchange was not observable."),
    ):
        reviews.append(
            {
                "asset_id": record["asset_id"],
                "model_call": json.dumps(record),
                "verdict": verdict,
                "corrected_quantum_vulnerable": "",
                "corrected_threat": "",
                "corrected_classical_weakness": "",
                "corrected_data_secrecy_lifetime": "",
                "corrected_migration_priority": "",
                "corrected_evidence_ref": "",
                "corrected_confidence": "",
                "reviewer_reason": reason,
                "evidence_checked": "Checked supplied evidence.",
                "minutes_spent": "2",
            }
        )
    return cbom, triage, reviews, []


class TestPublicationSummary(unittest.TestCase):
    def test_aggregates_final_reviewed_values_and_redacts_identifiers(self) -> None:
        cbom, triage, reviews, misclass = publication_fixture()
        summary = build_publication_summary(cbom, triage, reviews, misclass)

        self.assertEqual(summary["counts"]["quantum_vulnerable"]["yes"], 1)
        self.assertEqual(summary["counts"]["quantum_vulnerable"]["no"], 0)
        self.assertEqual(summary["counts"]["quantum_vulnerable"]["unknown"], 1)
        self.assertEqual(summary["counts"]["model_unknown_rate"], 0.0)
        self.assertEqual(summary["counts"]["reviewed_quantum_unknown_rate"], 0.5)
        self.assertEqual(summary["counts"]["by_source_tool"]["sonar-cryptography"], 1)
        self.assertEqual(summary["counts"]["by_source_tool"]["other"], 1)
        self.assertFalse(summary["eligible_for_external_publication"])
        self.assertEqual(summary["generic_examples"], [])

        serialized = json.dumps(summary)
        for private_value in (
            "private-asset-1",
            "secret-subscription-host",
            "private.example",
            "src/private.py",
            "Sensitive endpoint",
        ):
            self.assertNotIn(private_value, serialized)

    def test_requires_review_gate_before_writing_publication_file(self) -> None:
        cbom, triage, reviews, misclass = publication_fixture()
        with self.assertRaisesRegex(ValueError, "missing review rows"):
            build_publication_summary(cbom, triage, reviews[:1], misclass)

    def test_writes_only_to_the_private_run_summary_path(self) -> None:
        cbom, triage, reviews, misclass = publication_fixture()
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            (run_dir / "raw").mkdir()
            (run_dir / "cbom.json").write_text(json.dumps(cbom), encoding="utf-8")
            (run_dir / "triage.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in triage),
                encoding="utf-8",
            )
            for name, columns, rows in (
                ("review.csv", REVIEW_COLUMNS, reviews),
                ("misclass.csv", MISCLASS_COLUMNS, misclass),
            ):
                with (run_dir / name).open(
                    "w", encoding="utf-8", newline=""
                ) as stream:
                    writer = csv.DictWriter(stream, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(rows)

            output_path = run_dir / "publication-summary.json"
            create_publication_summary(
                run_dir / "cbom.json",
                run_dir / "triage.jsonl",
                run_dir / "review.csv",
                run_dir / "misclass.csv",
                output_path,
            )
            self.assertTrue(output_path.is_file())
            self.assertFalse((run_dir / "raw" / output_path.name).exists())
            with self.assertRaisesRegex(ValueError, "publication-summary.json"):
                create_publication_summary(
                    run_dir / "cbom.json",
                    run_dir / "triage.jsonl",
                    run_dir / "review.csv",
                    run_dir / "misclass.csv",
                    run_dir / "raw" / output_path.name,
                )


if __name__ == "__main__":
    unittest.main()
