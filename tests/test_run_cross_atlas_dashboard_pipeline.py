from pathlib import Path

import pandas as pd

from core.atlas.run_cross_atlas_dashboard_pipeline import (
    build_arg_parser,
    run_cross_atlas_dashboard_pipeline,
)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--atlases",
            "gbm",
            "luad",
            "--rerun-full-batch",
            "--open-report",
        ]
    )

    assert args.atlases == ["gbm", "luad"]
    assert args.rerun_full_batch is True
    assert args.open_report is True


def test_run_cross_atlas_dashboard_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    summary_output = tmp_path / "cross_atlas_dashboard_summary.tsv"
    source_matrix_output = tmp_path / "cross_atlas_dashboard_source_matrix.tsv"
    modality_matrix_output = tmp_path / "cross_atlas_dashboard_modality_matrix.tsv"
    qc_metrics_output = tmp_path / "cross_atlas_dashboard_qc_metrics.tsv"
    rankings_output = tmp_path / "cross_atlas_rankings.tsv"
    rows_bar = tmp_path / "cross_atlas_rows_bar.png"
    unknown_bar = tmp_path / "cross_atlas_unknown_modality_bar.png"
    missing_url_bar = tmp_path / "cross_atlas_missing_url_bar.png"
    source_stacked_bar = tmp_path / "cross_atlas_source_stacked_bar.png"
    modality_heatmap = tmp_path / "cross_atlas_modality_heatmap.png"
    rankings_bar = tmp_path / "cross_atlas_rankings_bar.png"
    report_html_path = tmp_path / "cross_atlas_dashboard.html"

    def fake_run_full_keyword_public_omics_batch(
        config_dir,
        atlas_names=None,
        build_summary_output_path=None,
        qc_summary_output_path=None,
        open_reports=False,
    ):
        return (
            pd.DataFrame([{"atlas_name": "gbm"}, {"atlas_name": "luad"}]),
            pd.DataFrame([{"atlas_name": "gbm"}, {"atlas_name": "luad"}]),
        )

    def fake_generate_cross_atlas_dashboard(
        display_registry_path,
        build_summary_path,
        qc_summary_path,
        atlas_root,
        summary_output_path,
        source_matrix_output_path,
        modality_matrix_output_path,
        qc_metrics_output_path,
        rankings_output_path,
        rows_bar_path,
        unknown_bar_path,
        missing_url_bar_path,
        source_stacked_bar_path,
        modality_heatmap_path,
        rankings_bar_path,
        output_html_path,
        atlas_names=None,
        title="Cross-Atlas Intelligence Dashboard",
    ):
        summary_df = pd.DataFrame(
            [
                {"atlas_name": "gbm", "rows": 95},
                {"atlas_name": "luad", "rows": 68},
            ]
        )
        rankings_df = pd.DataFrame(
            [
                {"atlas_name": "gbm", "overall_rank": 1},
                {"atlas_name": "luad", "overall_rank": 2},
            ]
        )

        summary_output_path.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(summary_output_path, sep="\t", index=False)
        pd.DataFrame([{"atlas_name": "gbm"}]).to_csv(source_matrix_output_path, sep="\t", index=False)
        pd.DataFrame([{"atlas_name": "gbm"}]).to_csv(modality_matrix_output_path, sep="\t", index=False)
        pd.DataFrame([{"atlas_name": "gbm"}]).to_csv(qc_metrics_output_path, sep="\t", index=False)
        rankings_df.to_csv(rankings_output_path, sep="\t", index=False)

        for path in [rows_bar_path, unknown_bar_path, missing_url_bar_path, source_stacked_bar_path, modality_heatmap_path, rankings_bar_path]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fakepng")

        output_html_path.parent.mkdir(parents=True, exist_ok=True)
        output_html_path.write_text("<html>Cross-Atlas Intelligence Dashboard</html>", encoding="utf-8")

        return summary_df, rankings_df, "<html>Cross-Atlas Intelligence Dashboard</html>"

    monkeypatch.setattr(
        "core.atlas.run_cross_atlas_dashboard_pipeline.run_full_keyword_public_omics_batch",
        fake_run_full_keyword_public_omics_batch,
    )
    monkeypatch.setattr(
        "core.atlas.run_cross_atlas_dashboard_pipeline.generate_cross_atlas_dashboard",
        fake_generate_cross_atlas_dashboard,
    )

    summary_df, rankings_df, report_html = run_cross_atlas_dashboard_pipeline(
        atlas_names=["gbm", "luad"],
        rerun_full_batch=True,
        summary_output_path=summary_output,
        source_matrix_output_path=source_matrix_output,
        modality_matrix_output_path=modality_matrix_output,
        qc_metrics_output_path=qc_metrics_output,
        rankings_output_path=rankings_output,
        rows_bar_path=rows_bar,
        unknown_bar_path=unknown_bar,
        missing_url_bar_path=missing_url_bar,
        source_stacked_bar_path=source_stacked_bar,
        modality_heatmap_path=modality_heatmap,
        rankings_bar_path=rankings_bar,
        output_html_path=report_html_path,
        open_report=False,
    )

    assert summary_output.exists()
    assert source_matrix_output.exists()
    assert modality_matrix_output.exists()
    assert qc_metrics_output.exists()
    assert rankings_output.exists()
    assert rows_bar.exists()
    assert unknown_bar.exists()
    assert missing_url_bar.exists()
    assert source_stacked_bar.exists()
    assert modality_heatmap.exists()
    assert rankings_bar.exists()
    assert report_html_path.exists()

    assert summary_df.shape[0] == 2
    assert rankings_df.shape[0] == 2
    assert "Cross-Atlas Intelligence Dashboard" in report_html
