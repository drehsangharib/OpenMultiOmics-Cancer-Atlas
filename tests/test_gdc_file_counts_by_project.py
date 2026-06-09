import pandas as pd

from core.search.gdc_file_counts_by_project import (
    extract_project_id_from_file_hit,
    get_pagination_total,
    make_project_filter,
    normalize_value,
    parse_gdc_file_hit,
    parse_gdc_files_response,
    summarize_file_counts,
)


def test_normalize_value_none():
    assert normalize_value(None) == ""


def test_normalize_value_list():
    assert normalize_value(["A", "B"]) == "A; B"


def test_make_project_filter():
    filt = make_project_filter("TCGA-GBM")

    assert filt["op"] == "="
    assert filt["content"]["field"] == "cases.project.project_id"
    assert filt["content"]["value"] == "TCGA-GBM"


def test_extract_project_id_from_file_hit_list_cases():
    hit = {
        "cases": [
            {
                "project": {
                    "project_id": "TCGA-GBM"
                }
            }
        ]
    }

    assert extract_project_id_from_file_hit(hit) == "TCGA-GBM"


def test_extract_project_id_from_file_hit_missing_uses_fallback():
    hit = {"cases": []}

    assert extract_project_id_from_file_hit(hit, fallback="TCGA-LUAD") == "TCGA-LUAD"


def test_parse_gdc_file_hit():
    hit = {
        "file_id": "file-1",
        "data_category": "Transcriptome Profiling",
        "data_type": "Gene Expression Quantification",
        "experimental_strategy": "RNA-Seq",
        "analysis": {
            "workflow_type": "STAR - Counts"
        },
        "data_format": "TSV",
        "access": "open",
        "cases": [
            {
                "project": {
                    "project_id": "TCGA-GBM"
                }
            }
        ],
    }

    row = parse_gdc_file_hit(hit)

    assert row["project_id"] == "TCGA-GBM"
    assert row["data_category"] == "Transcriptome Profiling"
    assert row["data_type"] == "Gene Expression Quantification"
    assert row["experimental_strategy"] == "RNA-Seq"
    assert row["workflow_type"] == "STAR - Counts"
    assert row["data_format"] == "TSV"
    assert row["access"] == "open"


def test_parse_gdc_files_response():
    payload = {
        "data": {
            "hits": [
                {
                    "data_category": "Transcriptome Profiling",
                    "data_type": "Gene Expression Quantification",
                    "experimental_strategy": "RNA-Seq",
                    "analysis": {
                        "workflow_type": "STAR - Counts"
                    },
                    "data_format": "TSV",
                    "access": "open",
                    "cases": [
                        {
                            "project": {
                                "project_id": "TCGA-GBM"
                            }
                        }
                    ],
                },
                {
                    "data_category": "Simple Nucleotide Variation",
                    "data_type": "Masked Somatic Mutation",
                    "experimental_strategy": "WXS",
                    "analysis": {
                        "workflow_type": "MuTect2 Variant Aggregation and Masking"
                    },
                    "data_format": "MAF",
                    "access": "open",
                    "cases": [
                        {
                            "project": {
                                "project_id": "TCGA-GBM"
                            }
                        }
                    ],
                },
            ]
        }
    }

    df = parse_gdc_files_response(payload)

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 2
    assert set(df["data_category"]) == {
        "Transcriptome Profiling",
        "Simple Nucleotide Variation",
    }


def test_get_pagination_total():
    payload = {
        "data": {
            "pagination": {
                "total": 123
            }
        }
    }

    assert get_pagination_total(payload) == 123


def test_summarize_file_counts():
    file_df = pd.DataFrame(
        [
            {
                "project_id": "TCGA-GBM",
                "data_category": "Transcriptome Profiling",
                "data_type": "Gene Expression Quantification",
                "experimental_strategy": "RNA-Seq",
                "workflow_type": "STAR - Counts",
                "data_format": "TSV",
                "access": "open",
            },
            {
                "project_id": "TCGA-GBM",
                "data_category": "Transcriptome Profiling",
                "data_type": "Gene Expression Quantification",
                "experimental_strategy": "RNA-Seq",
                "workflow_type": "STAR - Counts",
                "data_format": "TSV",
                "access": "open",
            },
            {
                "project_id": "TCGA-GBM",
                "data_category": "DNA Methylation",
                "data_type": "Methylation Beta Value",
                "experimental_strategy": "Methylation Array",
                "workflow_type": "",
                "data_format": "TXT",
                "access": "open",
            },
        ]
    )

    summary = summarize_file_counts(file_df)

    assert summary.shape[0] == 2

    rna_row = summary[
        (summary["data_category"] == "Transcriptome Profiling")
        & (summary["data_type"] == "Gene Expression Quantification")
    ].iloc[0]

    assert rna_row["file_count"] == 2
    assert rna_row["source_database"] == "GDC"
    assert rna_row["public_data_use"] == "file_availability_summary"


def test_summarize_file_counts_empty():
    file_df = pd.DataFrame()
    summary = summarize_file_counts(file_df)

    assert summary.empty
    assert "project_id" in summary.columns
    assert "file_count" in summary.columns