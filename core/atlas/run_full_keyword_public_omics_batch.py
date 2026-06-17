#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from core.atlas.run_keyword_public_omics_atlas_batch import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_BUILD_SUMMARY_OUTPUT,
    run_keyword_public_omics_atlas_batch,
)
from core.atlas.run_keyword_public_omics_atlas_qc_batch import (
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_QC_SUMMARY_OUTPUT,
    run_keyword_public_omics_atlas_qc_batch,
)


def run_full_keyword_public_omics_batch(
    config_dir=DEFAULT_CONFIG_DIR,
    atlas_names=None,
    build_summary_output_path=DEFAULT_BUILD_SUMMARY_OUTPUT,
    qc_summary_output_path=DEFAULT_QC_SUMMARY_OUTPUT,
    open_reports=False,
):
    build_summary_df = run_keyword_public_omics_atlas_batch(
        config_dir=config_dir,
        atlas_names=atlas_names,
        summary_output_path=build_summary_output_path,
        open_reports=False,
    )

    qc_summary_df = run_keyword_public_omics_atlas_qc_batch(
        config_dir=config_dir,
        atlas_names=atlas_names,
        summary_output_path=qc_summary_output_path,
        open_reports=open_reports,
    )

    print("\nFull keyword atlas batch pipeline complete.")
    print(f"Atlas count: {len(build_summary_df)}")
    print(f"Build summary: {build_summary_output_path}")
    print(f"QC summary: {qc_summary_output_path}")

    return build_summary_df, qc_summary_df


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the full keyword-driven public omics atlas batch pipeline."
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
        help="Optional atlas names to build, e.g. gbm luad brca",
    )

    parser.add_argument(
        "--build-summary-output",
        type=Path,
        default=DEFAULT_BUILD_SUMMARY_OUTPUT,
        help=f"Atlas build batch summary TSV output. Default: {DEFAULT_BUILD_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--qc-summary-output",
        type=Path,
        default=DEFAULT_QC_SUMMARY_OUTPUT,
        help=f"Atlas QC batch summary TSV output. Default: {DEFAULT_QC_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--open-reports",
        action="store_true",
        help="Open generated atlas and QC reports at the end of the batch pipeline.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_full_keyword_public_omics_batch(
            config_dir=args.config_dir,
            atlas_names=args.atlases,
            build_summary_output_path=args.build_summary_output,
            qc_summary_output_path=args.qc_summary_output,
            open_reports=args.open_reports,
        )
    except Exception as exc:
        print(f"ERROR: Failed to run full keyword atlas batch pipeline: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())