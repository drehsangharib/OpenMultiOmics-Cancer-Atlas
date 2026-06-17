#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
import webbrowser

from core.atlas.build_cross_atlas_comparison import (
    DEFAULT_BUILD_SUMMARY,
    DEFAULT_QC_SUMMARY,
    DEFAULT_ATLAS_ROOT,
    DEFAULT_SUMMARY_OUTPUT,
    DEFAULT_SOURCE_MATRIX_OUTPUT,
    DEFAULT_MODALITY_MATRIX_OUTPUT,
    DEFAULT_QC_METRICS_OUTPUT,
    DEFAULT_ROWS_BAR,
    DEFAULT_UNKNOWN_BAR,
    DEFAULT_MISSING_URL_BAR,
    DEFAULT_SOURCE_STACKED_BAR,
    DEFAULT_MODALITY_HEATMAP,
    DEFAULT_REPORT,
    generate_cross_atlas_comparison,
)
from core.atlas.run_full_keyword_public_omics_batch import (
    run_full_keyword_public_omics_batch,
)


def run_cross_atlas_comparison_pipeline(
    atlas_names=None,
    rerun_full_batch=False,
    config_dir=Path("configs/atlas_definitions"),
    build_summary_path=DEFAULT_BUILD_SUMMARY,
    qc_summary_path=DEFAULT_QC_SUMMARY,
    atlas_root=DEFAULT_ATLAS_ROOT,
    summary_output_path=DEFAULT_SUMMARY_OUTPUT,
    source_matrix_output_path=DEFAULT_SOURCE_MATRIX_OUTPUT,
    modality_matrix_output_path=DEFAULT_MODALITY_MATRIX_OUTPUT,
    qc_metrics_output_path=DEFAULT_QC_METRICS_OUTPUT,
    rows_bar_path=DEFAULT_ROWS_BAR,
    unknown_bar_path=DEFAULT_UNKNOWN_BAR,
    missing_url_bar_path=DEFAULT_MISSING_URL_BAR,
    source_stacked_bar_path=DEFAULT_SOURCE_STACKED_BAR,
    modality_heatmap_path=DEFAULT_MODALITY_HEATMAP,
    output_html_path=DEFAULT_REPORT,
    title="Cross-Atlas Comparison Report",
    open_report=False,
):
    if rerun_full_batch:
        run_full_keyword_public_omics_batch(
            config_dir=config_dir,
            atlas_names=atlas_names,
            build_summary_output_path=build_summary_path,
            qc_summary_output_path=qc_summary_path,
            open_reports=False,
        )

    summary_df, report_html = generate_cross_atlas_comparison(
        build_summary_path=build_summary_path,
        qc_summary_path=qc_summary_path,
        atlas_root=atlas_root,
        summary_output_path=summary_output_path,
        source_matrix_output_path=source_matrix_output_path,
        modality_matrix_output_path=modality_matrix_output_path,
        qc_metrics_output_path=qc_metrics_output_path,
        rows_bar_path=rows_bar_path,
        unknown_bar_path=unknown_bar_path,
        missing_url_bar_path=missing_url_bar_path,
        source_stacked_bar_path=source_stacked_bar_path,
        modality_heatmap_path=modality_heatmap_path,
        output_html_path=output_html_path,
        atlas_names=atlas_names,
        title=title,
    )

    if open_report and Path(output_html_path).exists():
        webbrowser.open(Path(output_html_path).resolve().as_uri())

    print("Cross-atlas comparison pipeline complete.")
    print(f"Atlas count: {len(summary_df)}")
    print(f"Summary output: {summary_output_path}")
    print(f"HTML report: {output_html_path}")
    print(f"HTML characters: {len(report_html)}")

    return summary_df, report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the cross-atlas comparison and visualization pipeline."
    )

    parser.add_argument(
        "--atlases",
        nargs="*",
        default=None,
        help="Optional atlas names, e.g. gbm luad brca lgg",
    )

    parser.add_argument(
        "--rerun-full-batch",
        action="store_true",
        help="Rerun the full atlas batch pipeline before building the comparison report.",
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("configs/atlas_definitions"),
        help="Config directory for atlas definitions when rerunning the full batch pipeline.",
    )

    parser.add_argument(
        "--build-summary",
        type=Path,
        default=DEFAULT_BUILD_SUMMARY,
        help=f"Atlas batch summary TSV. Default: {DEFAULT_BUILD_SUMMARY}",
    )

    parser.add_argument(
        "--qc-summary",
        type=Path,
        default=DEFAULT_QC_SUMMARY,
        help=f"Atlas QC batch summary TSV. Default: {DEFAULT_QC_SUMMARY}",
    )

    parser.add_argument(
        "--atlas-root",
        type=Path,
        default=DEFAULT_ATLAS_ROOT,
        help=f"Atlas inventory root directory. Default: {DEFAULT_ATLAS_ROOT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Cross-atlas comparison TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--source-matrix",
        type=Path,
        default=DEFAULT_SOURCE_MATRIX_OUTPUT,
        help=f"Cross-atlas source matrix TSV output. Default: {DEFAULT_SOURCE_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX_OUTPUT,
        help=f"Cross-atlas modality matrix TSV output. Default: {DEFAULT_MODALITY_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--qc-metrics",
        type=Path,
        default=DEFAULT_QC_METRICS_OUTPUT,
        help=f"Cross-atlas QC metrics TSV output. Default: {DEFAULT_QC_METRICS_OUTPUT}",
    )

    parser.add_argument(
        "--rows-bar",
        type=Path,
        default=DEFAULT_ROWS_BAR,
        help=f"Rows-by-atlas chart PNG output. Default: {DEFAULT_ROWS_BAR}",
    )

    parser.add_argument(
        "--unknown-bar",
        type=Path,
        default=DEFAULT_UNKNOWN_BAR,
        help=f"Unknown-modality chart PNG output. Default: {DEFAULT_UNKNOWN_BAR}",
    )

    parser.add_argument(
        "--missing-url-bar",
        type=Path,
        default=DEFAULT_MISSING_URL_BAR,
        help=f"Missing-source-URL chart PNG output. Default: {DEFAULT_MISSING_URL_BAR}",
    )

    parser.add_argument(
        "--source-stacked-bar",
        type=Path,
        default=DEFAULT_SOURCE_STACKED_BAR,
        help=f"Source stacked-bar PNG output. Default: {DEFAULT_SOURCE_STACKED_BAR}",
    )

    parser.add_argument(
        "--modality-heatmap",
        type=Path,
        default=DEFAULT_MODALITY_HEATMAP,
        help=f"Modality heatmap PNG output. Default: {DEFAULT_MODALITY_HEATMAP}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Cross-atlas HTML report output. Default: {DEFAULT_REPORT}",
    )

    parser.add_argument(
        "--title",
        default="Cross-Atlas Comparison Report",
        help="HTML report title.",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open the generated HTML report after pipeline completion.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_cross_atlas_comparison_pipeline(
            atlas_names=args.atlases,
            rerun_full_batch=args.rerun_full_batch,
            config_dir=args.config_dir,
            build_summary_path=args.build_summary,
            qc_summary_path=args.qc_summary,
            atlas_root=args.atlas_root,
            summary_output_path=args.output,
            source_matrix_output_path=args.source_matrix,
            modality_matrix_output_path=args.modality_matrix,
            qc_metrics_output_path=args.qc_metrics,
            rows_bar_path=args.rows_bar,
            unknown_bar_path=args.unknown_bar,
            missing_url_bar_path=args.missing_url_bar,
            source_stacked_bar_path=args.source_stacked_bar,
            modality_heatmap_path=args.modality_heatmap,
            output_html_path=args.report,
            title=args.title,
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: Failed to run cross-atlas comparison pipeline: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())