from pathlib import Path

import pandas as pd

from core.integration.unified_public_cancer_omics_inventory import (
    UNIFIED_COLUMNS,
    build_unified_public_cancer_omics_inventory,
    finalize_unified_inventory,
    infer_priority_for_atlas_from_score,
    normalize_gdc_inventory,
    normalize_xena_inventory,
    write_unified_public_cancer_omics_inventory,
)


def make_gdc_df():
    return pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "case_count": 617,
                "file_count": 1200,
                "priority_score": 95,
                "priority_label": "very_high",
                "rna_file_count": 100,
                "mutation_file_count": 50,
                "methylation_file_count": 40,
            },
            {
                "project_id": "TCGA-LGG",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "case_count": 516,
                "file_count": 1000,
                "priority_score": 90,
                "priority_label": "very_high",
                "rna_file_count": 100,
                "copy_number_file_count": 25,
            },
        ]
    )


def make_xena_df():
    return pd.DataFrame(
        [
            {
                "hub_id": "gdc_xena",
                "hub_name": "GDC Xena Hub",
                "hub_url": "https://gdc.xenahubs.net",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
                "dataset_name": "TCGA-GBM.star_tpm.tsv",
                "dataset_label": "TCGA GBM STAR TPM",
                "data_category": "gene expression",
                "omics_modality": "transcriptomics",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "cancer_scope": "TCGA cancer cohorts",
                "sample_scope": "samples",
                "priority_for_atlas": 5,
                "integration_stage": "live_inventory",
                "source_database": "UCSC Xena",
                "notes": "Metadata-only inventory.",
            },
            {
                "hub_id": "pancanatlas",
                "hub_name": "Pan-Cancer Atlas Hub",
                "hub_url": "https://pancanatlas.xenahubs.net",
                "dataset_id": "TCGA-RPPA-pancan-clean.xena",
                "dataset_name": "TCGA-RPPA-pancan-clean.xena",
                "dataset_label": "TCGA RPPA pancan clean",
                "data_category": "protein abundance",
                "omics_modality": "proteomics",
                "matrix_type": "sample-by-protein abundance matrix",
                "resource_family": "TCGA Pan-Cancer Atlas",
                "cancer_scope": "pan-cancer",
                "sample_scope": "samples",
                "priority_for_atlas": 5,
                "integration_stage": "live_inventory",
                "source_database": "UCSC Xena",
                "notes": "Metadata-only inventory.",
            },
        ]
    )


def test_infer_priority_for_atlas_from_score():
    assert infer_priority_for_atlas_from_score(95, "") == 5
    assert infer_priority_for_atlas_from_score(65, "") == 4
    assert infer_priority_for_atlas_from_score(45, "") == 3
    assert infer_priority_for_atlas_from_score(25, "") == 2
    assert infer_priority_for_atlas_from_score(5, "") == 1
    assert infer_priority_for_atlas_from_score("", "very_high") == 5


def test_normalize_gdc_inventory():
    normalized = normalize_gdc_inventory(make_gdc_df())

    assert list(normalized.columns) == UNIFIED_COLUMNS
    assert normalized.shape[0] == 2
    assert set(normalized["source_id"]) == {"gdc"}
    assert set(normalized["source_record_type"]) == {"gdc_project"}
    assert "TCGA-GBM" in set(normalized["project_id"])
    assert normalized["priority_for_atlas"].max() == 5


def test_normalize_xena_inventory():
    normalized = normalize_xena_inventory(make_xena_df())

    assert list(normalized.columns) == UNIFIED_COLUMNS
    assert normalized.shape[0] == 2
    assert set(normalized["source_id"]) == {"xena"}
    assert set(normalized["source_record_type"]) == {"xena_dataset"}
    assert "TCGA-GBM.star_tpm.tsv" in set(normalized["dataset_id"])


def test_finalize_unified_inventory_schema_and_sorting():
    gdc = normalize_gdc_inventory(make_gdc_df())
    xena = normalize_xena_inventory(make_xena_df())
    combined = pd.concat([gdc, xena], ignore_index=True)

    finalized = finalize_unified_inventory(combined)

    assert list(finalized.columns) == UNIFIED_COLUMNS
    assert finalized.iloc[0]["priority_for_atlas"] >= finalized.iloc[-1]["priority_for_atlas"]


def test_build_unified_public_cancer_omics_inventory_from_files(tmp_path: Path):
    gdc_path = tmp_path / "gdc.tsv"
    xena_path = tmp_path / "xena.tsv"

    make_gdc_df().to_csv(gdc_path, sep="\t", index=False)
    make_xena_df().to_csv(xena_path, sep="\t", index=False)

    unified = build_unified_public_cancer_omics_inventory(
        gdc_input=gdc_path,
        xena_input=xena_path,
        allow_missing_inputs=False,
    )

    assert list(unified.columns) == UNIFIED_COLUMNS
    assert unified.shape[0] == 4
    assert set(unified["source_id"]) == {"gdc", "xena"}


def test_write_unified_public_cancer_omics_inventory(tmp_path: Path):
    gdc_path = tmp_path / "gdc.tsv"
    xena_path = tmp_path / "xena.tsv"
    output_path = tmp_path / "unified.tsv"

    make_gdc_df().to_csv(gdc_path, sep="\t", index=False)
    make_xena_df().to_csv(xena_path, sep="\t", index=False)

    unified = write_unified_public_cancer_omics_inventory(
        output_path=output_path,
        gdc_input=gdc_path,
        xena_input=xena_path,
        allow_missing_inputs=False,
    )

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == unified.shape[0]
    assert "source_id" in loaded.columns