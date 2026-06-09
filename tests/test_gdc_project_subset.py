import pandas as pd
import pytest

from core.search.gdc_project_subset import (
    build_gdc_project_subset_from_dataframes,
    build_subset_query_description,
    contains_any,
    filter_project_subset,
    join_gdc_project_tables,
    modality_to_column,
    parse_bool,
    parse_int,
)


def make_project_df():
    return pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "project_name": "Glioblastoma Multiforme",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "case_count": 600,
                "file_count": 30000,
            },
            {
                "project_id": "TCGA-BRCA",
                "project_name": "Breast Invasive Carcinoma",
                "program_name": "TCGA",
                "primary_site": "Breast",
                "disease_type": "Ductal and Lobular Neoplasms",
                "case_count": 1100,
                "file_count": 70000,
            },
            {
                "project_id": "CPTAC-3",
                "project_name": "CPTAC-3 Discovery",
                "program_name": "CPTAC",
                "primary_site": "Multiple",
                "disease_type": "Multiple",
                "case_count": 900,
                "file_count": 100000,
            },
        ]
    )


def make_modality_df():
    return pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "has_transcriptomics": True,
                "has_methylation": True,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": True,
                "has_biospecimen": True,
                "has_proteomics": True,
                "has_slide_images": True,
                "has_sequencing_reads": True,
                "total_file_count": 30000,
                "open_file_count": 15000,
                "controlled_file_count": 15000,
            },
            {
                "project_id": "TCGA-BRCA",
                "has_transcriptomics": True,
                "has_methylation": True,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": True,
                "has_biospecimen": True,
                "has_proteomics": True,
                "has_slide_images": True,
                "has_sequencing_reads": True,
                "total_file_count": 70000,
                "open_file_count": 35000,
                "controlled_file_count": 35000,
            },
            {
                "project_id": "CPTAC-3",
                "has_transcriptomics": True,
                "has_methylation": True,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": False,
                "has_biospecimen": False,
                "has_proteomics": True,
                "has_slide_images": False,
                "has_sequencing_reads": True,
                "total_file_count": 100000,
                "open_file_count": 20000,
                "controlled_file_count": 80000,
            },
        ]
    )


def make_ranking_df():
    return pd.DataFrame(
        [
            {
                "rank": 1,
                "project_id": "TCGA-BRCA",
                "priority_score": 36,
                "priority_label": "excellent",
                "multiomics_modality_count": 10,
                "priority_rationale": "transcriptomics; methylation; proteomics; clinical",
            },
            {
                "rank": 2,
                "project_id": "TCGA-GBM",
                "priority_score": 35,
                "priority_label": "excellent",
                "multiomics_modality_count": 10,
                "priority_rationale": "transcriptomics; methylation; proteomics; clinical",
            },
            {
                "rank": 3,
                "project_id": "CPTAC-3",
                "priority_score": 31,
                "priority_label": "excellent",
                "multiomics_modality_count": 7,
                "priority_rationale": "transcriptomics; methylation; proteomics",
            },
        ]
    )


def make_joined_df():
    return join_gdc_project_tables(
        project_df=make_project_df(),
        modality_df=make_modality_df(),
        ranking_df=make_ranking_df(),
    )


def test_parse_int_and_bool():
    assert parse_int("10") == 10
    assert parse_int("bad") == 0
    assert parse_bool("True") is True
    assert parse_bool("false") is False


def test_contains_any():
    assert contains_any("Brain; Central nervous system", ["brain"]) is True
    assert contains_any("Breast", ["lung", "brain"]) is False
    assert contains_any("Breast", None) is True


def test_modality_to_column():
    assert modality_to_column("transcriptomics") == "has_transcriptomics"
    assert modality_to_column("DNA methylation") == "has_methylation"
    assert modality_to_column("proteomics") == "has_proteomics"

    with pytest.raises(ValueError):
        modality_to_column("unknown_modality")


def test_join_gdc_project_tables():
    joined = make_joined_df()

    assert joined.shape[0] == 3
    assert "project_name" in joined.columns
    assert "has_transcriptomics" in joined.columns
    assert "priority_score" in joined.columns


def test_filter_by_primary_site():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        primary_sites=["Brain"],
    )

    assert subset.shape[0] == 1
    assert subset.iloc[0]["project_id"] == "TCGA-GBM"


def test_filter_by_program():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        programs=["TCGA"],
    )

    assert set(subset["project_id"]) == {"TCGA-GBM", "TCGA-BRCA"}


def test_filter_by_priority_label_and_min_case_count():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        priority_labels=["excellent"],
        min_case_count=1000,
    )

    assert subset.shape[0] == 1
    assert subset.iloc[0]["project_id"] == "TCGA-BRCA"


def test_filter_by_required_modality():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        required_modalities=["clinical", "proteomics"],
    )

    assert set(subset["project_id"]) == {"TCGA-GBM", "TCGA-BRCA"}


def test_filter_top_n():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        top_n=2,
    )

    assert subset.shape[0] == 2
    assert subset.iloc[0]["project_id"] == "TCGA-BRCA"


def test_build_subset_query_description():
    description = build_subset_query_description(
        programs=["TCGA"],
        primary_sites=["Brain"],
        required_modalities=["transcriptomics"],
        min_case_count=100,
    )

    assert "program=TCGA" in description
    assert "primary_site=Brain" in description
    assert "has_modality=transcriptomics" in description
    assert "min_case_count=100" in description


def test_build_gdc_project_subset_from_dataframes():
    subset = build_gdc_project_subset_from_dataframes(
        project_df=make_project_df(),
        modality_df=make_modality_df(),
        ranking_df=make_ranking_df(),
        programs=["TCGA"],
        required_modalities=["proteomics"],
    )

    assert set(subset["project_id"]) == {"TCGA-GBM", "TCGA-BRCA"}
    assert "subset_query" in subset.columns
    assert "source_database" in subset.columns
def test_filter_by_primary_site_exact():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        primary_sites_exact=["Brain"],
    )

    assert subset.shape[0] == 1
    assert subset.iloc[0]["project_id"] == "TCGA-GBM"


def test_filter_by_disease_type_exact():
    subset = filter_project_subset(
        joined_df=make_joined_df(),
        disease_types_exact=["Gliomas"],
    )

    assert subset.shape[0] == 1
    assert subset.iloc[0]["project_id"] == "TCGA-GBM"
