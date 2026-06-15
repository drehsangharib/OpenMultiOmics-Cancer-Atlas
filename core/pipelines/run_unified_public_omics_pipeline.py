#!/usr/bin/env python3

"""
Run Unified Public Omics Pipeline

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Run the unified public cancer omics workflow with one command.

This pipeline can:
    1. Optionally refresh the UCSC Xena metadata inventory.
    2. Build the unified GDC + Xena public cancer omics inventory.
    3. Optionally generate the unified inventory HTML report.
    4. Write a pipeline summary TSV.

The pipeline is metadata-only. It does not download molecular matrices.

Examples:
    python -m core.pipelines.run_unified_public_omics_pipeline

    python -m core.pipelines.run_unified_public_omics_pipeline --make-report

    python -m core.pipelines.run_unified_public_omics_pipeline --make-report --open-report

    python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --make-report

    python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report
"""

from __future__ import annotations

import argparse
import sys
import time
import webbrowser
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from core.integration.unified_public_cancer_omics_inventory import (
    DEFAULT_OUTPUT as DEFAULT_UNIFIED_INVENTORY_OUTPUT,
    write_unified_public_cancer_omics_inventory,
)
from core.pipelines.run_xena_metadata_pipeline import (
    run_xena_metadata_pipeline,
)
from core.reporting.unified_public_cancer_omics_inventory_report import (
    DEFAULT_OUTPUT as DEFAULT_UNIFIED_REPORT_OUTPUT,
    generate_unified_public_cancer_omics_inventory_report,
)
from core.search.xena_dataset_inventory import (
    DEFAULT_OUTPUT as DEFAULT_XENA_DATASET_INVENTORY,
)


DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/unified_public_omics_pipeline_summary.tsv")


def format_seconds(seconds: float) -> str:
    """
    Format elapsed seconds in a compact readable form.
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remainder = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remainder:.1f}s"

    hours = minutes // 60
    minutes = minutes % 60

    return f"{hours}h {minutes}m {remainder:.1f}s"


def safe_count_by_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Build simple count table for one column.
    """
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=["summary_type", "name", "count"])

    value_counts = df[column].fillna("").astype(str).value_counts()

    rows = []
    for name, count in value_counts.items():
        rows.append(
            {
                "summary_type": column,
                "name": str(name),
                "count": int(count),
            }
        )

    return pd.DataFrame(rows, columns=["summary_type", "name", "count"])


def build_unified_pipeline_summary_table(
    unified_df: pd.DataFrame,
    elapsed_seconds: float = 0.0,
    xena_refreshed: bool = False,
    report_generated: bool = False,
    unified_output_path: Optional[Path] = None,
    summary_output_path: Optional[Path] = None,
    report_output_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Build summary table for the unified public omics pipeline.
    """
    total_rows = int(len(unified_df))

    source_count = 0
    if not unified_df.empty and "source_id" in unified_df.columns:
        source_count = int(unified_df["source_id"].nunique())

    record_type_count = 0
    if not unified_df.empty and "source_record_type" in unified_df.columns:
        record_type_count = int(unified_df["source_record_type"].nunique())

    unknown_modality_rows = 0
    if not unified_df.empty and "omics_modality" in unified_df.columns:
        unknown_modality_rows = int((unified_df["omics_modality"] == "unknown").sum())

    summary_rows = [
        {
            "summary_type": "pipeline_metric",
            "name": "total_unified_rows",
            "count": total_rows,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "source_count",
            "count": source_count,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "record_type_count",
            "count": record_type_count,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "unknown_modality_rows",
            "count": unknown_modality_rows,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "elapsed_seconds_rounded",
            "count": round(float(elapsed_seconds), 3),
        },
        {
            "summary_type": "pipeline_metric",
            "name": "xena_refreshed",
            "count": int(bool(xena_refreshed)),
        },
        {
            "summary_type": "pipeline_metric",
            "name": "report_generated",
            "count": int(bool(report_generated)),
        },
    ]

    if unified_output_path is not None:
        summary_rows.append(
            {
                "summary_type": "pipeline_output",
                "name": "unified_inventory_path",
                "count": str(unified_output_path),
            }
        )

    if summary_output_path is not None:
        summary_rows.append(
            {
                "summary_type": "pipeline_output",
                "name": "summary_path",
                "count": str(summary_output_path),
            }
        )

    if report_output_path is not None:
        summary_rows.append(
            {
                "summary_type": "pipeline_output",
                "name": "report_path",
                "count": str(report_output_path),
            }
        )

    summary_df = pd.DataFrame(summary_rows)

    count_tables = [
        safe_count_by_column(unified_df, "source_id"),
        safe_count_by_column(unified_df, "source_record_type"),
        safe_count_by_column(unified_df, "omics_modality"),
        safe_count_by_column(unified_df, "data_category"),
        safe_count_by_column(unified_df, "cancer_scope"),
    ]

    non_empty_count_tables = [table for table in count_tables if not table.empty]

    if non_empty_count_tables:
        summary_df = pd.concat(
            [summary_df] + non_empty_count_tables,
            ignore_index=True,
        )

    return summary_df.loc[:, ["summary_type", "name", "count"]]


def write_unified_pipeline_summary(
    unified_df: pd.DataFrame,
    summary_output_path: Path = DEFAULT_SUMMARY_OUTPUT,
    elapsed_seconds: float = 0.0,
    xena_refreshed: bool = False,
    report_generated: bool = False,
    unified_output_path: Optional[Path] = None,
    report_output_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Write unified public omics pipeline summary TSV.
    """
    summary_df = build_unified_pipeline_summary_table(
        unified_df=unified_df,
        elapsed_seconds=elapsed_seconds,
        xena_refreshed=xena_refreshed,
        report_generated=report_generated,
        unified_output_path=unified_output_path,
        summary_output_path=summary_output_path,
        report_output_path=report_output_path,
    )

    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_output_path, sep="\t", index=False)

    return summary_df


def print_unified_pipeline_summary(
    unified_df: pd.DataFrame,
    elapsed_seconds: float,
    unified_output_path: Path,
    summary_output_path: Path,
    report_output_path: Optional[Path] = None,
    xena_refreshed: bool = False,
    report_generated: bool = False,
) -> None:
    """
    Print readable pipeline summary.
    """
    print("\nUnified public omics pipeline summary:")
    print(f"  unified_inventory_rows: {len(unified_df)}")
    print(f"  elapsed_time: {format_seconds(elapsed_seconds)}")
    print(f"  xena_refreshed: {int(bool(xena_refreshed))}")
    print(f"  unified_inventory_output: {unified_output_path}")
    print(f"  summary_output: {summary_output_path}")

    if report_generated and report_output_path is not None:
        print(f"  report_output: {report_output_path}")

    if not unified_df.empty and "source_id" in unified_df.columns:
        print("\nRows by source:")
        for source_id, count in unified_df["source_id"].fillna("").astype(str).value_counts().items():
            print(f"  {source_id}: {count}")

    if not unified_df.empty and "source_record_type" in unified_df.columns:
        print("\nRows by record type:")
        for record_type, count in unified_df["source_record_type"].fillna("").astype(str).value_counts().items():
            print(f"  {record_type}: {count}")

    if not unified_df.empty and "omics_modality" in unified_df.columns:
        print("\nRows by modality:")
        for modality, count in unified_df["omics_modality"].fillna("").astype(str).value_counts().head(12).items():
            print(f"  {modality}: {count}")


def run_unified_public_omics_pipeline(
    unified_output_path: Path = DEFAULT_UNIFIED_INVENTORY_OUTPUT,
    summary_output_path: Path = DEFAULT_SUMMARY_OUTPUT,
    report_output_path: Path = DEFAULT_UNIFIED_REPORT_OUTPUT,
    report_title: str = "Unified Public Cancer Omics Inventory Report",
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
    open_report: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run unified public cancer omics inventory pipeline.
    """
    start = time.time()

    if refresh_xena:
        run_xena_metadata_pipeline(
            output_path=xena_input,
            recommended_only=xena_recommended_only,
            min_priority=xena_min_priority,
            timeout=xena_timeout,
            sleep_seconds=xena_sleep_seconds,
            strict=xena_strict,
            make_report=False,
            open_report=False,
        )

    unified_df = write_unified_public_cancer_omics_inventory(
        output_path=unified_output_path,
        gdc_input=gdc_input,
        xena_input=xena_input,
        allow_missing_inputs=not strict_inputs,
    )

    report_generated = False

    if make_report:
        generate_unified_public_cancer_omics_inventory_report(
            input_path=unified_output_path,
            output_path=report_output_path,
            title=report_title,
        )
        report_generated = True

    elapsed = time.time() - start

    summary_df = write_unified_pipeline_summary(
        unified_df=unified_df,
        summary_output_path=summary_output_path,
        elapsed_seconds=elapsed,
        xena_refreshed=refresh_xena,
        report_generated=report_generated,
        unified_output_path=unified_output_path,
        report_output_path=report_output_path if make_report else None,
    )

    print_unified_pipeline_summary(
        unified_df=unified_df,
        elapsed_seconds=elapsed,
        unified_output_path=unified_output_path,
        summary_output_path=summary_output_path,
        report_output_path=report_output_path if make_report else None,
        xena_refreshed=refresh_xena,
        report_generated=report_generated,
    )

    if open_report and make_report and report_output_path.exists():
        webbrowser.open(report_output_path.resolve().as_uri())

    return unified_df, summary_df


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run unified public cancer omics metadata-only pipeline."
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
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Pipeline summary output TSV. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_UNIFIED_REPORT_OUTPUT,
        help=f"Unified inventory HTML report output. Default: {DEFAULT_UNIFIED_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--report-title",
        default="Unified Public Cancer Omics Inventory Report",
        help="HTML report title.",
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
        "--open-report",
        action="store_true",
        help="Open generated unified inventory HTML report. Requires --make-report.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_unified_public_omics_pipeline(
            unified_output_path=args.output,
            summary_output_path=args.summary,
            report_output_path=args.report,
            report_title=args.report_title,
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
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: Unified public omics pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("\nUnified public omics pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
