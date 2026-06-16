#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import yaml

from core.atlas.build_keyword_public_omics_atlas import (
    build_keyword_public_omics_atlas,
    default_output_path,
    default_report_path,
)


def load_atlas_definition(config_path):
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Atlas definition file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Atlas definition must be a YAML mapping: {config_path}")

    atlas_name = data.get("atlas_name")
    keywords = data.get("keywords")

    if not atlas_name or not isinstance(atlas_name, str):
        raise ValueError(f"'atlas_name' is required and must be a string in {config_path}")

    if not keywords or not isinstance(keywords, list):
        raise ValueError(f"'keywords' is required and must be a list in {config_path}")

    return data


def resolve_input_path(config):
    value = config.get("input")
    return Path(value) if value else None


def resolve_output_path(config):
    value = config.get("output")
    if value:
        return Path(value)
    return default_output_path(config["atlas_name"])


def resolve_report_path(config):
    value = config.get("report")
    if value:
        return Path(value)
    return default_report_path(config["atlas_name"])


def build_keyword_public_omics_atlas_from_config(config_path):
    config = load_atlas_definition(config_path)

    atlas_name = config["atlas_name"]
    keywords = config["keywords"]

    input_path = resolve_input_path(config)
    output_path = resolve_output_path(config)
    report_path = resolve_report_path(config)
    report_title = config.get("report_title")
    min_priority = config.get("min_priority")
    allowed_sources = config.get("allowed_sources")
    make_report = bool(config.get("make_report", True))

    atlas_df = build_keyword_public_omics_atlas(
        atlas_name=atlas_name,
        keywords=keywords,
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
        make_report=make_report,
        report_title=report_title,
        min_priority=min_priority,
        allowed_sources=allowed_sources,
    )

    return atlas_df, output_path, report_path, config


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a keyword-driven public omics atlas slice from a YAML atlas definition."
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to YAML atlas definition file.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        atlas_df, output_path, report_path, config = build_keyword_public_omics_atlas_from_config(args.config)
    except Exception as exc:
        print(f"ERROR: Failed to build atlas from config: {exc}", file=sys.stderr)
        return 1

    print(f"{config['atlas_name'].upper()} public omics atlas from config complete.")
    print(f"Rows: {len(atlas_df)}")
    print(f"Output: {output_path}")

    if bool(config.get("make_report", True)):
        print(f"Report: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())