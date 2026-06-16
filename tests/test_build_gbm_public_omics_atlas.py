from pathlib import Path

import pandas as pd

from atlases.gbm.build_gbm_public_omics_atlas import (
    build_gbm_public_omics_atlas,
    build_gbm_public_omics_atlas_report_html,
    collect_match_terms,
    filter_gbm_relevant_records,
    value_counts_table,
)


def make_unified_df():
    return pd.DataFrame(
        [
            {
                "source_id": "gdc",
                "source_record_type": "gdc_project",
                "record_id": "TCGA-GBM",
                "record_name": "Glioblastoma Multiforme",
                "project_id": "TCGA-GBM",
                "dataset_id": "",
                "hub_id": "",
                "omics_modality": "clinical_annotation;snv;transcriptomics",
                "data_category": "GDC project metadata",
                "matrix_type": "project-level metadata",
                "resource_family": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "cancer_scope": "GDC project/cohort",
                "priority_for_atlas": 5,
                "source_url": "https://portal.gdc.cancer.gov/projects/TCGA-GBM",
                "notes": "GBM project",
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-GBM.star_tpm.tsv",
                "record_name": "TCGA GBM STAR TPM",
                "project_id": "",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
                "hub_id": "gdc_xena",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "primary_site": "",
                "disease_type": "",
                "cancer_scope": "TCGA cancer cohorts",
                "priority_for_atlas": 5,
                "source_url": "https://gdc.xenahubs.net/",
                "notes": "GBM dataset",
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-LUAD.star_tpm.tsv",
                "record_name": "TCGA LUAD STAR TPM",
                "project_id": "",
                "dataset_id": "TCGA-LUAD.star_tpm.tsv",
                "hub_id": "gdc_xena",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "primary_site": "Lung",
                "disease_type": "Adenocarcinoma",
                "cancer_scope": "TCGA cancer cohorts",
                "priority_for_atlas": 4,
                "source_url": "https://gdc.xenahubs.net/",
                "notes": "non brain dataset",
            },
        ]
    )


def test_collect_match_terms():
    row = make_unified_df().iloc[0]
    terms = collect_match_terms(row)

    assert "gbm" in terms
    assert "brain" in terms or "glioma" in terms


def test_filter_gbm_relevant_records():
    filtered = filter_gbm_relevant_records(make_unified_df())

    assert filtered.shape[0] == 2
    assert "TCGA-GBM" in set(filtered["record_id"])
    assert "TCGA-GBM.star_tpm.tsv" in set(filtered["record_id"])
    assert "TCGA-LUAD.star_tpm.tsv" not in set(filtered["record_id"])
    assert "gbm_match_terms" in filtered.columns


def test_value_counts_table():
    filtered = filter_gbm_relevant_records(make_unified_df())
    counts = value_counts_table(filtered, "source_id")

    assert "source_id" in counts.columns
    assert "count" in counts.columns


def test_build_gbm_public_omics_atlas_report_html():
    filtered = filter_gbm_relevant_records(make_unified_df())
    html = build_gbm_public_omics_atlas_report_html(filtered)

    assert "GBM Public Omics Atlas Inventory Report" in html
    assert "GBM-relevant records" in html
    assert "TCGA-GBM" in html


def test_build_gbm_public_omics_atlas(tmp_path: Path):
    input_path = tmp_path / "unified.tsv"
    output_path = tmp_path / "gbm.tsv"
    report_path = tmp_path / "gbm_report.html"

    make_unified_df().to_csv(input_path, sep="\t", index=False)

    gbm_df = build_gbm_public_omics_atlas(
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
        make_report=True,
    )

    assert output_path.exists()
    assert report_path.exists()
    assert gbm_df.shape[0] == 2

    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == 2