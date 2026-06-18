from pathlib import Path

import pandas as pd
import yaml

from core.atlas.build_atlas_portfolio_bundle import (
    build_arg_parser,
    generate_atlas_portfolio_bundle,
)


def write_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--atlases", "gbm", "luad"])

    assert args.atlases == ["gbm", "luad"]


def test_generate_atlas_portfolio_bundle(tmp_path: Path):
    display_registry_path = tmp_path / "atlas_display_registry.yaml"
    dashboard_summary_path = tmp_path / "cross_atlas_dashboard_summary.tsv"
    rankings_path = tmp_path / "cross_atlas_rankings.tsv"
    dashboard_html_path = tmp_path / "cross_atlas_dashboard.html"
    reports_dir = tmp_path / "reports"
    bundle_dir = tmp_path / "atlas_portfolio_bundle"
    zip_output = tmp_path / "atlas_portfolio_bundle.zip"

    write_yaml(
        display_registry_path,
        {
            "gbm": {
                "display_name": "Glioblastoma",
                "short_name": "GBM",
                "color": "#1f77b4",
                "order": 1,
            },
            "luad": {
                "display_name": "Lung Adenocarcinoma",
                "short_name": "LUAD",
                "color": "#ff7f0e",
                "order": 2,
            },
        },
    )

    reports_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "atlas_name": "gbm",
                "display_name": "Glioblastoma",
                "short_name": "GBM",
                "color": "#1f77b4",
                "order": 1,
                "rows": 95,
                "source_count": 2,
                "record_type_count": 2,
                "modality_count": 9,
                "unknown_modality_rows": 18,
                "missing_source_url_rows": 0,
                "inventory_path": "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv",
                "atlas_report_path": str(reports_dir / "gbm_public_omics_atlas_report.html"),
                "qc_html_characters": 9152,
                "qc_report_path": str(reports_dir / "gbm_public_omics_atlas_qc_report.html"),
            },
            {
                "atlas_name": "luad",
                "display_name": "Lung Adenocarcinoma",
                "short_name": "LUAD",
                "color": "#ff7f0e",
                "order": 2,
                "rows": 68,
                "source_count": 2,
                "record_type_count": 2,
                "modality_count": 10,
                "unknown_modality_rows": 10,
                "missing_source_url_rows": 0,
                "inventory_path": "outputs/atlases/luad/luad_public_omics_atlas_inventory.tsv",
                "atlas_report_path": str(reports_dir / "luad_public_omics_atlas_report.html"),
                "qc_html_characters": 7398,
                "qc_report_path": str(reports_dir / "luad_public_omics_atlas_qc_report.html"),
            },
        ]
    ).to_csv(dashboard_summary_path, sep="\t", index=False)

    pd.DataFrame(
        [
            {"atlas_name": "gbm", "overall_rank": 1, "composite_rank_score": 5},
            {"atlas_name": "luad", "overall_rank": 2, "composite_rank_score": 7},
        ]
    ).to_csv(rankings_path, sep="\t", index=False)

    dashboard_html_path.write_text("<html>Cross-Atlas Dashboard</html>", encoding="utf-8")
    (reports_dir / "gbm_public_omics_atlas_report.html").write_text("<html>gbm report</html>", encoding="utf-8")
    (reports_dir / "gbm_public_omics_atlas_qc_report.html").write_text("<html>gbm qc</html>", encoding="utf-8")
    (reports_dir / "luad_public_omics_atlas_report.html").write_text("<html>luad report</html>", encoding="utf-8")
    (reports_dir / "luad_public_omics_atlas_qc_report.html").write_text("<html>luad qc</html>", encoding="utf-8")
    (reports_dir / "cross_atlas_rankings_bar.png").write_bytes(b"fakepng")
    (reports_dir / "cross_atlas_rows_bar.png").write_bytes(b"fakepng")
    (reports_dir / "cross_atlas_source_stacked_bar.png").write_bytes(b"fakepng")
    (reports_dir / "cross_atlas_modality_heatmap.png").write_bytes(b"fakepng")

    benchmark_df, index_html_path, zip_path = generate_atlas_portfolio_bundle(
        display_registry_path=display_registry_path,
        dashboard_summary_path=dashboard_summary_path,
        rankings_path=rankings_path,
        dashboard_html_path=dashboard_html_path,
        reports_dir=reports_dir,
        bundle_dir=bundle_dir,
        zip_output_path=zip_output,
        atlas_names=["gbm", "luad"],
    )

    assert bundle_dir.exists()
    assert index_html_path.exists()
    assert zip_path.exists()
    assert benchmark_df.shape[0] == 2
    assert set(benchmark_df["atlas_name"]) == {"gbm", "luad"}