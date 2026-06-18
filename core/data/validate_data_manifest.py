#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_MANIFEST_DIR = Path("configs/data_manifests")
DEFAULT_VALIDATION_SUMMARY = Path("outputs/reports/data_manifest_validation_summary.tsv")

REQUIRED_TOP_LEVEL_KEYS = [
    "manifest_id",
    "atlas_name",
    "modality",
    "data_type",
    "assay",
    "species",
    "source_name",
    "source_url",
    "access_level",
    "input_files",
    "sample_metadata",
    "processing_plan",
    "expected_outputs",
    "agent_role",
]

SUPPORTED_MODALITIES = {
    "transcriptomics",
    "proteomics",
    "epigenome",
    "metabolomics",
    "multiomics",
}

SUPPORTED_MATRIX_ORIENTATIONS = {
    "samples_by_features",
    "features_by_samples",
}


def load_yaml_mapping(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Data manifest not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Data manifest must be a YAML mapping: {path}")

    return data


def require_nonempty_string(data, key, source_label):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string in {source_label}")
    return value.strip()


def require_mapping(data, key, source_label):
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"'{key}' must be a mapping in {source_label}")
    return value


def require_list(data, key, source_label):
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"'{key}' must be a non-empty list in {source_label}")
    return value


def validate_input_files(input_files, source_label):
    cleaned = []

    for item in input_files:
        if not isinstance(item, dict):
            raise ValueError(f"Each input_files item must be a mapping in {source_label}")

        for key in [
            "file_id",
            "path",
            "file_format",
            "matrix_orientation",
            "sample_id_column",
            "feature_id_type",
        ]:
            if not isinstance(item.get(key), str) or not item.get(key).strip():
                raise ValueError(f"input_files item missing non-empty '{key}' in {source_label}")

        orientation = item["matrix_orientation"].strip()
        if orientation not in SUPPORTED_MATRIX_ORIENTATIONS:
            raise ValueError(
                f"Unsupported matrix_orientation '{orientation}' in {source_label}. "
                f"Supported: {sorted(SUPPORTED_MATRIX_ORIENTATIONS)}"
            )

        cleaned.append(
            {
                "file_id": item["file_id"].strip(),
                "path": item["path"].strip(),
                "file_format": item["file_format"].strip(),
                "matrix_orientation": orientation,
                "sample_id_column": item["sample_id_column"].strip(),
                "feature_id_type": item["feature_id_type"].strip(),
            }
        )

    return cleaned


def validate_manifest_data(data, source_label="<memory>"):
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise ValueError(f"Missing required key '{key}' in {source_label}")

    manifest_id = require_nonempty_string(data, "manifest_id", source_label)
    atlas_name = require_nonempty_string(data, "atlas_name", source_label)
    modality = require_nonempty_string(data, "modality", source_label).lower()
    data_type = require_nonempty_string(data, "data_type", source_label)
    assay = require_nonempty_string(data, "assay", source_label)
    species = require_nonempty_string(data, "species", source_label)
    source_name = require_nonempty_string(data, "source_name", source_label)
    source_url = require_nonempty_string(data, "source_url", source_label)
    access_level = require_nonempty_string(data, "access_level", source_label)

    if modality not in SUPPORTED_MODALITIES:
        raise ValueError(
            f"Unsupported modality '{modality}' in {source_label}. "
            f"Supported: {sorted(SUPPORTED_MODALITIES)}"
        )

    input_files = validate_input_files(require_list(data, "input_files", source_label), source_label)

    sample_metadata = require_mapping(data, "sample_metadata", source_label)
    if not isinstance(sample_metadata.get("path"), str) or not sample_metadata["path"].strip():
        raise ValueError(f"sample_metadata.path must be a non-empty string in {source_label}")
    if not isinstance(sample_metadata.get("sample_id_column"), str) or not sample_metadata["sample_id_column"].strip():
        raise ValueError(f"sample_metadata.sample_id_column must be a non-empty string in {source_label}")

    feature_metadata = data.get("feature_metadata", {})
    if feature_metadata is not None and not isinstance(feature_metadata, dict):
        raise ValueError(f"feature_metadata must be a mapping if provided in {source_label}")

    processing_plan = require_mapping(data, "processing_plan", source_label)
    expected_outputs = require_mapping(data, "expected_outputs", source_label)
    agent_role = require_mapping(data, "agent_role", source_label)

    if not isinstance(agent_role.get("stage"), str) or not agent_role["stage"].strip():
        raise ValueError(f"agent_role.stage must be a non-empty string in {source_label}")
    if not isinstance(agent_role.get("purpose"), str) or not agent_role["purpose"].strip():
        raise ValueError(f"agent_role.purpose must be a non-empty string in {source_label}")

    normalized = {
        "manifest_id": manifest_id,
        "atlas_name": atlas_name,
        "modality": modality,
        "data_type": data_type,
        "assay": assay,
        "species": species,
        "source_name": source_name,
        "source_url": source_url,
        "access_level": access_level,
        "input_files": input_files,
        "sample_metadata": sample_metadata,
        "feature_metadata": feature_metadata or {},
        "processing_plan": processing_plan,
        "expected_outputs": expected_outputs,
        "agent_role": agent_role,
    }

    return normalized


def validate_manifest_file(path):
    data = load_yaml_mapping(path)
    return validate_manifest_data(data, source_label=str(path))


def list_manifest_files(manifest_dir):
    manifest_dir = Path(manifest_dir)

    if not manifest_dir.exists():
        raise FileNotFoundError(f"Manifest directory not found: {manifest_dir}")

    paths = sorted(list(manifest_dir.glob("*.yaml")) + list(manifest_dir.glob("*.yml")))

    if not paths:
        raise FileNotFoundError(f"No YAML data manifests found in: {manifest_dir}")

    return paths


def validate_manifest_dir(manifest_dir, summary_output=DEFAULT_VALIDATION_SUMMARY):
    rows = []

    for manifest_path in list_manifest_files(manifest_dir):
        manifest = validate_manifest_file(manifest_path)
        rows.append(
            {
                "manifest_id": manifest["manifest_id"],
                "atlas_name": manifest["atlas_name"],
                "modality": manifest["modality"],
                "data_type": manifest["data_type"],
                "assay": manifest["assay"],
                "source_name": manifest["source_name"],
                "access_level": manifest["access_level"],
                "input_file_count": len(manifest["input_files"]),
                "agent_stage": manifest["agent_role"]["stage"],
                "manifest_path": str(manifest_path),
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_output = Path(summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_output, sep="\t", index=False)

    return summary_df


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Validate modality-aware data manifests for the AI multi-omics analysis agent/system."
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--manifest",
        type=Path,
        help="Validate one data manifest YAML file.",
    )

    group.add_argument(
        "--manifest-dir",
        type=Path,
        help="Validate all data manifest YAML files in a directory.",
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_VALIDATION_SUMMARY,
        help=f"Validation summary TSV output. Default: {DEFAULT_VALIDATION_SUMMARY}",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.manifest is not None:
            manifest = validate_manifest_file(args.manifest)
            print(f"{manifest['manifest_id']} is valid.")
            print(f"Atlas: {manifest['atlas_name']}")
            print(f"Modality: {manifest['modality']}")
            print(f"Input files: {len(manifest['input_files'])}")
        else:
            summary_df = validate_manifest_dir(
                args.manifest_dir,
                summary_output=args.summary_output,
            )
            print("Data manifest registry validation complete.")
            print(f"Manifest count: {len(summary_df)}")
            print(f"Summary output: {args.summary_output}")
    except Exception as exc:
        print(f"ERROR: Data manifest validation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())