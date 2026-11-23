"""Merge CycloneDX 1.6 CBOM inputs while preserving crypto-asset provenance."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCAN_AREAS = frozenset(
    {
        "code-and-libraries",
        "container-images",
        "azure-config",
        "key-vault",
        "endpoint-tls",
    }
)
ASSET_TYPES = frozenset(
    {"algorithm", "certificate", "protocol", "related-crypto-material"}
)
MERGER_VERSION = "1.0.0"
ASSET_NAMESPACE = uuid.UUID("21930d8e-68ce-4f5c-b77a-8ef28a2147d4")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _asset_identity(component: Mapping[str, Any]) -> str:
    crypto_properties = component.get("cryptoProperties")
    if not isinstance(crypto_properties, dict):
        raise ValueError("cryptographic asset is missing cryptoProperties")

    asset_type = crypto_properties.get("assetType")
    if asset_type not in ASSET_TYPES:
        raise ValueError(f"unsupported or missing crypto assetType: {asset_type!r}")

    name = component.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("cryptographic asset is missing a non-empty name")

    identity = {
        "assetType": asset_type,
        "name": name.strip(),
        "cryptoProperties": crypto_properties,
    }
    return _canonical_json(identity)


def _occurrence_key(occurrence: Mapping[str, Any]) -> str:
    location = occurrence.get("location")
    if not isinstance(location, str) or not location.strip():
        raise ValueError("every cryptographic asset occurrence needs a location")
    key_fields = ("location", "line", "offset", "offsetLength")
    return _canonical_json({key: occurrence[key] for key in key_fields if key in occurrence})


def _merge_occurrence(
    current: dict[str, Any], incoming: Mapping[str, Any], key: str
) -> None:
    for field, value in incoming.items():
        if field == "additionalContext":
            if not isinstance(value, str) or (
                field in current and not isinstance(current[field], str)
            ):
                raise ValueError(f"invalid additionalContext for occurrence {key}")
            contexts = {
                item.strip()
                for item in (current.get(field), value)
                if isinstance(item, str) and item.strip()
            }
            if contexts:
                current[field] = " | ".join(sorted(contexts))
            continue
        if field in current and current[field] != value:
            raise ValueError(
                f"conflicting occurrence evidence for {key}: field {field!r}"
            )
        current[field] = copy.deepcopy(value)


def _add_property(properties: list[dict[str, str]], name: str, value: str) -> None:
    item = {"name": name, "value": value}
    if item not in properties:
        properties.append(item)


def _merge_component(
    merged: dict[str, dict[str, Any]],
    component: Mapping[str, Any],
    source_tool: str,
    scan_area: str,
) -> str:
    identity = _asset_identity(component)
    merged_ref = f"urn:uuid:{uuid.uuid5(ASSET_NAMESPACE, identity)}"
    if merged_ref not in merged:
        merged_component = copy.deepcopy(dict(component))
        merged_component["bom-ref"] = merged_ref
        merged_component["properties"] = []
        source_evidence = component.get("evidence", {})
        if not isinstance(source_evidence, dict):
            raise ValueError("cryptographic asset evidence must be an object")
        merged_component["evidence"] = copy.deepcopy(source_evidence)
        merged_component["evidence"]["occurrences"] = []
        merged[merged_ref] = merged_component

    target = merged[merged_ref]
    for field, value in component.items():
        if field in {"bom-ref", "cryptoProperties", "description", "evidence", "name", "properties"}:
            continue
        if field in target and target[field] != value:
            raise ValueError(f"conflicting component field {field!r} for {merged_ref}")
        target[field] = copy.deepcopy(value)

    properties = target.get("properties")
    if not isinstance(properties, list):
        raise ValueError("cryptographic asset properties must be an array")
    source_properties = component.get("properties", [])
    if not isinstance(source_properties, list):
        raise ValueError("cryptographic asset properties must be an array")
    for prop in source_properties:
        if (
            not isinstance(prop, dict)
            or not isinstance(prop.get("name"), str)
            or not isinstance(prop.get("value"), str)
        ):
            raise ValueError("each cryptographic asset property needs string name/value")
        _add_property(properties, prop["name"], prop["value"])
    _add_property(properties, "source_tool", source_tool)
    _add_property(properties, "scan_area", scan_area)

    evidence = component.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("cryptographic asset evidence must be an object")
    target_evidence = target["evidence"]
    for field, value in evidence.items():
        if field == "occurrences":
            continue
        if field not in target_evidence:
            target_evidence[field] = copy.deepcopy(value)
        elif isinstance(value, list) and isinstance(target_evidence[field], list):
            combined = target_evidence[field]
            for item in value:
                if item not in combined:
                    combined.append(copy.deepcopy(item))
        elif target_evidence[field] != value:
            raise ValueError(
                f"conflicting evidence field {field!r} for asset {merged_ref}"
            )
    occurrences = evidence.get("occurrences", [])
    if not isinstance(occurrences, list) or not occurrences:
        raise ValueError("every cryptographic asset needs at least one occurrence")

    target_occurrences = target_evidence["occurrences"]
    occurrence_indexes = {
        _occurrence_key(item): item for item in target_occurrences
    }
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            raise ValueError("each evidence occurrence must be an object")
        key = _occurrence_key(occurrence)
        if key in occurrence_indexes:
            _merge_occurrence(occurrence_indexes[key], occurrence, key)
        else:
            new_occurrence = copy.deepcopy(occurrence)
            target_occurrences.append(new_occurrence)
            occurrence_indexes[key] = new_occurrence

    description = component.get("description")
    if isinstance(description, str) and description.strip():
        descriptions = {
            item.strip()
            for item in (target.get("description"), description)
            if isinstance(item, str) and item.strip()
        }
        target["description"] = " | ".join(sorted(descriptions))
    return merged_ref


def _load_input(
    manifest_dir: Path, entry: Mapping[str, Any]
) -> tuple[dict[str, Any], str, str, Path]:
    path_value = entry.get("path")
    source_tool = entry.get("source_tool")
    scan_area = entry.get("scan_area")
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("each input needs a relative path")
    if not isinstance(source_tool, str) or not source_tool.strip():
        raise ValueError(f"input {path_value!r} needs source_tool")
    if scan_area not in SCAN_AREAS:
        raise ValueError(
            f"input {path_value!r} has unsupported scan_area {scan_area!r}; "
            f"choose one of {', '.join(sorted(SCAN_AREAS))}"
        )

    run_root = manifest_dir.resolve()
    input_path = (manifest_dir / path_value).resolve(strict=True)
    if not input_path.is_relative_to(run_root):
        raise ValueError(f"input path escapes the run directory: {path_value!r}")
    if not input_path.is_file():
        raise ValueError(f"input is not a file: {path_value!r}")

    with input_path.open(encoding="utf-8") as stream:
        bom = json.load(stream)
    if not isinstance(bom, dict):
        raise ValueError(f"input is not a JSON object: {path_value!r}")
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise ValueError(
            f"input {path_value!r} must be a CycloneDX 1.6 BOM; "
            "convert it explicitly before merging"
        )
    supported_top_level = {
        "bomFormat",
        "specVersion",
        "serialNumber",
        "version",
        "metadata",
        "components",
        "dependencies",
    }
    unsupported_content = [
        key
        for key, value in bom.items()
        if key not in supported_top_level and value not in (None, [], {})
    ]
    if unsupported_content:
        raise ValueError(
            f"input {path_value!r} has unsupported top-level data: "
            f"{', '.join(sorted(unsupported_content))}"
        )
    components = bom.get("components")
    if not isinstance(components, list):
        raise ValueError(f"input {path_value!r} must contain a components array")
    for index, component in enumerate(components):
        if not isinstance(component, dict) or component.get("type") != "cryptographic-asset":
            raise ValueError(
                f"input {path_value!r} component {index} is not a cryptographic-asset"
            )
    dependencies = bom.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ValueError(f"input {path_value!r} dependencies must be an array")
    return bom, source_tool.strip(), scan_area, input_path


def merge_manifest(manifest_path: Path, output_path: Path) -> dict[str, Any]:
    """Merge listed CBOM inputs; source files are never modified."""
    manifest_path = manifest_path.resolve(strict=True)
    if manifest_path.parent.name == "raw" or not (manifest_path.parent / "raw").is_dir():
        raise ValueError("manifest must be stored at the run root beside raw/")
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("inputs"), list):
        raise ValueError("manifest must be an object containing an inputs array")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("manifest must contain a non-empty run_id")

    run_root = manifest_path.parent.resolve()
    output_path = output_path.resolve()
    if not output_path.is_relative_to(run_root):
        raise ValueError("output path must remain inside the run directory")
    if output_path == manifest_path:
        raise ValueError("merged output must not overwrite the input manifest")
    raw_dir = (run_root / "raw").resolve()
    if output_path.is_relative_to(raw_dir):
        raise ValueError("merged output must not overwrite or be placed under raw/")

    merged_components: dict[str, dict[str, Any]] = {}
    source_tools: set[str] = set()
    scan_areas: set[str] = set()
    dependency_edges: dict[str, dict[str, set[str]]] = {}
    source_bom_serial_numbers: set[str] = set()

    for entry in manifest["inputs"]:
        if not isinstance(entry, dict):
            raise ValueError("each manifest input must be an object")
        bom, source_tool, scan_area, input_path = _load_input(
            manifest_path.parent, entry
        )
        if output_path == input_path:
            raise ValueError("merged output must not overwrite a source input")
        source_tools.add(source_tool)
        scan_areas.add(scan_area)
        serial_number = bom.get("serialNumber")
        if isinstance(serial_number, str):
            source_bom_serial_numbers.add(serial_number)

        ref_map: dict[str, str] = {}
        for component in bom["components"]:
            merged_ref = _merge_component(
                merged_components, component, source_tool, scan_area
            )
            source_ref = component.get("bom-ref")
            if isinstance(source_ref, str):
                if source_ref in ref_map and ref_map[source_ref] != merged_ref:
                    raise ValueError(f"duplicate bom-ref in input {entry['path']!r}")
                ref_map[source_ref] = merged_ref

        for dependency in bom.get("dependencies", []):
            if not isinstance(dependency, dict) or not isinstance(dependency.get("ref"), str):
                raise ValueError(f"invalid dependency in input {entry['path']!r}")
            ref = dependency["ref"]
            if ref not in ref_map:
                raise ValueError(
                    f"dependency references a component not merged from {entry['path']!r}: {ref}"
                )
            target_ref = ref_map[ref]
            unsupported_dependency_fields = set(dependency) - {
                "ref",
                "dependsOn",
                "provides",
            }
            if unsupported_dependency_fields:
                raise ValueError(
                    f"unsupported dependency fields in input {entry['path']!r}: "
                    f"{', '.join(sorted(unsupported_dependency_fields))}"
                )
            target_edges = dependency_edges.setdefault(
                target_ref, {"dependsOn": set(), "provides": set()}
            )
            for field in ("dependsOn", "provides"):
                refs = dependency.get(field, [])
                if not isinstance(refs, list) or any(
                    not isinstance(item, str) for item in refs
                ):
                    raise ValueError(
                        f"invalid {field} list in input {entry['path']!r}"
                    )
                for item in refs:
                    if item not in ref_map:
                        raise ValueError(
                            f"dependency references a component not merged from "
                            f"{entry['path']!r}: {item}"
                        )
                    target_edges[field].add(ref_map[item])

    components = sorted(
        merged_components.values(),
        key=lambda component: (component["name"], component["bom-ref"]),
    )
    dependencies = [
        {
            "ref": ref,
            "dependsOn": sorted(edges["dependsOn"]),
            **({"provides": sorted(edges["provides"])} if edges["provides"] else {}),
        }
        for ref, edges in sorted(dependency_edges.items())
    ]
    output = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "properties": [
                {"name": "run_id", "value": run_id},
                *(
                    {"name": "source_tool", "value": value}
                    for value in sorted(source_tools)
                ),
                *(
                    {"name": "scan_area", "value": value}
                    for value in sorted(scan_areas)
                ),
                *(
                    {"name": "source_bom_serial_number", "value": value}
                    for value in sorted(source_bom_serial_numbers)
                ),
                {"name": "cbom_merger_version", "value": MERGER_VERSION},
            ],
        },
        "components": components,
        "dependencies": dependencies,
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
        json.dump(output, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = merge_manifest(args.manifest, args.output)
    print(
        f"Wrote {len(result['components'])} cryptographic assets "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
