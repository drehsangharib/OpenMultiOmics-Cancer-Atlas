#!/usr/bin/env python3#!/import argparse
import sys
import webbrowser
from pathlib import Path
import argparse

from atlases.gbm.build_gbm_public_omics_atlas import (
    DEFAULT_OUTPUT as DEFAULT_GBM_OUTPUT,
    DEFAULT_REPORT as DEFAULT_GBM_REPORT,
    build_gbm_public_omics_atlas,
)
from atlases.gbm.report_gbm_public_omics_atlas_qc import (
    DEFAULT_OUTPUT as DEFAULT_GBM_QC_REPORT,
    generate_gbm_public_omics_atlas_qc_report,
)
from core.integration.unified_public_cancer_omics_inventory import (
    DEFAULT_OUTPUT as DEFAULT_UNIFIED_OUTPUT,
)
from core.pipelines.run_unified_public_omics_qc_pipeline import (
    DEFAULT_QC_REPORT_OUTPUT as DEFAULT_UNIFIED_QC_REPORT,
    DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT,
    DEFAULT_UNIFIED_REPORT_OUTPUT,
    run_unified_public_omics_qc_pipeline,
)


def run_gbm_public_omics_atlas_pipeline(
    unified_output_path=DEFAULT_UNIFIED_OUTPUT,
    unified_summary_path=DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT,
    unified_report_path=DEFAULT_UNIFIED_REPORT_OUTPUT,
    unified_qc_report_path=DEFAULT_UNIFIED_QC_REPORT,
    gbm_output_path=DEFAULT_GBM_OUTPUT,
    gbm_report_path=DEFAULT_GBM_REPORT,
    gbm_qc_report_path=DEFAULT_GBM_QC_REPORT,
    refresh_xena=False,
    xena_recommended_only=False,
    xena_min_priority=None,
    xena_timeout=60,
    xena_sleep_seconds=0.0,
    xena_strict=False,
    strict_inputs=False,
    make_report=True,
    make_qc_report=True,
    open_report=False,
):
    unified_df, unified_summary_df, unified_qc_html = run_unified_public_omics_qc_pipeline(
        unified_output_path=unified_output_path,
        summary_output_path=unified_summary_path,
        report_output_path=unified_report_path,
        qc_report_output_path=unified_qc_report_path,
        report_title="Unified Public Cancer Omics Inventory Report",
        qc_report_title="Unified Public Cancer Omics Inventory QC Report",
        strict_inputs=strict_inputs,
        refresh_xena=refresh_xena,
        xena_recommended_only=xena_recommended_only,
        xena_min_priority=xena_min_priority,
        xena_timeout=xena_timeout,
        xena_sleep_seconds=xena_sleep_seconds,
        xena_strict=xena_strict,
        make_report=make_report,
        make_qc_report=make_qc_report,
        open_report=False,
        open_qc_report=False,
    )

    gbm_df = build_gbm_public_omics_atlas(
        input_path=unified_output_path,
        output_path=gbm_output_path,
        report_path=gbm_report_path,
        make_report=make_report,
        report_title="GBM Public Omics Atlas Inventory Report",
    )

    gbm_qc_html = None
    if make_qc_report:
        gbm_qc_html = generate_gbm_public_omics_atlas_qc_report(
            input_path=gbm_output_path,
            output_path=gbm_qc_report_path,
            title="GBM Public Omics Atlas QC Report",
        )

    if open_report:
        if make_report and gbm_report_path.exists():
            webbrowser.open(gbm_report_path.resolve().as_uri())
        if make_qc_report and gbm_qc_report_path.exists():
            webbrowser.open(gbm_qc_report_path.resolve().as_uri())

    print("GBM public omics atlas pipeline complete.")
    print(f"Unified inventory rows: {len(unified_df)}")
    print(f"GBM atlas rows: {len(gbm_df)}")
    print(f"Unified inventory output: {unified_output_path}")
    print(f"GBM atlas output: {gbm_output_path}")

    if make_report:
        print(f"GBM atlas report: {gbm_report_path}")

    if make_qc_report:
        print(f"GBM atlas QC report: {gbm_qc_report_path}")

    return unified_df, unified_summary_df, unified_qc_html, gbm_df, gbm_qc_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the GBM public omics atlas pipeline."
    )

    parser.add_argument("--refresh-xena", action="store_true")
    parser.add_argument("--xena-recommended-only", action="store_true")
    parser.add_argument("--xena-min-priority", type=int, default=None)
    parser.add_argument("--xena-timeout", type=int, default=60)
    parser.add_argument("--xena-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--xena-strict", action="store_true")
    parser.add_argument("--strict-inputs", action="store_true")

    parser.add_argument("--make-report", action="store_true")
    parser.add_argument("--make-qc-report", action="store_true")
    parser.add_argument("--open-report", action="store_true")

    parser.add_argument("--unified-output", type=Path, default=DEFAULT_UNIFIED_OUTPUT)
    parser.add_argument("--unified-summary", type=Path, default=DEFAULT_UNIFIED_PIPELINE_SUMMARY_OUTPUT)
    parser.add_argument("--unified-report", type=Path, default=DEFAULT_UNIFIED_REPORT_OUTPUT)
    parser.add_argument("--unified-qc-report", type=Path, default=DEFAULT_UNIFIED_QC_REPORT)

    parser.add_argument("--gbm-output", type=Path, default=DEFAULT_GBM_OUTPUT)
    parser.add_argument("--gbm-report", type=Path, default=DEFAULT_GBM_REPORT)
    parser.add_argument("--gbm-qc-report", type=Path, default=DEFAULT_GBM_QC_REPORT)

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_gbm_public_omics_atlas_pipeline(
            unified_output_path=args.unified_output,
            unified_summary_path=args.unified_summary,
            unified_report_path=args.unified_report,
            unified_qc_report_path=args.unified_qc_report,
            gbm_output_path=args.gbm_output,
            gbm_report_path=args.gbm_report,
            gbm_qc_report_path=args.gbm_qc_report,
            refresh_xena=args.refresh_xena,
            xena_recommended_only=args.xena_recommended_only,
            xena_min_priority=args.xena_min_priority,
            xena_timeout=args.xena_timeout,
            xena_sleep_seconds=args.xena_sleep_seconds,
            xena_strict=args.xena_strict,
            strict_inputs=args.strict_inputs,
            make_report=args.make_report,
            make_qc_report=args.make_qc_report,
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: GBM atlas pipeline failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

