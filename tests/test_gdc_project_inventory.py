import pandas as pd

from core.search.gdc_project_inventory import (
    add_inventory_annotations,
    normalize_list_or_value,
    parse_gdc_project_hit,
    parse_gdc_projects_response,
    safe_get_nested,
)


def test_safe_get_nested_existing_path():
    record = {"summary": {"case_count": 123}}
    assert safe_get_nested(record, "summary.case_count") == 123


def test_safe_get_nested_missing_path_returns_default():
    record = {"summary": {"case_count": 123}}
    assert safe_get_nested(record, "summary.file_count", default="NA") == "NA"


def test_normalize_list_or_value_scalar():
    assert normalize_list_or_value("GBM") == "GBM"
    assert normalize_list_or_value(10) == "10"


def test_normalize_list_or_value_list():
    assert normalize_list_or_value(["Brain", "Lung"]) == "Brain; Lung"


def test_normalize_list_or_value_none():
    assert normalize_list_or_value(None) == ""


def test_parse_gdc_project_hit_flattening():
    hit = {
        "project_id": "TCGA-GBM",
        "name": "Glioblastoma Multiforme",
        "primary_site": ["Brain"],
        "disease_type": ["Gliomas"],
        "program": {"name": "TCGA"},
        "summary": {
            "case_count": 600,
            "file_count": 10000,
        },
    }

    row = parse_gdc_project_hit(hit)

    assert row["project_id"] == "TCGA-GBM"
    assert row["project_name"] == "Glioblastoma Multiforme"
    assert row["program_name"] == "TCGA"
    assert row["primary_site"] == "Brain"
    assert row["disease_type"] == "Gliomas"
    assert row["case_count"] == "600"
    assert row["file_count"] == "10000"
    assert row["source_database"] == "GDC"


def test_parse_gdc_projects_response():
    payload = {
        "data": {
            "hits": [
                {
                    "project_id": "TCGA-LUAD",
                    "name": "Lung Adenocarcinoma",
                    "primary_site": ["Bronchus and lung"],
                    "disease_type": ["Adenomas and Adenocarcinomas"],
                    "program": {"name": "TCGA"},
                    "summary": {"case_count": 500, "file_count": 8000},
                },
                {
                    "project_id": "TCGA-GBM",
                    "name": "Glioblastoma Multiforme",
                    "primary_site": ["Brain"],
                    "disease_type": ["Gliomas"],
                    "program": {"name": "TCGA"},
                    "summary": {"case_count": 600, "file_count": 10000},
                },
            ]
        }
    }

    df = parse_gdc_projects_response(payload)

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 2
    assert set(df["project_id"]) == {"TCGA-LUAD", "TCGA-GBM"}
    assert "program_name" in df.columns
    assert "source_endpoint" in df.columns


def test_add_inventory_annotations_empty_dataframe():
    df = pd.DataFrame()
    out = add_inventory_annotations(df)

    assert "atlas_scope" in out.columns
    assert "public_data_use" in out.columns


def test_add_inventory_annotations_nonempty_dataframe():
    df = pd.DataFrame(
        {
            "project_id": ["TCGA-GBM"],
            "project_name": ["Glioblastoma Multiforme"],
        }
    )

    out = add_inventory_annotations(df)

    assert out.loc[0, "atlas_scope"] == "pan_cancer_public_reference"
    assert out.loc[0, "public_data_use"] == "project_inventory"