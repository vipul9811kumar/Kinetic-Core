"""Unit tests for private quantum-readiness run setup and CBOM merging."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.quantum_readiness.inventory_adapter import build_inventory
from tools.quantum_readiness.merge_cbom import merge_manifest
from tools.quantum_readiness.run_setup import create_run


def make_cbom(location: str, context: str) -> dict:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:source",
        "version": 1,
        "components": [
            {
                "type": "cryptographic-asset",
                "bom-ref": f"source-{location}",
                "name": "SHA-256",
                "cryptoProperties": {
                    "assetType": "algorithm",
                    "algorithmProperties": {
                        "primitive": "hash",
                        "cryptoFunctions": ["digest"],
                        "parameterSetIdentifier": "256",
                    },
                },
                "evidence": {
                    "occurrences": [
                        {
                            "location": location,
                            "line": 10,
                            "additionalContext": context,
                        }
                    ]
                },
                "properties": [],
            }
        ],
        "dependencies": [],
    }


class TestRunSetup(unittest.TestCase):
    def test_creates_private_run_layout_and_csv_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = create_run("2026-11-23", Path(temporary_directory))

            self.assertTrue((run_dir / "raw").is_dir())
            self.assertTrue((run_dir / "cbom.json").is_file())
            self.assertTrue((run_dir / "triage.jsonl").is_file())
            self.assertTrue((run_dir / "triage-inputs.jsonl").is_file())
            self.assertEqual(
                json.loads((run_dir / "inventory-inputs.json").read_text())[
                    "syft_inputs"
                ],
                [],
            )
            self.assertEqual(
                (run_dir / "review.csv").read_text(encoding="utf-8").splitlines()[0],
                "asset_id,model_call,verdict,corrected_quantum_vulnerable,"
                "corrected_threat,corrected_classical_weakness,"
                "corrected_data_secrecy_lifetime,corrected_migration_priority,"
                "corrected_evidence_ref,corrected_confidence,reviewer_reason,"
                "evidence_checked,minutes_spent",
            )
            self.assertEqual(json.loads((run_dir / "inputs.json").read_text())["inputs"], [])

    def test_refuses_to_overwrite_an_existing_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            create_run("2026-11-23", Path(temporary_directory))
            with self.assertRaises(FileExistsError):
                create_run("2026-11-23", Path(temporary_directory))


class TestCbomMerge(unittest.TestCase):
    def test_deduplicates_assets_and_locations_without_mutating_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            (run_dir / "raw").mkdir()
            first = make_cbom("src/crypto.py", "hash call")
            second = make_cbom("src/crypto.py", "same call from another scanner")
            second["components"][0]["evidence"]["occurrences"].append(
                {"location": "src/other.py", "line": 25}
            )
            first_path = run_dir / "raw" / "first.json"
            second_path = run_dir / "raw" / "second.json"
            first_path.write_text(json.dumps(first), encoding="utf-8")
            second_path.write_text(json.dumps(second), encoding="utf-8")
            first_bytes = first_path.read_bytes()
            second_bytes = second_path.read_bytes()
            manifest_path = run_dir / "inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "run_id": "run-2026-11-23",
                        "inputs": [
                            {
                                "path": "raw/first.json",
                                "source_tool": "sonar-cryptography",
                                "scan_area": "code-and-libraries",
                            },
                            {
                                "path": "raw/second.json",
                                "source_tool": "cbomkit-theia",
                                "scan_area": "container-images",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output_path = run_dir / "cbom.json"
            output = merge_manifest(manifest_path, output_path)

            self.assertEqual(len(output["components"]), 1)
            asset = output["components"][0]
            self.assertEqual(len(asset["evidence"]["occurrences"]), 2)
            self.assertIn(
                {"name": "source_tool", "value": "sonar-cryptography"},
                asset["properties"],
            )
            self.assertIn(
                {"name": "source_tool", "value": "cbomkit-theia"},
                asset["properties"],
            )
            self.assertEqual(first_path.read_bytes(), first_bytes)
            self.assertEqual(second_path.read_bytes(), second_bytes)
            self.assertEqual(json.loads(output_path.read_text())["specVersion"], "1.6")

    def test_rejects_input_paths_that_escape_the_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            outside_path = run_dir.parent / f"{run_dir.name}-outside.json"
            outside_path.write_text(json.dumps(make_cbom("outside.py", "test")))
            try:
                manifest_path = run_dir / "inputs.json"
                manifest_path.write_text(
                    json.dumps(
                        {
                            "run_id": "run-2026-11-23",
                            "inputs": [
                                {
                                    "path": f"../{outside_path.name}",
                                    "source_tool": "sonar-cryptography",
                                    "scan_area": "code-and-libraries",
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    merge_manifest(manifest_path, run_dir / "cbom.json")
            finally:
                outside_path.unlink(missing_ok=True)

    def test_refuses_to_write_merged_output_under_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            raw_dir = run_dir / "raw"
            raw_dir.mkdir()
            source_path = raw_dir / "source.json"
            source_path.write_text(
                json.dumps(make_cbom("src/crypto.py", "hash call")),
                encoding="utf-8",
            )
            manifest_path = run_dir / "inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "run_id": "run-2026-11-23",
                        "inputs": [
                            {
                                "path": "raw/source.json",
                                "source_tool": "sonar-cryptography",
                                "scan_area": "code-and-libraries",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_bytes = source_path.read_bytes()

            with self.assertRaises(ValueError):
                merge_manifest(manifest_path, raw_dir / "merged.json")

            self.assertEqual(source_path.read_bytes(), source_bytes)
            self.assertFalse((raw_dir / "merged.json").exists())


class TestInventoryAdapter(unittest.TestCase):
    def test_builds_candidate_inventory_without_inferencing_algorithms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            raw_dir = run_dir / "raw"
            raw_dir.mkdir()
            syft_path = raw_dir / "image.sbom.json"
            syft_path.write_text(
                json.dumps(
                    {
                        "bomFormat": "CycloneDX",
                        "specVersion": "1.7",
                        "serialNumber": "urn:uuid:source",
                        "metadata": {
                            "tools": {
                                "components": [
                                    {
                                        "name": "syft",
                                        "version": "1.57.2",
                                        "type": "application",
                                    }
                                ]
                            }
                        },
                        "components": [
                            {
                                "type": "library",
                                "name": "openssl",
                                "version": "3.5.7",
                                "purl": "pkg:deb/debian/openssl@3.5.7",
                            },
                            {
                                "type": "file",
                                "name": "/usr/lib/libssl.so",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = run_dir / "inventory-inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "syft_inputs": [
                            {
                                "path": "raw/image.sbom.json",
                                "scan_area": "container-images",
                            }
                        ],
                        "azure_inventory": None,
                    }
                ),
                encoding="utf-8",
            )

            result = build_inventory(manifest_path, run_dir / "inventory.json")

            syft_inventory = result["syft_inventories"][0]
            self.assertEqual(syft_inventory["source_tool_version"], "1.57.2")
            self.assertEqual(syft_inventory["component_count"], 2)
            self.assertEqual(syft_inventory["crypto_library_candidate_count"], 1)
            self.assertEqual(
                syft_inventory["crypto_library_candidates"][0]["name"], "openssl"
            )
            self.assertIn("do not", syft_inventory["interpretation"])
            self.assertNotIn("algorithm", syft_inventory["crypto_library_candidates"][0])

    def test_records_azure_denominator_without_copying_unneeded_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            raw_dir = run_dir / "raw"
            raw_dir.mkdir()
            azure_path = raw_dir / "azure.json"
            azure_path.write_text(
                json.dumps(
                    {
                        "collectedAtUtc": "2026-11-19T23:01:32+00:00",
                        "scope": "test pilot",
                        "deploymentState": "Succeeded",
                        "resourceTypeCounts": {"Microsoft.KeyVault/vaults": 1},
                        "resources": [
                            {
                                "name": "vault-test",
                                "type": "Microsoft.KeyVault/vaults",
                                "location": "eastus",
                                "sku": {"name": "standard"},
                                "tags": {"private": "do-not-copy"},
                            }
                        ],
                        "keyVaultCertificateCount": 0,
                        "acrRepositoryCount": 0,
                        "containerAppCount": 0,
                        "secretValuesRead": False,
                        "limitations": ["Certificate metadata not rechecked."],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = run_dir / "inventory-inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {"syft_inputs": [], "azure_inventory": "raw/azure.json"}
                ),
                encoding="utf-8",
            )

            result = build_inventory(manifest_path, run_dir / "inventory.json")

            azure_inventory = result["azure_inventory"]
            self.assertEqual(azure_inventory["resource_count"], 1)
            self.assertEqual(
                azure_inventory["recorded_metrics"]["keyVaultCertificateCount"], 0
            )
            self.assertEqual(
                azure_inventory["resources"],
                [
                    {
                        "name": "vault-test",
                        "type": "Microsoft.KeyVault/vaults",
                        "location": "eastus",
                    }
                ],
            )
            self.assertFalse(azure_inventory["secret_values_read"])
            self.assertFalse(azure_inventory["resource_ids_available"])
            self.assertNotIn("tags", azure_inventory["resources"][0])

    def test_rejects_mismatched_azure_resource_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            raw_dir = run_dir / "raw"
            raw_dir.mkdir()
            (raw_dir / "azure.json").write_text(
                json.dumps(
                    {
                        "resources": [
                            {"name": "vault-test", "type": "Microsoft.KeyVault/vaults"}
                        ],
                        "resourceTypeCounts": {},
                        "secretValuesRead": False,
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = run_dir / "inventory-inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {"syft_inputs": [], "azure_inventory": "raw/azure.json"}
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "does not match"):
                build_inventory(manifest_path, run_dir / "inventory.json")

    def test_rejects_inventory_sources_outside_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            raw_dir = run_dir / "raw"
            raw_dir.mkdir()
            outside_path = run_dir / "outside.json"
            outside_path.write_text("{}", encoding="utf-8")
            manifest_path = run_dir / "inventory-inputs.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "syft_inputs": [
                            {
                                "path": "outside.json",
                                "scan_area": "container-images",
                            }
                        ],
                        "azure_inventory": None,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_inventory(manifest_path, run_dir / "inventory.json")


if __name__ == "__main__":
    unittest.main()
