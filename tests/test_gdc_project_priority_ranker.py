import pandas as pd
import pytest

from core.scoring.gdc_project_priority_ranker import (
    assign_priority_label,
    build_gdc_project_priority_ranking_from_dataframes,
    build_priority_rationale,
    compute_case_count_score,
    compute_clinical_utility_score,
    compute_multiomics_modality_count,
    compute_multiomics_score,
    compute_open_data_score,
    compute_proteogenomics_bonus,
    join_project_and_modality_tables,
    parse_bool,
    parse_int,
    validate_columns,
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
                "project_id": "TCGA-LUAD",
                "project_name": "Lung Adenocarcinoma",
                "program_name": "TCGA",
                "primary_site": "Bronchus and lung",
                "disease_type": "Adenomas and Adenocarcinomas",
                "case_count": 500,
                "file_count": 36000,
            },
            {
                "project_id": "MINIMAL-1",
                "project_name": "Minimal Public Project",
                "program_name": "TEST",
                "primary_site": "Unknown",
                "disease_type": "Unknown",
                "case_count": 10,
                "file_count": 20,
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
                "transcriptomics_file_count": 1000,
                "methylation_file_count": 500,
                "snv_file_count": 2000,
                "cnv_file_count": 1200,
                "structural_variation_file_count": 100,
                "clinical_file_count": 600,
                "biospecimen_file_count": 800,
                "proteomics_file_count": 300,
                "slide_image_file_count": 1000,
                "sequencing_read_file_count": 8000,
                "open_file_count": 15000,
                "controlled_file_count": 15000,
                "total_file_count": 30000,
            },
            {
                "project_id": "TCGA-LUAD",
                "has_transcriptomics": True,
                "has_methylation": False,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": True,
                "has_biospecimen": True,
                "has_proteomics": False,
                "has_slide_images": True,
                "has_sequencing_reads": True,
                "transcriptomics_file_count": 1100,
                "methylation_file_count": 0,
                "snv_file_count": 2500,
                "cnv_file_count": 1300,
                "structural_variation_file_count": 100,
                "clinical_file_count": 500,
                "biospecimen_file_count": 700,
                "proteomics_file_count": 0,
                "slide_image_file_count": 900,
                "sequencing_read_file_count": 7000,
                "open_file_count": 20000,
                "controlled_file_count": 16000,
                "total_file_count": 36000,
            },
            {
                "project_id": "MINIMAL-1",
                "has_transcriptomics": False,
                "has_methylation": False,
                "has_snv": False,
                "has_cnv": False,
                "has_structural_variation": False,
                "has_clinical": False,
                "has_biospecimen": False,
                "has_proteomics": False,
                "has_slide_images": False,
                "has_sequencing_reads": True,
                "transcriptomics_file_count": 0,
                "methylation_file_count": 0,
                "snv_file_count": 0,
                "cnv_file_count": 0,
                "structural_variation_file_count": 0,
                "clinical_file_count": 0,
                "biospecimen_file_count": 0,
                "proteomics_file_count": 0,
                "slide_image_file_count": 0,
                "sequencing_read_file_count": 20,
                "open_file_count": 0,
                "controlled_file_count": 20,
                "total_file_count": 20,
            },
        ]
    )


def test_parse_int():
    assert parse_int("10") == 10
    assert parse_int(2.0) == 2
    assert parse_int("bad") == 0
    assert parse_int(None) == 0


def test_parse_bool():
    assert parse_bool(True) is True
    assert parse_bool("True") is True
    assert parse_bool("yes") is True
    assert parse_bool("1") is True
    assert parse_bool(False) is False
    assert parse_bool("False") is False
    assert parse_bool("") is False


def test_validate_columns_raises():
    df = pd.DataFrame({"a": [1]})

    with pytest.raises(ValueError):
        validate_columns(df, ["a", "b"], name="test")


def test_compute_case_count_score():
    assert compute_case_count_score(1000) == 5
    assert compute_case_count_score(500) == 4
    assert compute_case_count_score(200) == 3
    assert compute_case_count_score(50) == 2
    assert compute_case_count_score(1) == 1
    assert compute_case_count_score(0) == 0


def test_compute_open_data_score():
    assert compute_open_data_score(5000, 6000) == 5
    assert compute_open_data_score(1000, 2000) == 3
    assert compute_open_data_score(100, 1000) == 1
    assert compute_open_data_score(0, 0) == 0


def test_compute_multiomics_score():
    row = make_modality_df().iloc[0]
    assert compute_multiomics_score(row) == 18


def test_compute_clinical_utility_score():
    row = make_modality_df().iloc[0]
    assert compute_clinical_utility_score(row) == 7


def test_compute_proteogenomics_bonus():
    row = make_modality_df().iloc[0]
    assert compute_proteogenomics_bonus(row) == 3

    no_protein = make_modality_df().iloc[1]
    assert compute_proteogenomics_bonus(no_protein) == 0


def test_compute_multiomics_modality_count():
    row = make_modality_df().iloc[0]
    assert compute_multiomics_modality_count(row) == 10


def test_assign_priority_label():
    assert assign_priority_label(30) == "excellent"
    assert assign_priority_label(24) == "high"
    assert assign_priority_label(16) == "medium"
    assert assign_priority_label(8) == "low"
    assert assign_priority_label(0) == "very_low"


def test_build_priority_rationale():
    joined = join_project_and_modality_tables(make_project_df(), make_modality_df())
    row = joined[joined["project_id"] == "TCGA-GBM"].iloc[0]

    rationale = build_priority_rationale(row)

    assert "transcriptomics" in rationale
    assert "proteomics" in rationale
    assert "clinical" in rationale
    assert "large cohort" in rationale


def test_join_project_and_modality_tables():
    joined = join_project_and_modality_tables(make_project_df(), make_modality_df())

    assert joined.shape[0] == 3
    assert "project_name" in joined.columns
    assert "has_transcriptomics" in joined.columns


def test_build_gdc_project_priority_ranking_from_dataframes():
    ranking = build_gdc_project_priority_ranking_from_dataframes(
        project_df=make_project_df(),
        modality_df=make_modality_df(),
    )

    assert ranking.shape[0] == 3
    assert ranking.iloc[0]["project_id"] == "TCGA-GBM"
    assert ranking.iloc[0]["priority_label"] == "excellent"
    assert "priority_score" in ranking.columns
    assert "priority_rationale" in ranking.columns

    minimal = ranking[ranking["project_id"] == "MINIMAL-1"].iloc[0]
    assert minimal["priority_label"] in {"very_low", "low"}