"""Tests for fail-closed Azure-only crypto-asset triage."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.quantum_readiness.triage import (
    _request_triage,
    build_messages,
    load_azure_settings,
    run_triage_files,
    validate_triage_batch,
    validate_triage_record,
)


def prompt_asset() -> dict:
    return {
        "asset_id": "urn:uuid:asset-1",
        "asset_type": "algorithm",
        "algorithm_or_protocol": "SHA-256",
        "key_size_or_curve": "unknown",
        "library": "stdlib",
        "scan_area": "code-and-libraries",
        "source_tool": "manual-review",
        "locations": ["src/hash.py:10"],
        "redacted_snippet": "digest(data)",
        "system_context": "device telemetry",
    }


def triage_record(**overrides: object) -> dict:
    record = {
        "asset_id": "urn:uuid:asset-1",
        "quantum_vulnerable": "no",
        "threat": "none",
        "classical_weakness": False,
        "data_secrecy_lifetime": "unknown",
        "migration_priority": "P3",
        "evidence_ref": "src/hash.py:10",
        "reason": "SHA-256 is not quantum-vulnerable under this rubric.",
        "confidence": "high",
    }
    record.update(overrides)
    return record


class TestAzureTriageConfiguration(unittest.TestCase):
    def test_direct_openai_key_does_not_enable_triage(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "AZURE_OPENAI_ENDPOINT"):
            load_azure_settings({"OPENAI_API_KEY": "direct-api-key"})

    def test_requires_https_and_an_explicit_deployment(self) -> None:
        settings = load_azure_settings(
            {
                "AZURE_OPENAI_ENDPOINT": "https://resource.openai.azure.com/",
                "AZURE_OPENAI_KEY": "azure-key",
                "AZURE_OPENAI_QR_TRIAGE_DEPLOYMENT": "approved-gpt4",
            }
        )
        self.assertEqual(settings.deployment, "approved-gpt4")
        self.assertNotIn("azure-key", repr(settings))

        with self.assertRaisesRegex(ValueError, "HTTPS"):
            load_azure_settings(
                {
                    "AZURE_OPENAI_ENDPOINT": "http://resource.openai.azure.com/",
                    "AZURE_OPENAI_KEY": "azure-key",
                    "AZURE_OPENAI_QR_TRIAGE_DEPLOYMENT": "approved-gpt4",
                }
            )

    def test_rejects_placeholder_deployment(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "placeholder"):
            load_azure_settings(
                {
                    "AZURE_OPENAI_ENDPOINT": "https://resource.openai.azure.com/",
                    "AZURE_OPENAI_KEY": "azure-key",
                    "AZURE_OPENAI_QR_TRIAGE_DEPLOYMENT": "<approved-gpt-4>",
                }
            )


class TestTriageValidation(unittest.TestCase):
    def test_prompt_uses_allowlisted_input_only(self) -> None:
        messages = build_messages(prompt_asset())
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn("src/hash.py:10", messages[1]["content"])
        asset = prompt_asset()
        asset["private_key"] = "must not be included"
        with self.assertRaisesRegex(ValueError, "unsupported"):
            build_messages(asset)

    def test_validates_schema_and_supplied_evidence_reference(self) -> None:
        record = validate_triage_record(
            triage_record(), "urn:uuid:asset-1", ["src/hash.py:10"]
        )
        self.assertEqual(record["migration_priority"], "P3")

        with self.assertRaisesRegex(ValueError, "evidence_ref"):
            validate_triage_record(
                triage_record(evidence_ref="src/other.py:1"),
                "urn:uuid:asset-1",
                ["src/hash.py:10"],
            )
        with self.assertRaisesRegex(ValueError, "at most 25 words"):
            validate_triage_record(
                triage_record(reason="word " * 26),
                "urn:uuid:asset-1",
                ["src/hash.py:10"],
            )
        with self.assertRaisesRegex(ValueError, "unsupported"):
            validate_triage_record(
                triage_record(extra="unexpected"),
                "urn:uuid:asset-1",
                ["src/hash.py:10"],
            )

    def test_batch_requires_exactly_one_response_per_asset(self) -> None:
        expected = {
            "urn:uuid:asset-1": ["src/hash.py:10"],
            "urn:uuid:asset-2": ["src/tls.py:20"],
        }
        records = [
            triage_record(),
            triage_record(
                asset_id="urn:uuid:asset-2",
                evidence_ref="src/tls.py:20",
            ),
        ]
        result = validate_triage_batch(records, expected)
        self.assertEqual([record["asset_id"] for record in result], list(expected))

        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_triage_batch(records + [records[0]], expected)
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_triage_batch(records[:1], expected)

    def test_azure_request_is_zero_temperature_and_validates_response(self) -> None:
        record = triage_record()

        class FakeClient:
            def __init__(self) -> None:
                self.request = None
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self.create)
                )

            def create(self, **kwargs: object) -> object:
                self.request = kwargs
                message = SimpleNamespace(content=json.dumps(record))
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=message)]
                )

        client = FakeClient()
        result = _request_triage(client, "approved-gpt4", prompt_asset())
        self.assertEqual(result["asset_id"], "urn:uuid:asset-1")
        self.assertEqual(client.request["model"], "approved-gpt4")
        self.assertEqual(client.request["temperature"], 0.0)
        self.assertEqual(client.request["response_format"], {"type": "json_object"})

    def test_batch_refuses_direct_openai_and_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            (run_dir / "raw").mkdir()
            inputs = run_dir / "triage-inputs.jsonl"
            inputs.write_text(json.dumps(prompt_asset()) + "\n", encoding="utf-8")
            output = run_dir / "triage.jsonl"
            output.write_text("existing output\n", encoding="utf-8")
            with patch.dict(
                os.environ, {"OPENAI_API_KEY": "direct-api-key"}, clear=True
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "AZURE_OPENAI_ENDPOINT"
                ):
                    run_triage_files(inputs, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing output\n")

    def test_duplicate_batch_inputs_fail_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            (run_dir / "raw").mkdir()
            inputs = run_dir / "triage-inputs.jsonl"
            serialized_asset = json.dumps(prompt_asset())
            inputs.write_text(
                    f"{serialized_asset}\n{serialized_asset}\n", encoding="utf-8"
            )
            output = run_dir / "triage.jsonl"
            output.write_text("existing output\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(ValueError, "duplicate triage input"):
                        run_triage_files(inputs, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing output\n")


if __name__ == "__main__":
    unittest.main()
