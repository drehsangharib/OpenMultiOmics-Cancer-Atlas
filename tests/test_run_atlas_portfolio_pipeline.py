from pathlib import Path

import pandas as pd

from core.atlas.run_atlas_portfolio_pipeline import (
    build_arg_parser,
    run_atlas_portfolio_pipeline,
)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--atlases",
            "gbm",
            "luad",
            "--rerun-dashboard",
            "--rerun-full-batch",
            "--open-report",
        ]
    )

    assert args.atlases == ["gbm", "luad"]
    assert args.rerun_dashboard is True
    assert args.rerun_full_batch is True
    assert args.open_report is True


def test_run_atlas_portfolio_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    bundle_dir = tmp_path / "atlas_portfolio_bundle"
    zip_output = tmp_path / "atlas_portfolio_bundle.zip"

    def fake_run_cross_atlas_dashboard_pipeline(
        atlas_names=None,
        rerun_full_batch=False,
        config_dir=None,
        display_registry_path=None,
        open_report=False,
        **kwargs,
    ):
        return (
            pd.DataFrame([{"atlas_name": "gbm"}, {"atlas_name": "luad"}]),
            pd.DataFrame([{"atlas_name": "gbm"}, {"atlas_name": "luad"}]),
            "<html>Dashboard</html>",
        )

    def fake_generate_atlas_portfolio_bundle(
        display_registry_path,
        dashboard_summary_path,
        rankings_path,
        dashboard_html_path,
        reports_dir,
        bundle_dir,
        zip_output_path,
        atlas_names=None,
    ):
        bundle_dir.mkdir(parents=True, exist_ok=True)
        index_html_path = bundle_dir / "index.html"
        index_html_path.write_text("<html>Atlas Portfolio Bundle</html>", encoding="utf-8")
        zip_output_path.parent.mkdir(parents=True, exist_ok=True)
        zip_output_path.write_bytes(b"fakezip")

        benchmark_df = pd.DataFrame(
            [
                {"atlas_name": "gbm"},
                {"atlas_name": "luad"},
            ]
        )
        return benchmark_df, index_html_path, zip_output_path

    monkeypatch.setattr(
        "core.atlas.run_atlas_portfolio_pipeline.run_cross_atlas_dashboard_pipeline",
        fake_run_cross_atlas_dashboard_pipeline,
    )
    monkeypatch.setattr(
        "core.atlas.run_atlas_portfolio_pipeline.generate_atlas_portfolio_bundle",
        fake_generate_atlas_portfolio_bundle,
    )

    benchmark_df, index_html_path, zip_path = run_atlas_portfolio_pipeline(
        atlas_names=["gbm", "luad"],
        rerun_dashboard=True,
        rerun_full_batch=True,
        bundle_dir=bundle_dir,
        zip_output_path=zip_output,
        open_report=False,
    )

    assert benchmark_df.shape[0] == 2
    assert index_html_path.exists()
    assert zip_path.exists()