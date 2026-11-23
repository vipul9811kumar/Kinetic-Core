"""Tests for complete human review and misclassification validation."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.quantum_readiness.review import (
    MISCLASS_COLUMNS,
    REVIEW_COLUMNS,
    validate_review_data,
    validate_review_files,
)


def fixture_data() -> tuple[dict, list[dict], list[dict[str, str]], list[dict[str, str]]]:
    components = [
        {
            "type": "cryptographic-asset",
            "bom-ref": "asset-1",
            "evidence": {"occurrences": [{"location": "src/hash.py:10"}]},
        },
        {
            "type": "cryptographic-asset",
            "bom-ref": "asset-2",
            "evidence": {"occurrences": [{"location": "src/tls.py:20"}]},
        },
    ]
    cbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": components,
    }
    triage = [
        {
            "asset_id": "asset-1",
            "quantum_vulnerable": "no",
            "threat": "none",
            "classical_weakness": False,
            "data_secrecy_lifetime": "unknown",
            "migration_priority": "P3",
            "evidence_ref": "src/hash.py:10",
            "reason": "SHA-256 is not quantum-vulnerable under this rubric.",
            "confidence": "high",
        },
        {
            "asset_id": "asset-2",
            "quantum_vulnerable": "yes",
            "threat": "shor",
            "classical_weakness": False,
            "data_secrecy_lifetime": "1-5y",
            "migration_priority": "P2",
            "evidence_ref": "src/tls.py:20",
            "reason": "Observed classical ECDHE is vulnerable to Shor's algorithm.",
            "confidence": "medium",
        },
    ]
    reviews = [review_row(record) for record in triage]
    return cbom, triage, reviews, []


def review_row(model_call: dict) -> dict[str, str]:
    return {
        "asset_id": model_call["asset_id"],
        "model_call": json.dumps(model_call),
        "verdict": "agree",
        "corrected_quantum_vulnerable": "",
        "corrected_threat": "",
        "corrected_classical_weakness": "",
        "corrected_data_secrecy_lifetime": "",
        "corrected_migration_priority": "",
        "corrected_evidence_ref": "",
        "corrected_confidence": "",
        "reviewer_reason": "",
        "evidence_checked": "Checked the cited source location.",
        "minutes_spent": "2",
    }


class TestHumanReviewValidation(unittest.TestCase):
    def test_accepts_complete_review_and_counts_verdicts(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
        result = validate_review_data(cbom, triage, reviews, misclass)
        self.assertEqual(
            result,
            {
                "assets": 2,
                "agree": 2,
                "correct": 0,
                "unknown": 0,
                "misclassifications": 0,
            },
        )

    def test_requires_review_for_every_cbom_asset(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
        with self.assertRaisesRegex(ValueError, "missing review rows"):
            validate_review_data(cbom, triage, reviews[:1], misclass)

    def test_correction_requires_matching_misclassification_record(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
        corrected = reviews[0]
        corrected.update(
            {
                "verdict": "correct",
                "corrected_quantum_vulnerable": "yes",
                "corrected_threat": "shor",
                "corrected_migration_priority": "P2",
                "reviewer_reason": "Evidence shows an ECDSA signature.",
            }
        )
        with self.assertRaisesRegex(ValueError, "missing a misclass.csv row"):
            validate_review_data(cbom, triage, reviews, misclass)

        wrong_type = [
            {
                "asset_id": "asset-1",
                "error_type": "wrong-priority",
                "caught_by": "evidence-check",
                "details": "Incorrect error category.",
                "minutes_spent": "2",
            }
        ]
        with self.assertRaisesRegex(ValueError, "missing: false-safe"):
            validate_review_data(cbom, triage, reviews, wrong_type)

        misclass = [
            {
                "asset_id": "asset-1",
                "error_type": "false-safe",
                "caught_by": "evidence-check",
                "details": "Source confirms the vulnerable signing algorithm.",
                "minutes_spent": "2",
            },
            {
                "asset_id": "asset-1",
                "error_type": "wrong-priority",
                "caught_by": "evidence-check",
                "details": "Priority changed after reviewing exposure.",
                "minutes_spent": "1",
            },
        ]
        result = validate_review_data(cbom, triage, reviews, misclass)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["misclassifications"], 2)

    def test_unknown_requires_reason_but_is_not_skipped(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
        reviews[1]["verdict"] = "unknown"
        reviews[1]["reviewer_reason"] = "The endpoint key-exchange group is not observable."
        result = validate_review_data(cbom, triage, reviews, misclass)
        self.assertEqual(result["unknown"], 1)
        self.assertEqual(result["assets"], 2)

    def test_high_confidence_unknown_requires_overconfidence_tag(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
        triage[1]["confidence"] = "high"
        reviews[1]["model_call"] = json.dumps(triage[1])
        reviews[1]["verdict"] = "unknown"
        reviews[1]["reviewer_reason"] = "The endpoint key-exchange group is not observable."
        with self.assertRaisesRegex(ValueError, "overconfident-unknown"):
            validate_review_data(cbom, triage, reviews, misclass)

        misclass = [
            {
                "asset_id": "asset-2",
                "error_type": "overconfident-unknown",
                "caught_by": "evidence-check",
                "details": "The evidence did not support a confident call.",
                "minutes_spent": "2",
            }
        ]
        result = validate_review_data(cbom, triage, reviews, misclass)
        self.assertEqual(result["unknown"], 1)

    def test_validates_csv_headers_and_run_paths(self) -> None:
        cbom, triage, reviews, misclass = fixture_data()
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

            result = validate_review_files(
                run_dir / "cbom.json",
                run_dir / "triage.jsonl",
                run_dir / "review.csv",
                run_dir / "misclass.csv",
            )
            self.assertEqual(result["assets"], 2)


if __name__ == "__main__":
    unittest.main()
