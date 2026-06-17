#!/usr/bin/env python3

import argparse
import sys
import webbrowser
from pathlib import Path

import pandas as pd

from core.atlas.build_keyword_public_omics_atlas_from_config import load_atlas_definition
from core.atlas.report_keyword_public_omics_atlas_qc_from_config import (
    report_keyword_public_omics_atlas_qc_from_config,
)


DEFAULT_CONFIG_DIR = Path("configs/atlas_definitions")
DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/atlas_qc_batch_summary.tsv")


def list_yaml_configs(config_dir):
    config_dir = Path(config_dir)

    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    configs = sorted(list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml")))

    if not configs:
        raise FileNotFoundError(f"No YAML atlas definitions found in: {config_dir}")

    return configs


def select_configs(config_paths, atlas_names=None):
    if not atlas_names:
        return config_paths

    requested = {str(name).strip().lower() for name in atlas_names if str(name).strip()}
    selected = []

    for config_path in config_paths:
        config = load_atlas_definition(config_path)
        atlas_name = str(config.get("atlas_name", "")).strip().lower()

        if atlas_name in requested:
            selected.append(config_path)

    return selected


def run_keyword_public_omics_atlas_qc_batch(
    config_dir=DEFAULT_CONFIG_DIR,
    atlas_names=None,
    summary_output_path=DEFAULT_SUMMARY_OUTPUT,
    open_reports=False,
):
    config_paths = list_yaml_configs(config_dir)
    config_paths = select_configs(config_paths, atlas_names=atlas_names)

    if not config_paths:
        raise ValueError("No atlas definition files selected for batch QC build.")

    rows = []

    for config_path in config_paths:
        report_html, output_path, config = report_keyword_public_omics_atlas_qc_from_config(config_path)

        atlas_name = config["atlas_name"]

        rows.append(
            {
                "atlas_name": atlas_name,
                "qc_html_characters": int(len(report_html)),
                "qc_report_path": str(output_path),
                "config_path": str(config_path),
            }
        )

        print(f"{atlas_name.upper()} atlas QC build complete.")
        print(f"  qc_html_characters: {len(report_html)}")
        print(f"  qc_report: {output_path}")

        if open_reports and Path(output_path).exists():
            webbrowser.open(Path(output_path).resolve().as_uri())

    summary_df = pd.DataFrame(rows)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_output_path, sep="\t", index=False)

    print("\nKeyword atlas QC batch build complete.")
    print(f"Atlas count: {len(summary_df)}")
    print(f"Summary output: {summary_output_path}")

    return summary_df


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate QC reports for multiple keyword-driven atlas definitions."
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help=f"Directory containing atlas definition YAML files. Default: {DEFAULT_CONFIG_DIR}",
    )

    parser.add_argument(
        "--atlases",
        nargs="*",
        default=None,
        help="Optional atlas names to build QC for, e.g. gbm luad brca",
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Batch QC summary TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--open-reports",
        action="store_true",
        help="Open generated QC reports after batch build.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_keyword_public_omics_atlas_qc_batch(
            config_dir=args.config_dir,
            atlas_names=args.atlases,
            summary_output_path=args.summary_output,
            open_reports=args.open_reports,
        )
    except Exception as exc:
        print(f"ERROR: Failed to run keyword atlas QC batch build: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())