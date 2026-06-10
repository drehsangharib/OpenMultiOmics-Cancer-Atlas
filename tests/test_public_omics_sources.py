from pathlib import Path

import pandas as pd

from core.registry.public_omics_sources import (
    SOURCE_COLUMNS,
    PublicOmicsSource,
    build_source_inventory_dataframe,
    filter_source_inventory,
    get_public_omics_sources,
    write_public_omics_sources_inventory,
)


def test_get_public_omics_sources_contains_core_sources():
    sources = get_public_omics_sources()
    source_ids = {source.source_id for source in sources}

    assert "gdc" in source_ids
    assert "xena" in source_ids
    assert "cbioportal" in source_ids
    assert "pdc" in source_ids
    assert "pride" in source_ids
    assert "icgc_argo" in source_ids


def test_public_omics_source_to_record():
    source = PublicOmicsSource(
        source_id="demo",
        source_name="Demo",
        source_type="repository",
        primary_domain="demo domain",
        omics_scope="transcriptomics",
        cancer_relevance="demo relevance",
        access_type="open",
        api_available=True,
        bulk_download_available=True,
        controlled_access_possible=False,
        recommended_first_integration=False,
        priority_for_atlas=3,
        integration_stage="test",
        base_url="https://example.org",
        api_or_docs_url="https://example.org/docs",
        notes="demo notes",
    )

    record = source.to_record()

    assert record["source_id"] == "demo"
    assert record["api_available"] is True
    assert record["priority_for_atlas"] == 3


def test_build_source_inventory_dataframe_columns_and_sorting():
    df = build_source_inventory_dataframe()

    assert list(df.columns) == SOURCE_COLUMNS
    assert df.shape[0] >= 10
    assert df.iloc[0]["priority_for_atlas"] >= df.iloc[-1]["priority_for_atlas"]


def test_filter_source_inventory_api_only():
    df = build_source_inventory_dataframe()
    filtered = filter_source_inventory(df, api_only=True)

    assert not filtered.empty
    assert filtered["api_available"].all()


def test_filter_source_inventory_recommended_only():
    df = build_source_inventory_dataframe()
    filtered = filter_source_inventory(df, recommended_only=True)

    assert not filtered.empty
    assert filtered["recommended_first_integration"].all()
    assert "gdc" in set(filtered["source_id"])
    assert "xena" in set(filtered["source_id"])


def test_filter_source_inventory_by_omics_scope():
    df = build_source_inventory_dataframe()
    filtered = filter_source_inventory(df, omics_scope="proteomics")

    assert not filtered.empty
    assert any(filtered["source_id"].isin(["pdc", "pride", "cptac"]))


def test_filter_source_inventory_min_priority():
    df = build_source_inventory_dataframe()
    filtered = filter_source_inventory(df, min_priority=5)

    assert not filtered.empty
    assert filtered["priority_for_atlas"].min() >= 5


def test_write_public_omics_sources_inventory(tmp_path: Path):
    output_path = tmp_path / "sources.tsv"

    df = write_public_omics_sources_inventory(output_path=output_path)

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == df.shape[0]
    assert "source_id" in loaded.columns


def test_write_public_omics_sources_inventory_filtered(tmp_path: Path):
    output_path = tmp_path / "sources_filtered.tsv"

    df = write_public_omics_sources_inventory(
        output_path=output_path,
        omics_scope="proteomics",
        min_priority=4,
    )

    assert output_path.exists()
    assert not df.empty
    assert df["priority_for_atlas"].min() >= 4