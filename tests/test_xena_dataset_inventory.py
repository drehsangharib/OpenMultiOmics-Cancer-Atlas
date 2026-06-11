import json
from pathlib import Path

import pandas as pd

from core.search.xena_dataset_inventory import (
    XENA_DATASET_COLUMNS,
    build_dataset_label,
    build_xena_dataset_inventory_dataframe,
    build_xena_dataset_record,
    infer_cancer_scope,
    infer_data_category,
    infer_matrix_type,
    infer_omics_modality,
    parse_xena_dataset_response,
    select_hubs,
    write_xena_dataset_inventory,
)


def make_hub_inventory_df():
    return pd.DataFrame(
        [
            {
                "hub_id": "gdc_xena",
                "hub_name": "GDC Xena Hub",
                "hub_url": "https://gdc.xenahubs.net",
                "source_scope": "GDC-derived public matrices",
                "primary_resources": "GDC; TCGA",
                "omics_scope": "transcriptomics; clinical",
                "cancer_relevance": "demo",
                "access_type": "open",
                "recommended_for_first_integration": True,
                "priority_for_atlas": 5,
                "integration_stage": "planned_next",
                "notes": "demo",
            },
            {
                "hub_id": "treehouse_xena",
                "hub_name": "Treehouse Xena Hub",
                "hub_url": "https://xena.treehouse.gi.ucsc.edu:443",
                "source_scope": "Treehouse pediatric cancer",
                "primary_resources": "Treehouse",
                "omics_scope": "transcriptomics",
                "cancer_relevance": "demo",
                "access_type": "open",
                "recommended_for_first_integration": False,
                "priority_for_atlas": 3,
                "integration_stage": "planned_later",
                "notes": "demo",
            },
        ]
    )


def fake_query_func(hub_url: str, timeout: int):
    if "gdc" in hub_url:
        return [
            "TCGA.GBM.sampleMap/HiSeqV2",
            "TCGA.GBM.sampleMap/Gistic2_CopyNumber_Gistic2_all_thresholded.by_genes",
            "TCGA.GBM.sampleMap/DNA_methylation",
            "TCGA.GBM.sampleMap/clinicalMatrix",
            "TCGA.GBM.sampleMap/mutation_broad",
        ]

    return ["Treehouse_expression_matrix"]


def test_parse_xena_dataset_response_list():
    payload = ["dataset_a", "dataset_b"]
    assert parse_xena_dataset_response(payload) == ["dataset_a", "dataset_b"]


def test_parse_xena_dataset_response_dict():
    payload = {"datasets": ["dataset_a", "dataset_b"]}
    assert parse_xena_dataset_response(payload) == ["dataset_a", "dataset_b"]


def test_infer_data_category():
    assert infer_data_category("TCGA.GBM.sampleMap/HiSeqV2") == "gene expression"
    assert infer_data_category("clinicalMatrix") == "clinical phenotype"
    assert infer_data_category("DNA_methylation") == "DNA methylation"
    assert infer_data_category("Gistic2_CopyNumber") == "copy number"
    assert infer_data_category("mutation_broad") == "somatic mutation"


def test_infer_omics_modality():
    assert infer_omics_modality("HiSeqV2") == "transcriptomics"
    assert infer_omics_modality("clinicalMatrix") == "clinical_annotation"
    assert infer_omics_modality("DNA_methylation") == "methylation"
    assert infer_omics_modality("Gistic2_CopyNumber") == "cnv"
    assert infer_omics_modality("mutation_broad") == "snv"


def test_infer_matrix_type():
    assert infer_matrix_type("HiSeqV2") == "sample-by-gene expression matrix"
    assert infer_matrix_type("clinicalMatrix") == "sample-by-feature annotation table"


def test_build_dataset_label():
    label = build_dataset_label("TCGA.GBM.sampleMap/HiSeqV2")
    assert "TCGA.GBM.sampleMap" in label
    assert "HiSeqV2" in label


def test_select_hubs():
    df = make_hub_inventory_df()
    selected = select_hubs(df, hub_ids=["gdc_xena"])
    assert selected.shape[0] == 1
    assert selected.iloc[0]["hub_id"] == "gdc_xena"

    recommended = select_hubs(df, recommended_only=True)
    assert set(recommended["hub_id"]) == {"gdc_xena"}


def test_build_xena_dataset_record():
    hub_row = make_hub_inventory_df().iloc[0].to_dict()
    record = build_xena_dataset_record(
        hub_row=hub_row,
        dataset_id="TCGA.GBM.sampleMap/HiSeqV2",
    )

    assert record["hub_id"] == "gdc_xena"
    assert record["omics_modality"] == "transcriptomics"
    assert record["data_category"] == "gene expression"
    assert record["source_database"] == "UCSC Xena"


def test_build_xena_dataset_inventory_dataframe_with_fake_query():
    df = build_xena_dataset_inventory_dataframe(
        hub_inventory_df=make_hub_inventory_df(),
        hub_ids=["gdc_xena"],
        query_func=fake_query_func,
    )

    assert list(df.columns) == XENA_DATASET_COLUMNS
    assert not df.empty
    assert set(df["hub_id"]) == {"gdc_xena"}
    assert "transcriptomics" in set(df["omics_modality"])
    assert "clinical_annotation" in set(df["omics_modality"])


def test_build_xena_dataset_inventory_dataframe_recommended_only():
    df = build_xena_dataset_inventory_dataframe(
        hub_inventory_df=make_hub_inventory_df(),
        recommended_only=True,
        query_func=fake_query_func,
    )

    assert not df.empty
    assert set(df["hub_id"]) == {"gdc_xena"}


def test_write_xena_dataset_inventory(tmp_path: Path, monkeypatch):
    output_path = tmp_path / "xena_dataset_inventory.tsv"

    monkeypatch.setattr(
        "core.search.xena_dataset_inventory.build_xena_hub_inventory_dataframe",
        lambda: make_hub_inventory_df(),
    )
    monkeypatch.setattr(
        "core.search.xena_dataset_inventory.query_xena_hub_datasets",
        fake_query_func,
    )

    df = write_xena_dataset_inventory(
        output_path=output_path,
        hub_ids=["gdc_xena"],
    )

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == df.shape[0]
    assert "dataset_id" in loaded.columns