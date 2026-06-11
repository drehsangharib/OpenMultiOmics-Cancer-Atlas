from pathlib import Path

import pandas as pd

from core.search.xena_hub_inventory import (
    XENA_HUB_COLUMNS,
    XenaHub,
    build_xena_hub_inventory_dataframe,
    filter_xena_hub_inventory,
    get_xena_hubs,
    write_xena_hub_inventory,
)


def test_get_xena_hubs_contains_core_hubs():
    hubs = get_xena_hubs()
    hub_ids = {hub.hub_id for hub in hubs}

    assert "ucsc_public" in hub_ids
    assert "gdc_xena" in hub_ids
    assert "tcga_xena" in hub_ids
    assert "pancanatlas" in hub_ids
    assert "toil_xena" in hub_ids


def test_xena_hub_to_record():
    hub = XenaHub(
        hub_id="demo",
        hub_name="Demo Hub",
        hub_url="https://example.org",
        source_scope="demo",
        primary_resources="demo",
        omics_scope="transcriptomics",
        cancer_relevance="demo relevance",
        access_type="open",
        recommended_for_first_integration=True,
        priority_for_atlas=5,
        integration_stage="test",
        notes="demo notes",
    )

    record = hub.to_record()

    assert record["hub_id"] == "demo"
    assert record["recommended_for_first_integration"] is True
    assert record["priority_for_atlas"] == 5


def test_build_xena_hub_inventory_dataframe_columns_and_sorting():
    df = build_xena_hub_inventory_dataframe()

    assert list(df.columns) == XENA_HUB_COLUMNS
    assert df.shape[0] >= 5
    assert df.iloc[0]["priority_for_atlas"] >= df.iloc[-1]["priority_for_atlas"]


def test_filter_xena_hub_inventory_recommended_only():
    df = build_xena_hub_inventory_dataframe()
    filtered = filter_xena_hub_inventory(df, recommended_only=True)

    assert not filtered.empty
    assert filtered["recommended_for_first_integration"].all()
    assert "gdc_xena" in set(filtered["hub_id"])


def test_filter_xena_hub_inventory_by_omics_scope():
    df = build_xena_hub_inventory_dataframe()
    filtered = filter_xena_hub_inventory(df, omics_scope="transcriptomics")

    assert not filtered.empty
    assert "toil_xena" in set(filtered["hub_id"])


def test_filter_xena_hub_inventory_min_priority():
    df = build_xena_hub_inventory_dataframe()
    filtered = filter_xena_hub_inventory(df, min_priority=5)

    assert not filtered.empty
    assert filtered["priority_for_atlas"].min() >= 5


def test_write_xena_hub_inventory(tmp_path: Path):
    output_path = tmp_path / "xena_hubs.tsv"

    df = write_xena_hub_inventory(output_path=output_path)

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == df.shape[0]
    assert "hub_id" in loaded.columns


def test_write_xena_hub_inventory_filtered(tmp_path: Path):
    output_path = tmp_path / "xena_hubs_filtered.tsv"

    df = write_xena_hub_inventory(
        output_path=output_path,
        recommended_only=True,
        min_priority=5,
    )

    assert output_path.exists()
    assert not df.empty
    assert df["priority_for_atlas"].min() >= 5
    assert df["recommended_for_first_integration"].all()