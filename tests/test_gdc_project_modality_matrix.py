import pandas as pd
import pytest

from core.search.gdc_project_modality_matrix import (
    add_modality_flags,
    build_project_modality_matrix,
    classify_modalities_for_row,
    compute_access_count,
    compute_dominant_data_category,
    compute_modality_count,
    parse_file_count,
    summarize_project_modalities,
    validate_file_counts_input,
)


def make_demo_file_counts():
    return pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "data_category": "Transcriptome Profiling",
                "data_type": "Gene Expression Quantification",
                "experimental_strategy": "RNA-Seq",
                "workflow_type": "STAR - Counts",
                "data_format": "TSV",
                "access": "open",
                "file_count": 100,
            },
            {
                "project_id": "TCGA-GBM",
                "data_category": "DNA Methylation",
                "data_type": "Methylation Beta Value",
                "experimental_strategy": "Methylation Array",
                "workflow_type": "",
                "data_format": "TXT",
                "access": "open",
                "file_count": 50,
            },
            {
                "project_id": "TCGA-GBM",
                "data_category": "Simple Nucleotide Variation",
                "data_type": "Masked Somatic Mutation",
                "experimental_strategy": "WXS",
                "workflow_type": "MuTect2",
                "data_format": "MAF",
                "access": "open",
                "file_count": 25,
            },
            {
                "project_id": "TCGA-GBM",
                "data_category": "Copy Number Variation",
                "data_type": "Copy Number Segment",
                "experimental_strategy": "Genotyping Array",
                "workflow_type": "DNAcopy",
                "data_format": "TXT",
                "access": "open",
                "file_count": 30,
            },
            {
                "project_id": "TCGA-LUAD",
                "data_category": "Clinical",
                "data_type": "Clinical Supplement",
                "experimental_strategy": "",
                "workflow_type": "",
                "data_format": "BCR XML",
                "access": "open",
                "file_count": 10,
            },
            {
                "project_id": "TCGA-LUAD",
                "data_category": "Proteome Profiling",
                "data_type": "Protein Expression Quantification",
                "experimental_strategy": "Reverse Phase Protein Array",
                "workflow_type": "",
                "data_format": "TSV",
                "access": "open",
                "file_count": 20,
            },
            {
                "project_id": "TCGA-LUAD",
                "data_category": "Sequencing Reads",
                "data_type": "Aligned Reads",
                "experimental_strategy": "WXS",
                "workflow_type": "BWA",
                "data_format": "BAM",
                "access": "controlled",
                "file_count": 200,
            },
            {
                "project_id": "TCGA-LUAD",
                "data_category": "Biospecimen",
                "data_type": "Slide Image",
                "experimental_strategy": "Diagnostic Slide",
                "workflow_type": "",
                "data_format": "SVS",
                "access": "open",
                "file_count": 5,
            },
        ]
    )


def test_parse_file_count_valid_and_invalid():
    assert parse_file_count("10") == 10
    assert parse_file_count(5) == 5
    assert parse_file_count("bad") == 0
    assert parse_file_count(None) == 0


def test_validate_file_counts_input_missing_column():
    df = pd.DataFrame({"project_id": ["TCGA-GBM"]})

    with pytest.raises(ValueError):
        validate_file_counts_input(df)


def test_classify_modalities_for_transcriptomics_row():
    row = pd.Series(
        {
            "data_category": "Transcriptome Profiling",
            "data_type": "Gene Expression Quantification",
            "experimental_strategy": "RNA-Seq",
        }
    )

    flags = classify_modalities_for_row(row)

    assert flags["transcriptomics"] is True
    assert flags["methylation"] is False


def test_classify_modalities_for_slide_image_row():
    row = pd.Series(
        {
            "data_category": "Biospecimen",
            "data_type": "Slide Image",
            "experimental_strategy": "Diagnostic Slide",
        }
    )

    flags = classify_modalities_for_row(row)

    assert flags["biospecimen"] is True
    assert flags["slide_images"] is True


def test_add_modality_flags():
    df = make_demo_file_counts()
    flagged = add_modality_flags(df)

    assert "is_transcriptomics" in flagged.columns
    assert "is_methylation" in flagged.columns
    assert "is_proteomics" in flagged.columns
    assert flagged["file_count"].dtype.kind in {"i", "u"}


def test_compute_modality_count():
    df = make_demo_file_counts()
    flagged = add_modality_flags(df)
    gbm = flagged[flagged["project_id"] == "TCGA-GBM"]

    assert compute_modality_count(gbm, "transcriptomics") == 100
    assert compute_modality_count(gbm, "methylation") == 50


def test_compute_access_count():
    df = make_demo_file_counts()
    flagged = add_modality_flags(df)
    luad = flagged[flagged["project_id"] == "TCGA-LUAD"]

    assert compute_access_count(luad, "open") == 35
    assert compute_access_count(luad, "controlled") == 200


def test_compute_dominant_data_category():
    df = make_demo_file_counts()
    flagged = add_modality_flags(df)
    luad = flagged[flagged["project_id"] == "TCGA-LUAD"]

    dominant = compute_dominant_data_category(luad)

    assert dominant["dominant_data_category"] == "Sequencing Reads"
    assert dominant["dominant_data_category_file_count"] == 200


def test_summarize_project_modalities():
    df = make_demo_file_counts()
    flagged = add_modality_flags(df)
    matrix = summarize_project_modalities(flagged)

    assert matrix.shape[0] == 2

    gbm = matrix[matrix["project_id"] == "TCGA-GBM"].iloc[0]
    assert bool(gbm["has_transcriptomics"]) is True
    assert bool(gbm["has_methylation"]) is True
    assert bool(gbm["has_snv"]) is True
    assert bool(gbm["has_cnv"]) is True
    assert gbm["total_file_count"] == 205

    luad = matrix[matrix["project_id"] == "TCGA-LUAD"].iloc[0]
    assert bool(luad["has_clinical"]) is True
    assert bool(luad["has_proteomics"]) is True
    assert bool(luad["has_sequencing_reads"]) is True
    assert bool(luad["has_slide_images"]) is True
    assert luad["controlled_file_count"] == 200


def test_build_project_modality_matrix():
    df = make_demo_file_counts()
    matrix = build_project_modality_matrix(df)

    assert set(matrix["project_id"]) == {"TCGA-GBM", "TCGA-LUAD"}
    assert "has_transcriptomics" in matrix.columns
    assert "proteomics_file_count" in matrix.columns
    assert "dominant_data_category" in matrix.columns