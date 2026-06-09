from pathlib import Path

import pandas as pd
import pytest

from core.reporting.gdc_priority_report import (
    build_bar_list,
    build_report_html,
    clean_modality_matrix,
    clean_priority_ranking,
    clean_project_inventory,
    dataframe_to_html_table,
    generate_gdc_priority_report,
    parse_bool,
    parse_int,
    summarize_modality_coverage,
    summarize_priority_labels,
    summarize_programs,
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
                "case_count": "600",
                "file_count": "30000",
            },
            {
                "project_id": "TCGA-LUAD",
                "project_name": "Lung Adenocarcinoma",
                "program_name": "TCGA",
                "primary_site": "Bronchus and lung",
                "disease_type": "Adenomas and Adenocarcinomas",
                "case_count": "500",
                "file_count": "36000",
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
                "total_file_count": "30000",
                "open_file_count": "15000",
                "controlled_file_count": "15000",
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
                "total_file_count": "36000",
                "open_file_count": "20000",
                "controlled_file_count": "16000",
            },
        ]
    )


def make_ranking_df():
    return pd.DataFrame(
        [
            {
                "rank": "1",
                "project_id": "TCGA-GBM",
                "project_name": "Glioblastoma Multiforme",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "case_count": "600",
                "priority_score": "35",
                "priority_label": "excellent",
                "multiomics_modality_count": "10",
                "priority_rationale": "transcriptomics; proteomics; clinical",
            },
            {
                "rank": "2",
                "project_id": "TCGA-LUAD",
                "project_name": "Lung Adenocarcinoma",
                "program_name": "TCGA",
                "primary_site": "Bronchus and lung",
                "case_count": "500",
                "priority_score": "33",
                "priority_label": "excellent",
                "multiomics_modality_count": "8",
                "priority_rationale": "transcriptomics; clinical",
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
    assert parse_bool("False") is False
    assert parse_bool("") is False


def test_validate_columns_raises():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError):
        validate_columns(df, ["a", "b"], name="demo")


def test_clean_project_inventory():
    clean = clean_project_inventory(make_project_df())
    assert clean["case_count"].dtype.kind in {"i", "u"}
    assert clean["file_count"].dtype.kind in {"i", "u"}


def test_clean_modality_matrix():
    clean = clean_modality_matrix(make_modality_df())
    assert bool(clean.loc[0, "has_transcriptomics"]) is True
    assert bool(clean.loc[1, "has_methylation"]) is False
    assert clean["total_file_count"].dtype.kind in {"i", "u"}


def test_clean_priority_ranking():
    clean = clean_priority_ranking(make_ranking_df())
    assert clean.iloc[0]["rank"] == 1
    assert clean.iloc[0]["priority_score"] == 35


def test_summarize_programs():
    summary = summarize_programs(clean_project_inventory(make_project_df()))
    assert summary.iloc[0]["program_name"] == "TCGA"
    assert summary.iloc[0]["project_count"] == 2


def test_summarize_priority_labels():
    summary = summarize_priority_labels(clean_priority_ranking(make_ranking_df()))
    assert "excellent" in summary["priority_label"].astype(str).tolist()


def test_summarize_modality_coverage():
    summary = summarize_modality_coverage(clean_modality_matrix(make_modality_df()))
    transcriptomics = summary[summary["modality"] == "Transcriptomics"].iloc[0]
    assert transcriptomics["project_count"] == 2


def test_dataframe_to_html_table():
    html_table = dataframe_to_html_table(make_ranking_df(), max_rows=1)
    assert "<table" in html_table
    assert "TCGA-GBM" in html_table


def test_build_bar_list():
    df = pd.DataFrame({"label": ["A", "B"], "value": [10, 5]})
    bars = build_bar_list(df, label_col="label", value_col="value")
    assert "bar-row" in bars
    assert "A" in bars


def test_build_report_html():
    report = build_report_html(
        project_df=clean_project_inventory(make_project_df()),
        modality_df=clean_modality_matrix(make_modality_df()),
        ranking_df=clean_priority_ranking(make_ranking_df()),
    )

    assert "OpenMultiOmics-Cancer-Atlas" in report
    assert "Top-ranked projects" in report
    assert "TCGA-GBM" in report


def test_generate_gdc_priority_report(tmp_path: Path):
    project_path = tmp_path / "project.tsv"
    modality_path = tmp_path / "modality.tsv"
    ranking_path = tmp_path / "ranking.tsv"
    output_path = tmp_path / "report.html"

    make_project_df().to_csv(project_path, sep="\t", index=False)
    make_modality_df().to_csv(modality_path, sep="\t", index=False)
    make_ranking_df().to_csv(ranking_path, sep="\t", index=False)

    report = generate_gdc_priority_report(
        project_inventory_path=project_path,
        modality_matrix_path=modality_path,
        priority_ranking_path=ranking_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert "OpenMultiOmics-Cancer-Atlas" in report
    assert "TCGA-LUAD" in report