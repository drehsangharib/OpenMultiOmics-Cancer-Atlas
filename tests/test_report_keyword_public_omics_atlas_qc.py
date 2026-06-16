from pathlib import Path

import pandas as pd

import core.atlas.report_keyword_public_omics_atlas_qc as qc


def make_atlas_df():
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
                "atlas_match_terms": "brain;gbm;glioma",
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
                "atlas_match_terms": "gbm;tcga-gbm",
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "unknown_dataset.txt",
                "record_name": "unknown dataset",
                "project_id": "",
                "dataset_id": "unknown_dataset.txt",
                "hub_id": "pancanatlas",
                "omics_modality": "unknown",
                "data_category": "unknown",
                "matrix_type": "unknown",
                "resource_family": "TCGA Pan-Cancer Atlas",
                "primary_site": "",
                "disease_type": "",
                "cancer_scope": "pan-cancer",
                "priority_for_atlas": 4,
                "source_url": "",
                "atlas_match_terms": "glioma",
            },
        ]
    )


def test_qc_metrics():
    metrics = qc.build_qc_metrics(make_atlas_df())

    assert "total_rows" in set(metrics["metric"])
    assert "unknown_modality_rows" in set(metrics["metric"])
    assert int(metrics.loc[metrics["metric"] == "total_rows", "value"].iloc[0]) == 3


def test_missingness_table():
    table = qc.build_missingness_table(make_atlas_df())

    assert "column" in table.columns
    assert "missing_rows" in table.columns


def test_value_counts_table():
    table = qc.value_counts_table(make_atlas_df(), "source_id")

    assert "source_id" in table.columns
    assert "count" in table.columns


def test_unknown_modality_table():
    table = qc.build_unknown_modality_table(make_atlas_df())

    assert table.shape[0] == 1
    assert table.iloc[0]["record_id"] == "unknown_dataset.txt"


def test_missing_source_url_table():
    table = qc.build_missing_source_url_table(make_atlas_df())

    assert table.shape[0] == 1
    assert table.iloc[0]["record_id"] == "unknown_dataset.txt"


def test_source_modality_coverage_table():
    table = qc.build_source_modality_coverage_table(make_atlas_df())

    assert not table.empty
    assert "source_id" in table.columns


def test_build_qc_report_html():
    report_html = qc.build_qc_report_html(make_atlas_df(), atlas_name="gbm")

    assert "GBM Public Omics Atlas QC Report" in report_html
    assert "Source x modality coverage" in report_html
    assert "unknown_dataset.txt" in report_html


def test_default_paths():
    assert str(qc.default_input_path("gbm")).replace("\\", "/").endswith(
        "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv"
    )
    assert str(qc.default_output_path("gbm")).replace("\\", "/").endswith(
        "outputs/reports/gbm_public_omics_atlas_qc_report.html"
    )


def test_generate_keyword_public_omics_atlas_qc_report(tmp_path: Path):
    input_path = tmp_path / "gbm.tsv"
    output_path = tmp_path / "gbm_qc.html"

    make_atlas_df().to_csv(input_path, sep="\t", index=False)

    report_html = qc.generate_keyword_public_omics_atlas_qc_report(
        atlas_name="gbm",
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert "Total records" in report_html
    assert "unknown_dataset.txt" in output_path.read_text(encoding="utf-8")