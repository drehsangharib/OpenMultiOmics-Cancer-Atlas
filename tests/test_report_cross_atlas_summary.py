from pathlib import Path

import pandas as pd

from core.atlas.report_cross_atlas_summary import (
    build_arg_parser,
    generate_cross_atlas_summary,
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


def test_generate_cross_atlas_summary(tmp_path: Path):
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
    output_tsv = reports_root / "cross_atlas_summary.tsv"
    output_html = reports_root / "cross_atlas_summary_report.html"

    build_summary = pd.DataFrame(
        [
            {"atlas_name": "gbm"},
            {"atlas_name": "luad"},
        ]
    )
    build_summary.to_csv(build_summary_path, sep="\t", index=False)

    qc_summary = pd.DataFrame(
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
    )
    qc_summary.to_csv(qc_summary_path, sep="\t", index=False)

    summary_df, report_html = generate_cross_atlas_summary(
        build_summary_path=build_summary_path,
        qc_summary_path=qc_summary_path,
        atlas_root=atlas_root,
        output_tsv_path=output_tsv,
        output_html_path=output_html,
        atlas_names=["gbm", "luad"],
    )

    assert output_tsv.exists()
    assert output_html.exists()
    assert summary_df.shape[0] == 2
    assert set(summary_df["atlas_name"]) == {"gbm", "luad"}
    assert "Cross-Atlas Summary Report" in report_html
    assert "gbm" in output_tsv.read_text(encoding="utf-8")
    assert "luad" in output_tsv.read_text(encoding="utf-8")