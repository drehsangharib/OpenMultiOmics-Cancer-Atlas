from pathlib import Path

import pandas as pd

from core.reporting.xena_dataset_inventory_report import (
    build_examples_by_hub_and_modality,
    build_top_priority_table,
    build_unknown_review_table,
    build_xena_dataset_inventory_report_html,
    dataframe_to_html_table,
    generate_xena_dataset_inventory_report,
    read_xena_dataset_inventory,
    value_counts_table,
)


def make_inventory_df():
    return pd.DataFrame(
        [
            {
                "hub_id": "gdc_xena",
                "hub_name": "GDC Xena Hub",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
                "dataset_label": "TCGA GBM star tpm",
                "data_category": "gene expression",
                "omics_modality": "transcriptomics",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "cancer_scope": "TCGA cancer cohorts",
                "sample_scope": "samples",
                "priority_for_atlas": 5,
                "integration_stage": "live_inventory",
                "notes": "Metadata-only inventory; matrix data not downloaded.",
            },
            {
                "hub_id": "gdc_xena",
                "hub_name": "GDC Xena Hub",
                "dataset_id": "TCGA-GBM.clinical.tsv",
                "dataset_label": "TCGA GBM clinical",
                "data_category": "clinical phenotype",
                "omics_modality": "clinical_annotation",
                "matrix_type": "sample-by-feature annotation table",
                "resource_family": "TCGA",
                "cancer_scope": "TCGA cancer cohorts",
                "sample_scope": "patients and samples",
                "priority_for_atlas": 5,
                "integration_stage": "live_inventory",
                "notes": "Metadata-only inventory; matrix data not downloaded.",
            },
            {
                "hub_id": "pancanatlas",
                "hub_name": "Pan-Cancer Atlas Hub",
                "dataset_id": "unknown_dataset.txt",
                "dataset_label": "unknown dataset",
                "data_category": "unknown",
                "omics_modality": "unknown",
                "matrix_type": "unknown",
                "resource_family": "TCGA Pan-Cancer Atlas",
                "cancer_scope": "pan-cancer",
                "sample_scope": "samples",
                "priority_for_atlas": 4,
                "integration_stage": "live_inventory",
                "notes": "Metadata-only inventory; matrix data not downloaded.",
            },
        ]
    )


def test_value_counts_table():
    df = make_inventory_df()
    counts = value_counts_table(df, "hub_id")

    assert list(counts.columns) == ["hub_id", "count"]
    assert "gdc_xena" in set(counts["hub_id"])


def test_dataframe_to_html_table():
    df = pd.DataFrame({"a": ["<unsafe>"], "b": [1]})
    html = dataframe_to_html_table(df)

    assert "<table" in html
    assert "&lt;unsafe&gt;" in html


def test_build_unknown_review_table():
    df = make_inventory_df()
    unknown = build_unknown_review_table(df)

    assert unknown.shape[0] == 1
    assert unknown.iloc[0]["hub_id"] == "pancanatlas"


def test_build_top_priority_table():
    df = make_inventory_df()
    top = build_top_priority_table(df)

    assert not top.empty
    assert top.iloc[0]["priority_for_atlas"] >= top.iloc[-1]["priority_for_atlas"]


def test_build_examples_by_hub_and_modality():
    df = make_inventory_df()
    examples = build_examples_by_hub_and_modality(df)

    assert not examples.empty
    assert "example_dataset_id" in examples.columns


def test_build_xena_dataset_inventory_report_html():
    df = make_inventory_df()
    html = build_xena_dataset_inventory_report_html(df)

    assert "UCSC Xena Dataset Inventory Report" in html
    assert "Dataset counts by hub" in html
    assert "Unknown-classification review list" in html
    assert "TCGA-GBM.star_tpm.tsv" in html


def test_read_xena_dataset_inventory(tmp_path: Path):
    input_path = tmp_path / "xena_dataset_inventory.tsv"
    make_inventory_df().to_csv(input_path, sep="\t", index=False)

    loaded = read_xena_dataset_inventory(input_path)

    assert loaded.shape[0] == 3
    assert "hub_id" in loaded.columns


def test_generate_xena_dataset_inventory_report(tmp_path: Path):
    input_path = tmp_path / "xena_dataset_inventory.tsv"
    output_path = tmp_path / "xena_dataset_inventory_report.html"

    make_inventory_df().to_csv(input_path, sep="\t", index=False)

    html = generate_xena_dataset_inventory_report(
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert "Dataset rows" in html
    assert "TCGA-GBM.clinical.tsv" in output_path.read_text(encoding="utf-8")