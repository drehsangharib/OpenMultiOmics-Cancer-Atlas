from pathlib import Path

import pandas as pd

from core.search.xena_dataset_inventory_seed import (
    XENA_DATASET_SEED_COLUMNS,
    build_xena_dataset_seed_dataframe,
    filter_xena_dataset_seed_inventory,
    get_xena_dataset_seed_records,
    write_xena_dataset_seed_inventory,
)


def test_get_xena_dataset_seed_records_contains_core_seeds():
    records = get_xena_dataset_seed_records()
    seed_ids = {record["dataset_seed_id"] for record in records}

    assert "gdc_xena_tcga_expression" in seed_ids
    assert "gdc_xena_tcga_clinical" in seed_ids
    assert "toil_tcga_gtex_expression" in seed_ids
    assert "pancanatlas_subtypes" in seed_ids


def test_build_xena_dataset_seed_dataframe_columns_and_sorting():
    df = build_xena_dataset_seed_dataframe()

    assert list(df.columns) == XENA_DATASET_SEED_COLUMNS
    assert df.shape[0] >= 10
    assert df.iloc[0]["priority_for_atlas"] >= df.iloc[-1]["priority_for_atlas"]


def test_filter_xena_dataset_seed_inventory_recommended_only():
    df = build_xena_dataset_seed_dataframe()
    filtered = filter_xena_dataset_seed_inventory(df, recommended_only=True)

    assert not filtered.empty
    assert filtered["recommended_for_first_integration"].all()
    assert "gdc_xena" in set(filtered["hub_id"])


def test_filter_xena_dataset_seed_inventory_by_hub_id():
    df = build_xena_dataset_seed_dataframe()
    filtered = filter_xena_dataset_seed_inventory(df, hub_id="toil")

    assert not filtered.empty
    assert set(filtered["hub_id"]) == {"toil_xena"}


def test_filter_xena_dataset_seed_inventory_by_modality():
    df = build_xena_dataset_seed_dataframe()
    filtered = filter_xena_dataset_seed_inventory(df, omics_modality="transcriptomics")

    assert not filtered.empty
    assert "transcriptomics" in set(filtered["omics_modality"])


def test_filter_xena_dataset_seed_inventory_by_category():
    df = build_xena_dataset_seed_dataframe()
    filtered = filter_xena_dataset_seed_inventory(df, data_category="methylation")

    assert not filtered.empty
    assert "DNA methylation" in set(filtered["data_category"])


def test_filter_xena_dataset_seed_inventory_min_priority():
    df = build_xena_dataset_seed_dataframe()
    filtered = filter_xena_dataset_seed_inventory(df, min_priority=5)

    assert not filtered.empty
    assert filtered["priority_for_atlas"].min() >= 5


def test_write_xena_dataset_seed_inventory(tmp_path: Path):
    output_path = tmp_path / "xena_dataset_seed.tsv"

    df = write_xena_dataset_seed_inventory(output_path=output_path)

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == df.shape[0]
    assert "dataset_seed_id" in loaded.columns


def test_write_xena_dataset_seed_inventory_filtered(tmp_path: Path):
    output_path = tmp_path / "xena_dataset_seed_filtered.tsv"

    df = write_xena_dataset_seed_inventory(
        output_path=output_path,
        recommended_only=True,
        min_priority=5,
    )

    assert output_path.exists()
    assert not df.empty
    assert df["priority_for_atlas"].min() >= 5
    assert df["recommended_for_first_integration"].all()