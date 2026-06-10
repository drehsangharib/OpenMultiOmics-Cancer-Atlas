#!/usr/bin/env python3

"""
Run GDC Metadata Pipeline

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Run the GDC public metadata workflow end-to-end with one command.

Pipeline steps:
    1. Fetch GDC project inventory
    2. Fetch/summarize GDC file counts by project
    3. Build GDC project modality matrix
    4. Build GDC project priority ranking
    5. Generate GDC priority visual outputs
    6. Generate GDC priority HTML report

Examples:
    # Full official run
    python -m core.pipelines.run_gdc_metadata_pipeline

    # Fast development run without overwriting official outputs
    python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output

    # Reuse existing official file counts and regenerate downstream report
    python -m core.pipelines.run_gdc_metadata_pipeline --report-only --open-report

    # Reuse existing official file counts but regenerate report without embedding images
    python -m core.pipelines.run_gdc_metadata_pipeline --report-only --link-images
"""

from __future__ import annotations

import argparse
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

from core.reporting.gdc_priority_report import (
    DEFAULT_OUTPUT as DEFAULT_REPORT_OUTPUT,
    generate_gdc_priority_report,
)
from core.scoring.gdc_project_priority_ranker import (
    DEFAULT_OUTPUT as DEFAULT_PRIORITY_RANKING,
    build_gdc_project_priority_ranking,
)
from core.search.gdc_file_counts_by_project import (
    DEFAULT_OUTPUT as DEFAULT_FILE_COUNTS,
    build_gdc_file_counts_by_project,
)
from core.search.gdc_project_inventory import (
    DEFAULT_OUTPUT as DEFAULT_PROJECT_INVENTORY,
    build_gdc_project_inventory,
)
from core.search.gdc_project_modality_matrix import (
    DEFAULT_OUTPUT as DEFAULT_MODALITY_MATRIX,
    build_gdc_project_modality_matrix,
)
from core.visualization.gdc_priority_visuals import (
    DEFAULT_FIGURES_DIR,
    generate_gdc_priority_visuals,
)


DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/gdc_metadata_pipeline_summary.tsv")


@dataclass
class PipelineStepResult:
    """
    Metadata for one pipeline step.
    """

    step_name: str
    status: str
    output_path: str
    row_count: Optional[int]
    elapsed_seconds: float


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


def count_tsv_rows(path: Path) -> Optional[int]:
    """
    Count rows in a TSV file, excluding the header.

    Returns None if the file does not exist.
    """
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    return max(0, line_count - 1)


def ensure_required_file(path: Path, description: str) -> None:
    """
    Raise FileNotFoundError if a required file is missing.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Required {description} not found: {path}. "
            "Run the full pipeline first or avoid skip/report-only mode."
        )


def dataframe_row_count(df: pd.DataFrame) -> int:
    """
    Return DataFrame row count safely.
    """
    if df is None:
        return 0

    return int(len(df))


def make_result(
    step_name: str,
    status: str,
    output_path: Path,
    row_count: Optional[int],
    elapsed_seconds: float,
) -> PipelineStepResult:
    """
    Create a pipeline step result.
    """
    return PipelineStepResult(
        step_name=step_name,
        status=status,
        output_path=str(output_path),
        row_count=row_count,
        elapsed_seconds=float(elapsed_seconds),
    )


def build_pipeline_summary_table(results: List[PipelineStepResult]) -> pd.DataFrame:
    """
    Convert pipeline results into a summary table.
    """
    rows = []

    for result in results:
        rows.append(
            {
                "step_name": result.step_name,
                "status": result.status,
                "output_path": result.output_path,
                "row_count": result.row_count,
                "elapsed_seconds": round(result.elapsed_seconds, 3),
            }
        )

    return pd.DataFrame(rows)


def write_pipeline_summary(
    results: List[PipelineStepResult],
    output_path: Path,
) -> None:
    """
    Write pipeline summary TSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df = build_pipeline_summary_table(results)
    summary_df.to_csv(output_path, sep="\t", index=False)


def print_pipeline_summary(results: List[PipelineStepResult]) -> None:
    """
    Print readable pipeline summary.
    """
    print("\nGDC metadata pipeline summary:")

    for result in results:
        row_text = "NA" if result.row_count is None else str(result.row_count)
        elapsed_text = format_seconds(result.elapsed_seconds)

        print(
            f"  {result.step_name}: {result.status} | "
            f"rows/items={row_text} | "
            f"time={elapsed_text} | "
            f"output={result.output_path}"
        )


def run_project_inventory_step(
    output_path: Path,
    size: int,
    timeout: int,
) -> PipelineStepResult:
    """
    Run the GDC project inventory step.
    """
    start = time.time()

    df = build_gdc_project_inventory(
        output_path=output_path,
        size=size,
        timeout=timeout,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="project_inventory",
        status="completed",
        output_path=output_path,
        row_count=dataframe_row_count(df),
        elapsed_seconds=elapsed,
    )


def run_file_counts_step(
    output_path: Path,
    project_inventory_path: Path,
    project_limit: Optional[int],
    page_size: int,
    timeout: int,
    sleep_seconds: float,
) -> PipelineStepResult:
    """
    Run the GDC file counts by project step.
    """
    start = time.time()

    df = build_gdc_file_counts_by_project(
        output_path=output_path,
        project_inventory_path=project_inventory_path,
        project_limit=project_limit,
        page_size=page_size,
        timeout=timeout,
        sleep_seconds=sleep_seconds,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="file_counts_by_project",
        status="completed",
        output_path=output_path,
        row_count=dataframe_row_count(df),
        elapsed_seconds=elapsed,
    )


def run_modality_matrix_step(
    input_path: Path,
    output_path: Path,
) -> PipelineStepResult:
    """
    Run the GDC project modality matrix step.
    """
    start = time.time()

    df = build_gdc_project_modality_matrix(
        input_path=input_path,
        output_path=output_path,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="project_modality_matrix",
        status="completed",
        output_path=output_path,
        row_count=dataframe_row_count(df),
        elapsed_seconds=elapsed,
    )


def run_priority_ranking_step(
    project_inventory_path: Path,
    modality_matrix_path: Path,
    output_path: Path,
) -> PipelineStepResult:
    """
    Run the GDC project priority ranking step.
    """
    start = time.time()

    df = build_gdc_project_priority_ranking(
        project_inventory_path=project_inventory_path,
        modality_matrix_path=modality_matrix_path,
        output_path=output_path,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="project_priority_ranking",
        status="completed",
        output_path=output_path,
        row_count=dataframe_row_count(df),
        elapsed_seconds=elapsed,
    )


def run_visuals_step(
    priority_ranking_path: Path,
    modality_matrix_path: Path,
    file_counts_path: Path,
    figures_dir: Path,
    top_n: int,
) -> PipelineStepResult:
    """
    Run the GDC visual generation step.
    """
    start = time.time()

    outputs = generate_gdc_priority_visuals(
        priority_ranking_path=priority_ranking_path,
        modality_matrix_path=modality_matrix_path,
        file_counts_path=file_counts_path,
        figures_dir=figures_dir,
        top_n=top_n,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="priority_visuals",
        status="completed",
        output_path=figures_dir,
        row_count=len(outputs),
        elapsed_seconds=elapsed,
    )


def run_report_step(
    project_inventory_path: Path,
    modality_matrix_path: Path,
    priority_ranking_path: Path,
    figures_dir: Path,
    output_path: Path,
    embed_images: bool,
) -> PipelineStepResult:
    """
    Run the GDC HTML report generation step.
    """
    start = time.time()

    html_report = generate_gdc_priority_report(
        project_inventory_path=project_inventory_path,
        modality_matrix_path=modality_matrix_path,
        priority_ranking_path=priority_ranking_path,
        figures_dir=figures_dir,
        output_path=output_path,
        embed_images=embed_images,
    )

    elapsed = time.time() - start

    return make_result(
        step_name="priority_html_report",
        status="completed",
        output_path=output_path,
        row_count=len(html_report),
        elapsed_seconds=elapsed,
    )


def skipped_existing_result(
    step_name: str,
    output_path: Path,
) -> PipelineStepResult:
    """
    Record a skipped step that reuses an existing file.
    """
    return make_result(
        step_name=step_name,
        status="skipped_existing",
        output_path=output_path,
        row_count=count_tsv_rows(output_path),
        elapsed_seconds=0.0,
    )


def skipped_result(
    step_name: str,
    output_path: Path,
) -> PipelineStepResult:
    """
    Record a skipped step.
    """
    return make_result(
        step_name=step_name,
        status="skipped",
        output_path=output_path,
        row_count=None,
        elapsed_seconds=0.0,
    )


def run_gdc_metadata_pipeline(
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    file_counts_path: Path = DEFAULT_FILE_COUNTS,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    priority_ranking_path: Path = DEFAULT_PRIORITY_RANKING,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    report_path: Path = DEFAULT_REPORT_OUTPUT,
    summary_path: Path = DEFAULT_SUMMARY_OUTPUT,
    project_limit: Optional[int] = None,
    project_inventory_size: int = 1000,
    file_page_size: int = 2000,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
    top_n: int = 30,
    skip_project_inventory: bool = False,
    skip_file_counts: bool = False,
    skip_visuals: bool = False,
    skip_report: bool = False,
    report_only: bool = False,
    link_images: bool = False,
    open_report: bool = False,
) -> List[PipelineStepResult]:
    """
    Run the full or partial GDC metadata pipeline.
    """
    results: List[PipelineStepResult] = []

    if report_only:
        skip_project_inventory = True
        skip_file_counts = True
        skip_visuals = False
        skip_report = False

    if not skip_project_inventory:
        print("\n[1/6] Building GDC project inventory...")
        results.append(
            run_project_inventory_step(
                output_path=project_inventory_path,
                size=project_inventory_size,
                timeout=timeout,
            )
        )
    else:
        ensure_required_file(project_inventory_path, "project inventory")
        results.append(
            skipped_existing_result(
                step_name="project_inventory",
                output_path=project_inventory_path,
            )
        )

    if not skip_file_counts:
        print("\n[2/6] Building GDC file counts by project...")
        results.append(
            run_file_counts_step(
                output_path=file_counts_path,
                project_inventory_path=project_inventory_path,
                project_limit=project_limit,
                page_size=file_page_size,
                timeout=timeout,
                sleep_seconds=sleep_seconds,
            )
        )
    else:
        ensure_required_file(file_counts_path, "file counts")
        results.append(
            skipped_existing_result(
                step_name="file_counts_by_project",
                output_path=file_counts_path,
            )
        )

    print("\n[3/6] Building GDC project modality matrix...")
    results.append(
        run_modality_matrix_step(
            input_path=file_counts_path,
            output_path=modality_matrix_path,
        )
    )

    print("\n[4/6] Building GDC project priority ranking...")
    results.append(
        run_priority_ranking_step(
            project_inventory_path=project_inventory_path,
            modality_matrix_path=modality_matrix_path,
            output_path=priority_ranking_path,
        )
    )

    if not skip_visuals:
        print("\n[5/6] Generating GDC priority visuals...")
        results.append(
            run_visuals_step(
                priority_ranking_path=priority_ranking_path,
                modality_matrix_path=modality_matrix_path,
                file_counts_path=file_counts_path,
                figures_dir=figures_dir,
                top_n=top_n,
            )
        )
    else:
        results.append(
            skipped_result(
                step_name="priority_visuals",
                output_path=figures_dir,
            )
        )

    if not skip_report:
        print("\n[6/6] Generating GDC priority HTML report...")
        results.append(
            run_report_step(
                project_inventory_path=project_inventory_path,
                modality_matrix_path=modality_matrix_path,
                priority_ranking_path=priority_ranking_path,
                figures_dir=figures_dir,
                output_path=report_path,
                embed_images=not link_images,
            )
        )
    else:
        results.append(
            skipped_result(
                step_name="priority_html_report",
                output_path=report_path,
            )
        )

    write_pipeline_summary(
        results=results,
        output_path=summary_path,
    )

    print_pipeline_summary(results)

    print(f"\nPipeline summary written to: {summary_path}")

    if open_report and report_path.exists():
        webbrowser.open(report_path.resolve().as_uri())

    return results


def apply_dev_output_paths(args: argparse.Namespace) -> argparse.Namespace:
    """
    Redirect all generated outputs to outputs/dev/.

    This protects full official outputs from accidental overwrite during
    project-limited development runs.
    """
    dev_dir = Path("outputs/dev")

    args.project_inventory = dev_dir / "gdc_project_inventory.tsv"
    args.file_counts = dev_dir / "gdc_file_counts_by_project.tsv"
    args.modality_matrix = dev_dir / "gdc_project_modality_matrix.tsv"
    args.priority_ranking = dev_dir / "gdc_project_priority_ranking.tsv"
    args.figures_dir = dev_dir / "figures"
    args.report = dev_dir / "gdc_project_priority_report.html"
    args.summary = dev_dir / "gdc_metadata_pipeline_summary.tsv"

    return args


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run the OpenMultiOmics GDC metadata pipeline end-to-end."
    )

    parser.add_argument(
        "--project-inventory",
        type=Path,
        default=DEFAULT_PROJECT_INVENTORY,
        help=f"Output/input project inventory TSV. Default: {DEFAULT_PROJECT_INVENTORY}",
    )

    parser.add_argument(
        "--file-counts",
        type=Path,
        default=DEFAULT_FILE_COUNTS,
        help=f"Output/input file-count TSV. Default: {DEFAULT_FILE_COUNTS}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX,
        help=f"Output modality matrix TSV. Default: {DEFAULT_MODALITY_MATRIX}",
    )

    parser.add_argument(
        "--priority-ranking",
        type=Path,
        default=DEFAULT_PRIORITY_RANKING,
        help=f"Output priority ranking TSV. Default: {DEFAULT_PRIORITY_RANKING}",
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=DEFAULT_FIGURES_DIR,
        help=f"Output figures directory. Default: {DEFAULT_FIGURES_DIR}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help=f"Output HTML report. Default: {DEFAULT_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Output pipeline summary TSV. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--project-limit",
        type=int,
        default=None,
        help="Optional limit on number of projects for file-count step.",
    )

    parser.add_argument(
        "--project-inventory-size",
        type=int,
        default=1000,
        help="Maximum number of GDC projects to request.",
    )

    parser.add_argument(
        "--file-page-size",
        type=int,
        default=2000,
        help="GDC files API page size.",
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
        help="Optional sleep between GDC API requests.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Top N projects for visual heatmaps.",
    )

    parser.add_argument(
        "--skip-project-inventory",
        action="store_true",
        help="Reuse existing project inventory.",
    )

    parser.add_argument(
        "--skip-file-counts",
        action="store_true",
        help="Reuse existing file counts.",
    )

    parser.add_argument(
        "--skip-visuals",
        action="store_true",
        help="Skip visual generation.",
    )

    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip HTML report generation.",
    )

    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Reuse existing data tables and regenerate visuals/report.",
    )

    parser.add_argument(
        "--link-images",
        action="store_true",
        help="Link images in HTML instead of embedding base64 images.",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open HTML report after generation.",
    )

    parser.add_argument(
        "--dev-output",
        action="store_true",
        help=(
            "Write all generated outputs to outputs/dev/ instead of official "
            "output locations. Recommended for --project-limit test runs."
        ),
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.dev_output:
        args = apply_dev_output_paths(args)

    try:
        run_gdc_metadata_pipeline(
            project_inventory_path=args.project_inventory,
            file_counts_path=args.file_counts,
            modality_matrix_path=args.modality_matrix,
            priority_ranking_path=args.priority_ranking,
            figures_dir=args.figures_dir,
            report_path=args.report,
            summary_path=args.summary,
            project_limit=args.project_limit,
            project_inventory_size=args.project_inventory_size,
            file_page_size=args.file_page_size,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
            top_n=args.top_n,
            skip_project_inventory=args.skip_project_inventory,
            skip_file_counts=args.skip_file_counts,
            skip_visuals=args.skip_visuals,
            skip_report=args.skip_report,
            report_only=args.report_only,
            link_images=args.link_images,
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: GDC metadata pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("\nGDC metadata pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())