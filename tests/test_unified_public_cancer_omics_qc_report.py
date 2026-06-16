from pathlib import Path

import pandas as pd

from core.reporting.unified_public_cancer_omics_qc_report import (
    build_brain_gbm_relevant_table,
    build_duplicate_record_table,
    build_missing_source_url_table,
    build_missingness_table,
    build_qc_metric_table,
    build_qc_report_html,
    build_unknown_modality_table,
    generate_unified_public_cancer_omics_qc_report,
    read_unified_inventory,
    value_counts_table,
)


def make_unified_df():
    return pd.DataFrame(
        [
            {
                "source_id": "gdc",
                "source_name": "NCI Genomic Data Commons",
                "source_record_type": "gdc_project",
                "record_id": "TCGA-GBM",
                "record_name": "Glioblastoma Multiforme",
                "project_id": "TCGA-GBM",
                "dataset_id": "",
                "hub_id": "",
                "cancer_scope": "GDC project/cohort",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "data_category": "GDC project metadata",
                "omics_modality": "clinical_annotation;snv;transcriptomics",
                "matrix_type": "project-level metadata",
                "resource_family": "TCGA",
                "sample_scope": "cases",
                "case_count": 617,
                "file_count": 1200,
                "priority_for_atlas": 5,
                "priority_score": 95,
                "priority_label": "very_high",
                "integration_stage": "unified_inventory",
                "source_url": "https://portal.gdc.cancer.gov/projects/TCGA-GBM",
                "notes": "demo",
            },
            {
                "source_id": "xena",
                "source_name": "UCSC Xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-GBM.star_tpm.tsv",
                "record_name": "TCGA GBM STAR TPM",
                "project_id": "",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
                "hub_id": "gdc_xena",
                "cancer_scope": "TCGA cancer cohorts",
                "primary_site": "",
                "disease_type": "",
                "data_category": "gene expression",
                "omics_modality": "transcriptomics",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "sample_scope": "samples",
                "case_count": "",
                "file_count": "",
                "priority_for_atlas": 5,
                "priority_score": "",
                "priority_label": "",
                "integration_stage": "unified_inventory",
                "source_url": "https://gdc.xenahubs.net/",
                "notes": "demo",
            },
            {
                "source_id": "xena",
                "source_name": "UCSC Xena",
                "source_record_type": "xena_dataset",
                "record_id": "unknown_dataset.txt",
                "record_name": "unknown dataset",
                "project_id": "",
                "dataset_id": "unknown_dataset.txt",
                "hub_id": "pancanatlas",
                "cancer_scope": "pan-cancer",
                "primary_site": "",
                "disease_type": "",
                "data_category": "unknown",
                "omics_modality": "unknown",
                "matrix_type": "unknown",
                "resource_family": "TCGA Pan-Cancer Atlas",
                "sample_scope": "samples",
                "case_count": "",
                "file_count": "",
                "priority_for_atlas": 4,
                "priority_score": "",
                "priority_label": "",
                "integration_stage": "unified_inventory",
                "source_url": "",
                "notes": "demo",
            },
        ]
    )


def test_qc_metric_table():
    metrics = build_qc_metric_table(make_unified_df())

    assert "total_rows" in set(metrics["metric"])
    assert "unknown_modality_rows" in set(metrics["metric"])
    assert int(metrics.loc[metrics["metric"] == "total_rows", "value"].iloc[0]) == 3


def test_missingness_table():
    table = build_missingness_table(make_unified_df())

    assert "column" in table.columns
    assert "missing_rows" in table.columns
    assert "source_url" in set(table["column"])


def test_value_counts_table():
    table = value_counts_table(make_unified_df(), "source_id")

    assert "xena" in set(table["source_id"])
    assert "count" in table.columns


def test_unknown_modality_table():
    table = build_unknown_modality_table(make_unified_df())

    assert table.shape[0] == 1
    assert table.iloc[0]["record_id"] == "unknown_dataset.txt"


def test_duplicate_record_table_empty_for_unique_records():
    table = build_duplicate_record_table(make_unified_df())

    assert table.empty


def test_missing_source_url_table():
    table = build_missing_source_url_table(make_unified_df())

    assert table.shape[0] == 1
    assert table.iloc[0]["record_id"] == "unknown_dataset.txt"


def test_brain_gbm_relevant_table():
    table = build_brain_gbm_relevant_table(make_unified_df())

    assert not table.empty
    assert any(table["record_id"].astype(str).str.contains("GBM"))


def test_build_qc_report_html():
    html = build_qc_report_html(make_unified_df())

    assert "Unified Public Cancer Omics Inventory QC Report" in html
    assert "QC metrics" in html
    assert "Unknown-modality review list" in html
    assert "TCGA-GBM" in html


def test_read_unified_inventory(tmp_path: Path):
    input_path = tmp_path / "unified.tsv"
    make_unified_df().to_csv(input_path, sep="\t", index=False)

    loaded = read_unified_inventory(input_path)

    assert loaded.shape[0] == 3
    assert "source_id" in loaded.columns


def test_generate_unified_public_cancer_omics_qc_report(tmp_path: Path):
    input_path = tmp_path / "unified.tsv"
    output_path = tmp_path / "qc_report.html"

    make_unified_df().to_csv(input_path, sep="\t", index=False)

    html = generate_unified_public_cancer_omics_qc_report(
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert "Total records" in html
    assert "unknown_dataset.txt" in output_path.read_text(encoding="utf-8")