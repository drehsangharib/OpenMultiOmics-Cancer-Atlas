from pathlib import Path

import pandas as pd
import pytest

from core.visualization.gdc_priority_visuals import (
    build_top_project_heatmap_matrix,
    clean_modality_matrix,
    clean_priority_ranking,
    generate_gdc_priority_visuals,
    parse_bool,
    parse_int,
    summarize_modality_coverage,
    summarize_priority_labels,
    validate_columns,
)


def make_ranking_df():
    return pd.DataFrame(
        [
            {
                "rank": "1",
                "project_id": "TCGA-GBM",
                "priority_score": "35",
                "priority_label": "excellent",
                "multiomics_modality_count": "10",
            },
            {
                "rank": "2",
                "project_id": "TCGA-LUAD",
                "priority_score": "33",
                "priority_label": "high",
                "multiomics_modality_count": "8",
            },
            {
                "rank": "3",
                "project_id": "MINIMAL-1",
                "priority_score": "4",
                "priority_label": "very_low",
                "multiomics_modality_count": "1",
            },
        ]
    )


def make_modality_df():
    return pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "has_transcriptomics": "True",
                "has_methylation": "True",
                "has_snv": "True",
                "has_cnv": "True",
                "has_structural_variation": "True",
                "has_clinical": "True",
                "has_biospecimen": "True",
                "has_proteomics": "True",
                "has_slide_images": "True",
                "has_sequencing_reads": "True",
            },
            {
                "project_id": "TCGA-LUAD",
                "has_transcriptomics": "True",
                "has_methylation": "False",
                "has_snv": "True",
                "has_cnv": "True",
                "has_structural_variation": "True",
                "has_clinical": "True",
                "has_biospecimen": "True",
                "has_proteomics": "False",
                "has_slide_images": "True",
                "has_sequencing_reads": "True",
            },
            {
                "project_id": "MINIMAL-1",
                "has_transcriptomics": "False",
                "has_methylation": "False",
                "has_snv": "False",
                "has_cnv": "False",
                "has_structural_variation": "False",
                "has_clinical": "False",
                "has_biospecimen": "False",
                "has_proteomics": "False",
                "has_slide_images": "False",
                "has_sequencing_reads": "True",
            },
        ]
    )


def test_parse_bool():
    assert parse_bool(True) is True
    assert parse_bool("True") is True
    assert parse_bool("yes") is True
    assert parse_bool("False") is False
    assert parse_bool("") is False


def test_parse_int():
    assert parse_int("10") == 10
    assert parse_int(2.0) == 2
    assert parse_int("bad") == 0
    assert parse_int(None) == 0


def test_validate_columns_raises():
    df = pd.DataFrame({"a": [1]})

    with pytest.raises(ValueError):
        validate_columns(df, ["a", "b"], name="demo")


def test_clean_priority_ranking():
    clean = clean_priority_ranking(make_ranking_df())

    assert clean.iloc[0]["rank"] == 1
    assert clean.iloc[0]["priority_score"] == 35
    assert clean.iloc[0]["multiomics_modality_count"] == 10


def test_clean_modality_matrix():
    clean = clean_modality_matrix(make_modality_df())

    assert bool(clean.loc[0, "has_transcriptomics"]) is True
    assert bool(clean.loc[1, "has_methylation"]) is False


def test_summarize_priority_labels():
    clean = clean_priority_ranking(make_ranking_df())
    summary = summarize_priority_labels(clean)

    labels = summary["priority_label"].tolist()
    assert labels == ["excellent", "high", "medium", "low", "very_low"]

    excellent = summary[summary["priority_label"] == "excellent"].iloc[0]
    assert excellent["project_count"] == 1


def test_summarize_modality_coverage():
    clean = clean_modality_matrix(make_modality_df())
    summary = summarize_modality_coverage(clean)

    transcriptomics = summary[summary["modality"] == "Transcriptomics"].iloc[0]
    assert transcriptomics["project_count"] == 2


def test_build_top_project_heatmap_matrix():
    ranking = clean_priority_ranking(make_ranking_df())
    modality = clean_modality_matrix(make_modality_df())

    matrix = build_top_project_heatmap_matrix(
        ranking_df=ranking,
        modality_df=modality,
        top_n=2,
    )

    assert matrix.shape[0] == 2
    assert "Transcriptomics" in matrix.columns
    assert matrix.loc["TCGA-GBM", "Transcriptomics"] == 1
    assert matrix.loc["TCGA-LUAD", "DNA methylation"] == 0


def test_generate_gdc_priority_visuals_without_file_counts(tmp_path: Path):
    ranking_path = tmp_path / "ranking.tsv"
    modality_path = tmp_path / "modality.tsv"
    file_counts_path = tmp_path / "missing_file_counts.tsv"
    figures_dir = tmp_path / "figures"

    make_ranking_df().to_csv(ranking_path, sep="\t", index=False)
    make_modality_df().to_csv(modality_path, sep="\t", index=False)

    outputs = generate_gdc_priority_visuals(
        priority_ranking_path=ranking_path,
        modality_matrix_path=modality_path,
        file_counts_path=file_counts_path,
        figures_dir=figures_dir,
        top_n=2,
    )

    expected_keys = {
        "priority_label_distribution",
        "modality_coverage",
        "project_modality_heatmap",
        "pipeline_schematic",
        "project_modality_heatmap_top_binary",
        "project_modality_heatmap_all_binary",
    }

    assert set(outputs.keys()) == expected_keys

    for path in outputs.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_gdc_priority_visuals_with_file_counts(tmp_path: Path):
    ranking_path = tmp_path / "ranking.tsv"
    modality_path = tmp_path / "modality.tsv"
    file_counts_path = tmp_path / "file_counts.tsv"
    figures_dir = tmp_path / "figures"

    make_ranking_df().to_csv(ranking_path, sep="\t", index=False)
    make_modality_df().to_csv(modality_path, sep="\t", index=False)

    file_counts_df = pd.DataFrame(
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
                "project_id": "TCGA-LUAD",
                "data_category": "DNA Methylation",
                "data_type": "Methylation Beta Value",
                "experimental_strategy": "Methylation Array",
                "workflow_type": "",
                "data_format": "TXT",
                "access": "open",
                "file_count": 50,
            },
        ]
    )

    file_counts_df.to_csv(file_counts_path, sep="\t", index=False)

    outputs = generate_gdc_priority_visuals(
        priority_ranking_path=ranking_path,
        modality_matrix_path=modality_path,
        file_counts_path=file_counts_path,
        figures_dir=figures_dir,
        top_n=2,
    )

    expected_keys = {
        "priority_label_distribution",
        "modality_coverage",
        "project_modality_heatmap",
        "pipeline_schematic",
        "project_modality_heatmap_top_binary",
        "project_modality_heatmap_all_binary",
        "project_modality_filecount_heatmap",
    }

    assert set(outputs.keys()) == expected_keys

    for path in outputs.values():
        assert path.exists()
        assert path.stat().st_size > 0

