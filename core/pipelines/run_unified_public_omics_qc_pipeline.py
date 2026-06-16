#!/usr/bin/env python3

"""
Run Unified Public Omics QC Pipeline

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Run the unified public cancer omics metadata workflow plus the unified
    inventory quality-control report with one command.

This wrapper can:
    1. Optionally refresh UCSC Xena metadata.
    2. Build the unified GDC + Xena public cancer omics inventory.
    3. Optionally generate the unified inventory HTML report.
    4. Generate the unified inventory QC HTML report.
    5. Optionally open the QC report.

The workflow is metadata-only. It does not download molecular matrices.

Examples:
    python -m core.pipelines.run_unified_public_omics_qc_pipeline

    python -m core.pipelines.run_unified_public_omics_qc_pipeline --make-qc-report

    python -m core.pipelines.run_unified_public_omics_qc_pipeline --make-report --make-qc-report

    python -m core.pipelines.run_unified_public_omics_qc_pipeline --refresh-xena --xena-recommended-only --make-report --make-qc-report --open-qc-report
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from core.integration.unified_public_cancer_omics_inventory import (
    DEFAULT_OUTPUT as DEFAULT_UNIFIED_INVENTORY_OUTPUT,
)
from core.pipelines.run_unified_public_omics_pipeline import (
    DEFAULT_SUMMARY_OUTPUT as DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT,
    run_unified_public_omics_pipeline,
)
from core.reporting.unified_public_cancer_omics_inventory_report import (
    DEFAULT_OUTPUT as DEFAULT_UNIFIED_REPORT_OUTPUT,
)
from core.reporting.unified_public_cancer_omics_qc_report import (
    DEFAULT_OUTPUT as DEFAULT_QC_REPORT_OUTPUT,
    generate_unified_public_cancer_omics_qc_report,
)
from core.search.xena_dataset_inventory import (
    DEFAULT_OUTPUT as DEFAULT_XENA_DATASET_INVENTORY,
)


def run_unified_public_omics_qc_pipeline(
    unified_output_path: Path = DEFAULT_UNIFIED_INVENTORY_OUTPUT,
    summary_output_path: Path = DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT,
    report_output_path: Path = DEFAULT_UNIFIED_REPORT_OUTPUT,
    qc_report_output_path: Path = DEFAULT_QC_REPORT_OUTPUT,
    report_title: str = "Unified Public Cancer Omics Inventory Report",
    qc_report_title: str = "Unified Public Cancer Omics Inventory QC Report",
    gdc_input: Optional[Path] = None,
    xena_input: Path = DEFAULT_XENA_DATASET_INVENTORY,
    strict_inputs: bool = False,
    refresh_xena: bool = False,
    xena_recommended_only: bool = False,
    xena_min_priority: Optional[int] = None,
    xena_timeout: int = 60,
    xena_sleep_seconds: float = 0.0,
    xena_strict: bool = False,
    make_report: bool = False,
    make_qc_report: bool = True,
    open_report: bool = False,
    open_qc_report: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[str]]:
    """
    Run unified public omics workflow and optionally generate QC report.
    """
    unified_df, summary_df = run_unified_public_omics_pipeline(
        unified_output_path=unified_output_path,
        summary_output_path=summary_output_path,
        report_output_path=report_output_path,
        report_title=report_title,
        gdc_input=gdc_input,
        xena_input=xena_input,
        strict_inputs=strict_inputs,
        refresh_xena=refresh_xena,
        xena_recommended_only=xena_recommended_only,
        xena_min_priority=xena_min_priority,
        xena_timeout=xena_timeout,
        xena_sleep_seconds=xena_sleep_seconds,
        xena_strict=xena_strict,
        make_report=make_report,
        open_report=open_report,
    )

    qc_html = None

    if make_qc_report:
        qc_html = generate_unified_public_cancer_omics_qc_report(
            input_path=unified_output_path,
            output_path=qc_report_output_path,
            title=qc_report_title,
        )

        print("\nUnified public omics QC pipeline summary:")
        print(f"  qc_report_output: {qc_report_output_path}")
        print(f"  qc_report_html_characters: {len(qc_html)}")

    if open_qc_report and make_qc_report and qc_report_output_path.exists():
        webbrowser.open(qc_report_output_path.resolve().as_uri())

    print("\nUnified public omics QC pipeline complete.")

    return unified_df, summary_df, qc_html


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run unified public cancer omics pipeline plus QC report."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_UNIFIED_INVENTORY_OUTPUT,
        help=f"Unified inventory output TSV. Default: {DEFAULT_UNIFIED_INVENTORY_OUTPUT}",
    )

    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT,
        help=f"Pipeline summary TSV. Default: {DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_UNIFIED_REPORT_OUTPUT,
        help=f"Unified inventory HTML report output. Default: {DEFAULT_UNIFIED_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--qc-report",
        type=Path,
        default=DEFAULT_QC_REPORT_OUTPUT,
        help=f"Unified inventory QC HTML report output. Default: {DEFAULT_QC_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--report-title",
        default="Unified Public Cancer Omics Inventory Report",
        help="Unified inventory HTML report title.",
    )

    parser.add_argument(
        "--qc-report-title",
        default="Unified Public Cancer Omics Inventory QC Report",
        help="Unified inventory QC HTML report title.",
    )

    parser.add_argument(
        "--gdc-input",
        type=Path,
        default=None,
        help="Optional GDC inventory/ranking TSV. If omitted, known default GDC paths are checked.",
    )

    parser.add_argument(
        "--xena-input",
        type=Path,
        default=DEFAULT_XENA_DATASET_INVENTORY,
        help=f"Xena dataset inventory TSV. Default: {DEFAULT_XENA_DATASET_INVENTORY}",
    )

    parser.add_argument(
        "--strict-inputs",
        action="store_true",
        help="Require both GDC and Xena inputs.",
    )

    parser.add_argument(
        "--refresh-xena",
        action="store_true",
        help="Refresh Xena dataset inventory before building unified inventory.",
    )

    parser.add_argument(
        "--xena-recommended-only",
        action="store_true",
        help="When refreshing Xena, query only recommended Xena hubs.",
    )

    parser.add_argument(
        "--xena-min-priority",
        type=int,
        default=None,
        help="When refreshing Xena, query hubs with priority_for_atlas >= this value.",
    )

    parser.add_argument(
        "--xena-timeout",
        type=int,
        default=60,
        help="HTTP timeout for Xena refresh.",
    )

    parser.add_argument(
        "--xena-sleep-seconds",
        type=float,
        default=0.0,
        help="Optional sleep between Xena hub queries.",
    )

    parser.add_argument(
        "--xena-strict",
        action="store_true",
        help="Fail Xena refresh immediately on hub query error.",
    )

    parser.add_argument(
        "--make-report",
        action="store_true",
        help="Generate unified public cancer omics inventory HTML report.",
    )

    parser.add_argument(
        "--make-qc-report",
        action="store_true",
        help="Generate unified public cancer omics inventory QC HTML report.",
    )

    parser.add_argument(
        "--no-qc-report",
        action="store_true",
        help="Disable QC report generation.",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open generated unified inventory HTML report. Requires --make-report.",
    )

    parser.add_argument(
        "--open-qc-report",
        action="store_true",
        help="Open generated unified inventory QC HTML report. Requires QC report generation.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    make_qc_report = args.make_qc_report or not args.no_qc_report

    try:
        run_unified_public_omics_qc_pipeline(
            unified_output_path=args.output,
            summary_output_path=args.summary,
            report_output_path=args.report,
            qc_report_output_path=args.qc_report,
            report_title=args.report_title,
            qc_report_title=args.qc_report_title,
            gdc_input=args.gdc_input,
            xena_input=args.xena_input,
            strict_inputs=args.strict_inputs,
            refresh_xena=args.refresh_xena,
            xena_recommended_only=args.xena_recommended_only,
            xena_min_priority=args.xena_min_priority,
            xena_timeout=args.xena_timeout,
            xena_sleep_seconds=args.xena_sleep_seconds,
            xena_strict=args.xena_strict,
            make_report=args.make_report,
            make_qc_report=make_qc_report,
            open_report=args.open_report,
            open_qc_report=args.open_qc_report,
        )
    except Exception as exc:
        print(f"ERROR: Unified public omics QC pipeline failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
