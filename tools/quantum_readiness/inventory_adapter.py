"""Build a private auxiliary inventory from Syft SBOMs and Azure exports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SYFT_SCAN_AREAS = frozenset({"code-and-libraries", "container-images"})
CRYPTO_NAME_TERMS = (
    "cryptography",
    "crypto",
    "openssl",
    "libssl",
    "boringssl",
    "libressl",
    "mbedtls",
    "wolfssl",
    "gnutls",
    "jsonwebtoken",
    "jose",
    "jwt",
    "nacl",
    "sodium",
    "tls",
    "ssl",
)


def _read_object(path: Path, label: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_path(raw_dir: Path, path_value: Any, label: str) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError(f"{label} must be a relative path under raw/")
    path = (raw_dir.parent / path_value).resolve()
    if not path.is_relative_to(raw_dir) or not path.is_file():
        raise ValueError(f"{label} must identify a file under raw/")
    return path


def _syft_tool_version(bom: Mapping[str, Any], source_path: Path) -> str:
    metadata = bom.get("metadata")
    tools = metadata.get("tools") if isinstance(metadata, dict) else None
    components = tools.get("components") if isinstance(tools, dict) else None
    if not isinstance(components, list):
        raise ValueError(f"Syft tool metadata is missing in {source_path.name!r}")
    matches = [
        tool
        for tool in components
        if isinstance(tool, dict)
        and isinstance(tool.get("name"), str)
        and tool["name"].casefold() == "syft"
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("version"), str):
        raise ValueError(
            f"exactly one versioned Syft tool is required in {source_path.name!r}"
        )
    return matches[0]["version"]


def _syft_inventory(source_path: Path, scan_area: str) -> dict[str, Any]:
    if not isinstance(scan_area, str) or scan_area not in SYFT_SCAN_AREAS:
        raise ValueError(
            f"unsupported Syft scan_area {scan_area!r}; choose one of "
            f"{', '.join(sorted(SYFT_SCAN_AREAS))}"
        )
    bom = _read_object(source_path, "Syft SBOM")
    if (
        bom.get("bomFormat") != "CycloneDX"
        or not isinstance(bom.get("specVersion"), str)
        or not bom["specVersion"].startswith("1.")
        or not isinstance(bom.get("components"), list)
    ):
        raise ValueError(f"{source_path.name!r} is not a CycloneDX SBOM")
    version = _syft_tool_version(bom, source_path)
    components = bom["components"]
    package_counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    for index, component in enumerate(components):
        if not isinstance(component, dict) or not isinstance(
            component.get("name"), str
        ):
            raise ValueError(
                f"invalid component at index {index} in {source_path.name!r}"
            )
        component_type = component.get("type")
        if not isinstance(component_type, str):
            raise ValueError(
                f"component type missing at index {index} in {source_path.name!r}"
            )
        package_counts[component_type] += 1
        if component_type != "library":
            continue
        normalized_name = component["name"].casefold()
        matches = [term for term in CRYPTO_NAME_TERMS if term in normalized_name]
        if not matches:
            continue
        candidate = {
            "name": component["name"],
            "candidate_match_terms": matches,
            "evidence_type": "software-package-name-match",
        }
        for field in ("version", "purl", "bom-ref"):
            value = component.get(field)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError(
                        f"invalid {field} for component at index {index} "
                        f"in {source_path.name!r}"
                    )
                candidate[field] = value
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            item["name"].casefold(),
            item.get("version", ""),
            item.get("purl", ""),
        )
    )
    return {
        "source_tool": "Syft",
        "source_tool_version": version,
        "scan_area": scan_area,
        "source_file": source_path.name,
        "source_sha256": _sha256_file(source_path),
        "source_bom_serial_number": bom.get("serialNumber"),
        "component_count": len(components),
        "component_type_counts": dict(sorted(package_counts.items())),
        "crypto_library_candidate_count": len(candidates),
        "crypto_library_candidates": candidates,
        "interpretation": (
            "Name matches identify packages for manual review only. They do not "
            "prove algorithm use, configuration, or runtime use; no algorithms "
            "are inferred from this SBOM."
        ),
    }


def _azure_inventory(source_path: Path) -> dict[str, Any]:
    data = _read_object(source_path, "Azure inventory")
    resources = data.get("resources")
    if not isinstance(resources, list):
        raise ValueError("Azure inventory must contain a resources array")
    normalized_resources: list[dict[str, str]] = []
    for index, resource in enumerate(resources):
        if (
            not isinstance(resource, dict)
            or not isinstance(resource.get("name"), str)
            or not isinstance(resource.get("type"), str)
        ):
            raise ValueError(f"invalid Azure resource at index {index}")
        normalized = {"name": resource["name"], "type": resource["type"]}
        resource_id = resource.get("id")
        if resource_id is not None:
            if not isinstance(resource_id, str):
                raise ValueError(f"invalid resource id at index {index}")
            normalized["id"] = resource_id
        location = resource.get("location")
        if location is not None:
            if not isinstance(location, str):
                raise ValueError(f"invalid resource location at index {index}")
            normalized["location"] = location
        normalized_resources.append(normalized)
    normalized_resources.sort(
        key=lambda item: (item["type"], item.get("id", item["name"]))
    )

    computed_type_counts = dict(
        sorted(Counter(resource["type"] for resource in normalized_resources).items())
    )
    reported_type_counts = data.get("resourceTypeCounts")
    if not isinstance(reported_type_counts, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for key, value in reported_type_counts.items()
    ):
        raise ValueError("Azure resourceTypeCounts must map resource types to counts")
    if dict(sorted(reported_type_counts.items())) != computed_type_counts:
        raise ValueError("Azure resourceTypeCounts does not match the resources array")
    if data.get("secretValuesRead") is not False:
        raise ValueError(
            "Azure inventory must explicitly confirm secretValuesRead=false"
        )

    metrics: dict[str, int] = {}
    for field in (
        "acrRepositoryCount",
        "containerAppCount",
        "keyVaultCertificateCount",
        "cosmosDatabaseCount",
        "cosmosContainerCount",
    ):
        value = data.get(field)
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"Azure inventory {field} must be a non-negative integer"
                )
            metrics[field] = value
    limitations = data.get("limitations", [])
    if not isinstance(limitations, list) or any(
        not isinstance(item, str) for item in limitations
    ):
        raise ValueError("Azure inventory limitations must be an array of strings")

    return {
        "source_tool": "Azure pilot configuration inventory",
        "source_tool_version": "not-recorded",
        "scan_area": "azure-config",
        "source_file": source_path.name,
        "source_sha256": _sha256_file(source_path),
        "source_collected_at_utc": data.get("collectedAtUtc"),
        "scope": data.get("scope"),
        "deployment_state": data.get("deploymentState"),
        "resource_count": len(normalized_resources),
        "resource_type_counts": computed_type_counts,
        "resource_ids_available": bool(normalized_resources)
        and all("id" in resource for resource in normalized_resources),
        "resources": normalized_resources,
        "recorded_metrics": metrics,
        "secret_values_read": False,
        "source_limitations": limitations,
        "interpretation": (
            "Counts and resources are limited to this export's collection time "
            "and scope. Recorded zero counts are not current verification. "
            "Resource identifiers and names are private inventory data; names "
            "alone are not stable global resource identifiers."
        ),
    }


def build_inventory(manifest_path: Path, output_path: Path) -> dict[str, Any]:
    """Create an auxiliary, non-CBOM inventory from raw Syft and Azure inputs."""
    manifest_path = manifest_path.resolve(strict=True)
    if manifest_path.parent.name == "raw" or not (
        manifest_path.parent / "raw"
    ).is_dir():
        raise ValueError("manifest must be stored at the run root beside raw/")
    run_root = manifest_path.parent.resolve()
    raw_dir = (run_root / "raw").resolve(strict=True)
    if not raw_dir.is_dir():
        raise ValueError("run raw/ path must be a directory")

    manifest = _read_object(manifest_path, "inventory manifest")
    syft_inputs = manifest.get("syft_inputs", [])
    azure_path_value = manifest.get("azure_inventory")
    if not isinstance(syft_inputs, list):
        raise ValueError("syft_inputs must be an array")
    if not syft_inputs and azure_path_value is None:
        raise ValueError("inventory manifest must list at least one source")

    output_path = output_path.resolve()
    if not output_path.is_relative_to(run_root):
        raise ValueError("inventory output must remain inside the run directory")
    if output_path == manifest_path or output_path.is_relative_to(raw_dir):
        raise ValueError(
            "inventory output must not overwrite inputs or be placed under raw/"
        )

    syft_inventories: list[dict[str, Any]] = []
    for index, entry in enumerate(syft_inputs):
        if not isinstance(entry, dict):
            raise ValueError(f"syft_inputs[{index}] must be an object")
        source_path = _source_path(
            raw_dir, entry.get("path"), f"syft_inputs[{index}].path"
        )
        if output_path == source_path:
            raise ValueError("inventory output must not overwrite a source input")
        syft_inventories.append(
            _syft_inventory(source_path, entry.get("scan_area"))
        )

    azure = None
    if azure_path_value is not None:
        azure_source_path = _source_path(
            raw_dir, azure_path_value, "azure_inventory"
        )
        if output_path == azure_source_path:
            raise ValueError("inventory output must not overwrite a source input")
        azure = _azure_inventory(azure_source_path)

    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Auxiliary inventory for coverage and manual triage. This is not a "
            "CycloneDX CBOM and does not establish cryptographic algorithm use."
        ),
        "syft_inventories": syft_inventories,
        "azure_inventory": azure,
    }
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
            json.dump(result, stream, indent=2, ensure_ascii=False)
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
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_inventory(args.manifest, args.output)
    candidate_count = sum(
        item["crypto_library_candidate_count"]
        for item in result["syft_inventories"]
    )
    resource_count = (
        result["azure_inventory"]["resource_count"]
        if result["azure_inventory"] is not None
        else 0
    )
    print(
        f"Wrote auxiliary inventory: {candidate_count} crypto-library "
        f"candidates, {resource_count} Azure resources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
