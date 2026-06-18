#!/usr/bin/env python3

import argparse
import sys
import webbrowser
from pathlib import Path

from core.atlas.build_atlas_portfolio_bundle import (
    DEFAULT_BUNDLE_DIR,
    DEFAULT_DASHBOARD_HTML,
    DEFAULT_DASHBOARD_SUMMARY,
    DEFAULT_DISPLAY_REGISTRY,
    DEFAULT_RANKINGS,
    DEFAULT_REPORTS_DIR,
    DEFAULT_ZIP_OUTPUT,
    generate_atlas_portfolio_bundle,
)
from core.atlas.run_cross_atlas_dashboard_pipeline import (
    run_cross_atlas_dashboard_pipeline,
)


def run_atlas_portfolio_pipeline(
    atlas_names=None,
    rerun_dashboard=False,
    rerun_full_batch=False,
    config_dir=Path("configs/atlas_definitions"),
    display_registry_path=DEFAULT_DISPLAY_REGISTRY,
    dashboard_summary_path=DEFAULT_DASHBOARD_SUMMARY,
    rankings_path=DEFAULT_RANKINGS,
    dashboard_html_path=DEFAULT_DASHBOARD_HTML,
    reports_dir=DEFAULT_REPORTS_DIR,
    bundle_dir=DEFAULT_BUNDLE_DIR,
    zip_output_path=DEFAULT_ZIP_OUTPUT,
    open_report=False,
):
    if rerun_dashboard:
        run_cross_atlas_dashboard_pipeline(
            atlas_names=atlas_names,
            rerun_full_batch=rerun_full_batch,
            config_dir=config_dir,
            display_registry_path=display_registry_path,
            open_report=False,
        )

    benchmark_df, index_html_path, zip_output_path = generate_atlas_portfolio_bundle(
        display_registry_path=display_registry_path,
        dashboard_summary_path=dashboard_summary_path,
        rankings_path=rankings_path,
        dashboard_html_path=dashboard_html_path,
        reports_dir=reports_dir,
        bundle_dir=bundle_dir,
        zip_output_path=zip_output_path,
        atlas_names=atlas_names,
    )

    if open_report and Path(index_html_path).exists():
        webbrowser.open(Path(index_html_path).resolve().as_uri())

    print("Atlas portfolio pipeline complete.")
    print(f"Atlas count: {len(benchmark_df)}")
    print(f"Bundle index: {index_html_path}")
    print(f"Zip bundle: {zip_output_path}")

    return benchmark_df, index_html_path, zip_output_path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the atlas portfolio bundle pipeline."
    )

    parser.add_argument(
        "--atlases",
        nargs="*",
        default=None,
        help="Optional atlas names, e.g. gbm luad brca lgg",
    )

    parser.add_argument(
        "--rerun-dashboard",
        action="store_true",
        help="Rerun the cross-atlas dashboard pipeline before bundling.",
    )

    parser.add_argument(
        "--rerun-full-batch",
        action="store_true",
        help="If rerunning the dashboard, also rerun the full atlas batch pipeline first.",
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("configs/atlas_definitions"),
        help="Config directory for atlas definitions when rerunning the dashboard pipeline.",
    )

    parser.add_argument(
        "--display-registry",
        type=Path,
        default=DEFAULT_DISPLAY_REGISTRY,
        help=f"Atlas display registry YAML. Default: {DEFAULT_DISPLAY_REGISTRY}",
    )

    parser.add_argument(
        "--dashboard-summary",
        type=Path,
        default=DEFAULT_DASHBOARD_SUMMARY,
        help=f"Dashboard summary TSV. Default: {DEFAULT_DASHBOARD_SUMMARY}",
    )

    parser.add_argument(
        "--rankings",
        type=Path,
        default=DEFAULT_RANKINGS,
        help=f"Dashboard rankings TSV. Default: {DEFAULT_RANKINGS}",
    )

    parser.add_argument(
        "--dashboard-html",
        type=Path,
        default=DEFAULT_DASHBOARD_HTML,
        help=f"Dashboard HTML input. Default: {DEFAULT_DASHBOARD_HTML}",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help=f"Reports directory. Default: {DEFAULT_REPORTS_DIR}",
    )

    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=DEFAULT_BUNDLE_DIR,
        help=f"Bundle directory output. Default: {DEFAULT_BUNDLE_DIR}",
    )

    parser.add_argument(
        "--zip-output",
        type=Path,
        default=DEFAULT_ZIP_OUTPUT,
        help=f"Zip output path. Default: {DEFAULT_ZIP_OUTPUT}",
    )

    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open the portfolio bundle index page after completion.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_atlas_portfolio_pipeline(
            atlas_names=args.atlases,
            rerun_dashboard=args.rerun_dashboard,
            rerun_full_batch=args.rerun_full_batch,
            config_dir=args.config_dir,
            display_registry_path=args.display_registry,
            dashboard_summary_path=args.dashboard_summary,
            rankings_path=args.rankings,
            dashboard_html_path=args.dashboard_html,
            reports_dir=args.reports_dir,
            bundle_dir=args.bundle_dir,
            zip_output_path=args.zip_output,
            open_report=args.open_report,
        )
    except Exception as exc:
        print(f"ERROR: Failed to run atlas portfolio pipeline: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())