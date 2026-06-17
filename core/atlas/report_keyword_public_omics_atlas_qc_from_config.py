#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from core.atlas.build_keyword_public_omics_atlas_from_config import (
    load_atlas_definition,
)
from core.atlas.report_keyword_public_omics_atlas_qc import (
    default_input_path,
    default_output_path,
    generate_keyword_public_omics_atlas_qc_report,
)


def resolve_qc_input_path(config):
    atlas_name = config["atlas_name"]
    value = config.get("output")
    if value:
        return Path(value)
    return default_input_path(atlas_name)


def resolve_qc_output_path(config):
    atlas_name = config["atlas_name"]
    if "qc_report" in config and config["qc_report"]:
        return Path(config["qc_report"])
    return default_output_path(atlas_name)


def resolve_qc_title(config):
    atlas_name = config["atlas_name"]
    if "qc_report_title" in config and config["qc_report_title"]:
        return str(config["qc_report_title"])
    return f"{atlas_name.upper()} Public Omics Atlas QC Report"


def report_keyword_public_omics_atlas_qc_from_config(config_path):
    config = load_atlas_definition(config_path)

    atlas_name = config["atlas_name"]
    input_path = resolve_qc_input_path(config)
    output_path = resolve_qc_output_path(config)
    title = resolve_qc_title(config)

    report_html = generate_keyword_public_omics_atlas_qc_report(
        atlas_name=atlas_name,
        input_path=input_path,
        output_path=output_path,
        title=title,
    )

    return report_html, output_path, config


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate atlas QC report from a YAML atlas definition."
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
        report_html, output_path, config = report_keyword_public_omics_atlas_qc_from_config(args.config)
    except Exception as exc:
        print(f"ERROR: Failed to generate atlas QC report from config: {exc}", file=sys.stderr)
        return 1

    print(f"{config['atlas_name'].upper()} atlas QC from config complete.")
    print(f"HTML characters: {len(report_html)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())