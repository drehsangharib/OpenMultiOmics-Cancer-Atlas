from pathlib import Path

import pandas as pd

from core.atlas.build_cross_atlas_comparison import (
    build_arg_parser,
    generate_cross_atlas_comparison,
    resolve_atlas_names,
)


def write_inventory(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(path, sep="\t", index=False)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--atlases", "gbm", "luad"])

    assert args.atlases == ["gbm", "luad"]


def test_resolve_atlas_names_from_build_summary(tmp_path: Path):
    build_summary = pd.DataFrame(
        [
            {"atlas_name": "gbm"},
            {"atlas_name": "luad"},
        ]
    )

    atlas_names = resolve_atlas_names(build_summary, tmp_path, atlas_names=None)

    assert atlas_names == ["gbm", "luad"]


def test_generate_cross_atlas_comparison(tmp_path: Path):
    atlas_root = tmp_path / "atlases"
    reports_root = tmp_path / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    write_inventory(
        atlas_root / "gbm" / "gbm_public_omics_atlas_inventory.tsv",
        [
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-GBM.star_tpm.tsv",
                "record_name": "TCGA GBM STAR TPM",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "source_url": "https://gdc.xenahubs.net/",
                "atlas_match_terms": "gbm;glioma",
            },
            {
                "source_id": "gdc",
                "source_record_type": "gdc_project",
                "record_id": "TCGA-GBM",
                "record_name": "TCGA-GBM",
                "omics_modality": "clinical_annotation;snv;transcriptomics",
                "data_category": "GDC project metadata",
                "source_url": "https://portal.gdc.cancer.gov/projects/TCGA-GBM",
                "atlas_match_terms": "gbm;tcga-gbm",
            },
        ],
    )

    write_inventory(
        atlas_root / "luad" / "luad_public_omics_atlas_inventory.tsv",
        [
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-LUAD.star_tpm.tsv",
                "record_name": "TCGA LUAD STAR TPM",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "source_url": "https://gdc.xenahubs.net/",
                "atlas_match_terms": "luad;tcga-luad",
            },
        ],
    )

    build_summary_path = reports_root / "atlas_batch_summary.tsv"
    qc_summary_path = reports_root / "atlas_qc_batch_summary.tsv"

    pd.DataFrame([{"atlas_name": "gbm"}, {"atlas_name": "luad"}]).to_csv(
        build_summary_path, sep="\t", index=False
    )

    pd.DataFrame(
        [
            {
                "atlas_name": "gbm",
                "qc_html_characters": 9152,
                "qc_report_path": "outputs/reports/gbm_public_omics_atlas_qc_report.html",
            },
            {
                "atlas_name": "luad",
                "qc_html_characters": 7398,
                "qc_report_path": "outputs/reports/luad_public_omics_atlas_qc_report.html",
            },
        ]
    ).to_csv(qc_summary_path, sep="\t", index=False)

    summary_output = reports_root / "cross_atlas_comparison.tsv"
    source_matrix_output = reports_root / "cross_atlas_source_matrix.tsv"
    modality_matrix_output = reports_root / "cross_atlas_modality_matrix.tsv"
    qc_metrics_output = reports_root / "cross_atlas_qc_metrics.tsv"
    rows_bar = reports_root / "cross_atlas_rows_bar.png"
    unknown_bar = reports_root / "cross_atlas_unknown_modality_bar.png"
    missing_url_bar = reports_root / "cross_atlas_missing_url_bar.png"
    source_stacked_bar = reports_root / "cross_atlas_source_stacked_bar.png"
    modality_heatmap = reports_root / "cross_atlas_modality_heatmap.png"
    report_html_path = reports_root / "cross_atlas_comparison_report.html"

    summary_df, report_html = generate_cross_atlas_comparison(
        build_summary_path=build_summary_path,
        qc_summary_path=qc_summary_path,
        atlas_root=atlas_root,
        summary_output_path=summary_output,
        source_matrix_output_path=source_matrix_output,
        modality_matrix_output_path=modality_matrix_output,
        qc_metrics_output_path=qc_metrics_output,
        rows_bar_path=rows_bar,
        unknown_bar_path=unknown_bar,
        missing_url_bar_path=missing_url_bar,
        source_stacked_bar_path=source_stacked_bar,
        modality_heatmap_path=modality_heatmap,
        output_html_path=report_html_path,
        atlas_names=["gbm", "luad"],
    )

    assert summary_output.exists()
    assert source_matrix_output.exists()
    assert modality_matrix_output.exists()
    assert qc_metrics_output.exists()
    assert rows_bar.exists()
    assert unknown_bar.exists()
    assert missing_url_bar.exists()
    assert source_stacked_bar.exists()
    assert modality_heatmap.exists()
    assert report_html_path.exists()

    assert summary_df.shape[0] == 2
    assert set(summary_df["atlas_name"]) == {"gbm", "luad"}
    assert "Cross-Atlas Comparison Report" in report_html