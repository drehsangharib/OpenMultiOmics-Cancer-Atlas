#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_CONFIG_DIR = Path("configs/atlas_definitions")
DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/atlas_definition_validation_summary.tsv")

REQUIRED_KEYS = {
    "atlas_name": str,
    "keywords": list,
}

OPTIONAL_STRING_KEYS = [
    "input",
    "output",
    "report",
    "qc_report",
    "report_title",
    "qc_report_title",
]

OPTIONAL_INT_KEYS = [
    "min_priority",
]

OPTIONAL_BOOL_KEYS = [
    "make_report",
]

OPTIONAL_LIST_STRING_KEYS = [
    "allowed_sources",
]


def load_yaml_mapping(config_path):
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Atlas definition file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Atlas definition must be a YAML mapping: {config_path}")

    return data


def validate_nonempty_string(value, field_name, source_label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string in {source_label}")
    return value.strip()


def validate_list_of_strings(value, field_name, source_label):
    if not isinstance(value, list) or not value:
        raise ValueError(f"'{field_name}' must be a non-empty list in {source_label}")

    cleaned = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"'{field_name}' must contain non-empty strings in {source_label}")
        cleaned.append(item.strip())

    return cleaned


def validate_atlas_definition_data(data, source_label="<memory>"):
    atlas_name = validate_nonempty_string(data.get("atlas_name"), "atlas_name", source_label)
    keywords = validate_list_of_strings(data.get("keywords"), "keywords", source_label)

    normalized = {
        "atlas_name": atlas_name,
        "keywords": keywords,
    }

    for key in OPTIONAL_STRING_KEYS:
        if key in data and data[key] is not None:
            normalized[key] = validate_nonempty_string(data[key], key, source_label)

    for key in OPTIONAL_INT_KEYS:
        if key in data and data[key] is not None:
            if not isinstance(data[key], int):
                raise ValueError(f"'{key}' must be an integer in {source_label}")
            normalized[key] = int(data[key])

    for key in OPTIONAL_BOOL_KEYS:
        if key in data and data[key] is not None:
            if not isinstance(data[key], bool):
                raise ValueError(f"'{key}' must be a boolean in {source_label}")
            normalized[key] = bool(data[key])

    for key in OPTIONAL_LIST_STRING_KEYS:
        if key in data and data[key] is not None:
            normalized[key] = validate_list_of_strings(data[key], key, source_label)

    return normalized


def validate_config_file(config_path):
    data = load_yaml_mapping(config_path)
    return validate_atlas_definition_data(data, source_label=str(config_path))


def list_yaml_configs(config_dir):
    config_dir = Path(config_dir)

    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    config_paths = sorted(list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml")))

    if not config_paths:
        raise FileNotFoundError(f"No YAML atlas definitions found in: {config_dir}")

    return config_paths


def validate_config_dir(config_dir, summary_output_path=DEFAULT_SUMMARY_OUTPUT):
    config_paths = list_yaml_configs(config_dir)

    rows = []

    for config_path in config_paths:
        config = validate_config_file(config_path)

        rows.append(
            {
                "atlas_name": config["atlas_name"],
                "config_path": str(config_path),
                "keywords_count": len(config["keywords"]),
                "has_allowed_sources": int(bool(config.get("allowed_sources"))),
                "make_report": int(config.get("make_report", True)),
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_output_path, sep="\t", index=False)

    return summary_df


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Validate YAML atlas definition files."
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--config",
        type=Path,
        help="Validate one YAML atlas definition file.",
    )

    group.add_argument(
        "--config-dir",
        type=Path,
        help="Validate all YAML atlas definition files in a directory.",
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Validation summary TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.config is not None:
            config = validate_config_file(args.config)
            print(f"{config['atlas_name'].upper()} atlas definition is valid.")
            print(f"Keywords: {len(config['keywords'])}")
            print(f"Config: {args.config}")
        else:
            summary_df = validate_config_dir(
                args.config_dir,
                summary_output_path=args.summary_output,
            )
            print("Atlas definition registry validation complete.")
            print(f"Config count: {len(summary_df)}")
            print(f"Summary output: {args.summary_output}")
    except Exception as exc:
        print(f"ERROR: Atlas definition validation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())