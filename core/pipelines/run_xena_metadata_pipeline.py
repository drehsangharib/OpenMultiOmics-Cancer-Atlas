#!/usr/bin/env python3

"""
Run UCSC Xena Metadata Pipeline

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Run the UCSC Xena metadata-only dataset inventory workflow with one command.

This pipeline wraps core.search.xena_dataset_inventory and can write:
    1. Live Xena dataset inventory TSV
    2. Xena metadata pipeline summary TSV
    3. Optional Xena dataset inventory HTML report

The pipeline does not download molecular matrices. It only queries dataset
metadata from selected Xena hubs.

Examples:
    python -m core.pipelines.run_xena_metadata_pipeline --recommended-only

    python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report

    python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report

    python -m core.pipelines.run_xena_metadata_pipeline --hub-id gdc_xena

    python -m core.pipelines.run_xena_metadata_pipeline --hub-id gdc_xena --hub-id tcga_xena
"""

from __future__ import annotations

import argparse
import sys
import time
import webbrowser
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from core.reporting.xena_dataset_inventory_report import (
    DEFAULT_OUTPUT as DEFAULT_XENA_REPORT_OUTPUT,
    generate_xena_dataset_inventory_report,
)
from core.search.xena_dataset_inventory import (
    DEFAULT_OUTPUT as DEFAULT_XENA_DATASET_INVENTORY,
    write_xena_dataset_inventory,
)


DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/xena_metadata_pipeline_summary.tsv")


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
    Return count table for one column.

    This implementation avoids pandas-version-dependent column names from
    value_counts().reset_index().
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


def build_xena_pipeline_summary_table(
    inventory_df: pd.DataFrame,
    elapsed_seconds: float = 0.0,
    report_path: Optional[Path] = None,
    report_generated: bool = False,
) -> pd.DataFrame:
    """
    Build summary table for a Xena metadata pipeline run.
    """
    total_rows = int(len(inventory_df))
    query_error_rows = 0

    if "integration_stage" in inventory_df.columns:
        query_error_rows = int((inventory_df["integration_stage"] == "query_error").sum())

    summary_rows = [
        {
            "summary_type": "pipeline_metric",
            "name": "total_dataset_rows",
            "count": total_rows,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "query_error_rows",
            "count": query_error_rows,
        },
        {
            "summary_type": "pipeline_metric",
            "name": "elapsed_seconds_rounded",
            "count": round(float(elapsed_seconds), 3),
        },
        {
            "summary_type": "pipeline_metric",
            "name": "report_generated",
            "count": int(bool(report_generated)),
        },
    ]

    if report_path is not None:
        summary_rows.append(
            {
                "summary_type": "pipeline_output",
                "name": "report_path",
                "count": str(report_path),
            }
        )

    summary_df = pd.DataFrame(summary_rows)

    count_tables = [
        safe_count_by_column(inventory_df, "hub_id"),
        safe_count_by_column(inventory_df, "omics_modality"),
        safe_count_by_column(inventory_df, "data_category"),
        safe_count_by_column(inventory_df, "integration_stage"),
    ]

    non_empty_count_tables = [table for table in count_tables if not table.empty]

    if non_empty_count_tables:
        summary_df = pd.concat(
            [summary_df] + non_empty_count_tables,
            ignore_index=True,
        )

    return summary_df.loc[:, ["summary_type", "name", "count"]]


def write_xena_pipeline_summary(
    inventory_df: pd.DataFrame,
    summary_path: Path = DEFAULT_SUMMARY_OUTPUT,
    elapsed_seconds: float = 0.0,
    report_path: Optional[Path] = None,
    report_generated: bool = False,
) -> pd.DataFrame:
    """
    Write Xena metadata pipeline summary TSV.
    """
    summary_df = build_xena_pipeline_summary_table(
        inventory_df=inventory_df,
        elapsed_seconds=elapsed_seconds,
        report_path=report_path,
        report_generated=report_generated,
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_path, sep="\t", index=False)

    return summary_df


def print_xena_pipeline_summary(
    inventory_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    output_path: Path,
    summary_path: Path,
    elapsed_seconds: float,
    report_path: Optional[Path] = None,
    report_generated: bool = False,
) -> None:
    """
    Print readable Xena metadata pipeline summary.
    """
    print("\nXena metadata pipeline summary:")
    print(f"  dataset_inventory_rows: {len(inventory_df)}")
    print(f"  elapsed_time: {format_seconds(elapsed_seconds)}")
    print(f"  dataset_inventory_output: {output_path}")
    print(f"  summary_output: {summary_path}")

    if report_generated and report_path is not None:
        print(f"  report_output: {report_path}")

    if not inventory_df.empty and "hub_id" in inventory_df.columns:
        print("\nRows by hub:")
        hub_counts = inventory_df["hub_id"].fillna("").astype(str).value_counts()
        for hub_id, count in hub_counts.items():
            print(f"  {hub_id}: {count}")

    if not inventory_df.empty and "omics_modality" in inventory_df.columns:
        print("\nRows by modality:")
        modality_counts = inventory_df["omics_modality"].fillna("").astype(str).value_counts()
        for modality, count in modality_counts.items():
            print(f"  {modality}: {count}")

    query_error_rows = 0

    if "integration_stage" in inventory_df.columns:
        query_error_rows = int((inventory_df["integration_stage"] == "query_error").sum())

    print(f"\nQuery-error rows: {query_error_rows}")


def run_xena_metadata_pipeline(
    output_path: Path = DEFAULT_XENA_DATASET_INVENTORY,
    summary_path: Path = DEFAULT_SUMMARY_OUTPUT,
    report_path: Path = DEFAULT_XENA_REPORT_OUTPUT,
    report_title: str = "UCSC Xena Dataset Inventory Report",
    hub_ids: Optional[Iterable[str]] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
    strict: bool = False,
    make_report: bool = False,
    open_report: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run Xena metadata-only dataset inventory pipeline.
    """
    start = time.time()

    inventory_df = write_xena_dataset_inventory(
        output_path=output_path,
        hub_ids=hub_ids,
        recommended_only=recommended_only,
        min_priority=min_priority,
        timeout=timeout,
        sleep_seconds=sleep_seconds,
        allow_failures=not strict,
    )

    report_generated = False

    if make_report:
        generate_xena_dataset_inventory_report(
            input_path=output_path,
            output_path=report_path,
            title=report_title,
        )
        report_generated = True

    elapsed = time.time() - start

    summary_df = write_xena_pipeline_summary(
        inventory_df=inventory_df,
        summary_path=summary_path,
        elapsed_seconds=elapsed,
        report_path=report_path if make_report else None,
        report_generated=report_generated,
    )

    print_xena_pipeline_summary(
        inventory_df=inventory_df,
        summary_df=summary_df,
        output_path=output_path,
        summary_path=summary_path,
        elapsed_seconds=elapsed,
        report_path=report_path if make_report else None,
        report_generated=report_generated,
    )

    if open_report and make_report and report_path.exists():
        webbrowser.open(report_path.resolve().as_uri())

    return inventory_df, summary_df


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run metadata-only UCSC Xena dataset inventory pipeline."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_XENA_DATASET_INVENTORY,
        help=f"Output Xena dataset inventory TSV. Default: {DEFAULT_XENA_DATASET_INVENTORY}",
    )

    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Output Xena metadata pipeline summary TSV. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_XENA_REPORT_OUTPUT,
        help=f"Output Xena dataset inventory HTML report. Default: {DEFAULT_XENA_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--report-title",
        default="UCSC Xena Dataset Inventory Report",
        help="HTML report title.",
    )

    parser.add_argument(
        "--hub-id",
        action="append",
        default=None,
        help="Hub ID to query. Can be repeated, e.g. --hub-id gdc_xena --hub-id tcga_xena.",
    )

    parser.add_argument(
        "--recommended-only",
        action="store_true",
        help="Query only hubs recommended for first integration.",
    )

    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Query only hubs with priority_for_atlas >= this value.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional sleep between hub queries.",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if any hub query fails.",
    )

    parser.add_argument(
        "--make-report",
        action="store_true",
        help="Generate Xena dataset inventory HTML report after inventory creation.",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open generated Xena dataset inventory HTML report. Requires --make-report.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_xena_metadata_pipeline(
            output_path=args.output,
            summary_path=args.summary,
            report_path=args.report,
            report_title=args.report_title,
            hub_ids=args.hub_id,
            recommended_only=args.recommended_only,
            min_priority=args.min_priority,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
            strict=args.strict,
            make_report=args.make_report,
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: Xena metadata pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("\nXena metadata pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())